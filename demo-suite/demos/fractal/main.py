# Copyright 2012 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Fractal demo."""

from __future__ import with_statement

__author__ = 'kbrisbin@google.com (Kathryn Hurley)'

import json
import logging
import os
import time

import lib_path
import google_cloud.gce as gce
import google_cloud.gce_appengine as gce_appengine
import google_cloud.oauth as oauth
import jinja2
import oauth2client.appengine as oauth2client
import user_data
import webapp2

from google.appengine.api import urlfetch

DEMO_NAME = 'fractal'
CUSTOM_IMAGE = 'fractal-demo-image'
MACHINE_TYPE='n1-highcpu-2'
FIREWALL = 'www-fractal'
FIREWALL_DESCRIPTION = 'Fractal Demo Firewall'
GCE_SCOPE = 'https://www.googleapis.com/auth/compute'
HEALTH_CHECK_TIMEOUT = 1

VM_FILES = os.path.join(os.path.dirname(__file__), 'vm_files')
STARTUP_SCRIPT = os.path.join(VM_FILES, 'startup.sh')
GO_PROGRAM = os.path.join(VM_FILES, 'mandelbrot.go')
GO_ARGS = '--portBase=80 --numPorts=1'
GO_TILESERVER_FLAG = '--tileServers='

# TODO: Update these values with your project and LB IP/destinations.
LB_PROJECTS = {
  'your-project': ['a.b.c.d'],
}

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(''))
oauth_decorator = oauth.decorator
parameters = [
    user_data.DEFAULTS[user_data.GCE_PROJECT_ID],
    user_data.DEFAULTS[user_data.GCE_ZONE_NAME]
]
data_handler = user_data.DataHandler(DEMO_NAME, parameters)


class ServerVarsAggregator(object):
  """Aggregate stats across multiple servers and produce a summary."""

  def __init__(self):
    """Constructor for ServerVarsAggregator."""
    # A map of tile-size -> count
    self.tile_counts = {}
    # A map of tile-size -> time
    self.tile_times = {}

    # The uptime of the server that has been up and running the longest.
    self.max_uptime = 0

  def aggregate_vars(self, instance_vars):
    """Integrate instance_vars into the running aggregates.

    Args:
      instance_vars A parsed JSON object returned from /debug/vars
    """
    self._aggregate_map(instance_vars['tileCount'], self.tile_counts)
    self._aggregate_map(instance_vars['tileTime'], self.tile_times)
    self.max_uptime = max(self.max_uptime, instance_vars['uptime'])

  def _aggregate_map(self, src_map, dest_map):
    """Aggregate one map from src_map into dest_map."""
    for k, v in src_map.items():
      dest_map[k] = dest_map.get(k, 0L) + long(v)

  def get_aggregate(self):
    """Get the overall aggregate, including derived values."""
    tile_time_avg = {}
    result = {
      'tileCount': self.tile_counts.copy(),
      'tileTime': self.tile_times.copy(),
      'tileTimeAvgMs': tile_time_avg,
      'maxUptime': self.max_uptime,
    }
    for size, count in self.tile_counts.items():
      time = self.tile_times.get(size, 0)
      if time and count:
        # Compute average tile time in milliseconds.  The raw time is in
        # nanoseconds.
        tile_time_avg[size] = float(time / count) / float(1000*1000)
        logging.debug('tile-size: %s count: %d time: %d avg: %d', size, count, time, tile_time_avg[size])
    return result


class Fractal(webapp2.RequestHandler):
  """Fractal demo."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get(self):
    """Show main page of Fractal demo."""

    template = jinja_environment.get_template(
        'demos/%s/templates/index.html' % DEMO_NAME)
    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    self.response.out.write(template.render({
      'demo_name': DEMO_NAME,
      'lb_enabled': gce_project_id in LB_PROJECTS,
    }))

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get_instances(self):
    """List instances.

    Uses app engine app identity to retrieve an access token for the app
    engine service account. No client OAuth required. External IP is used
    to determine if the instance is actually running.
    """

    gce_project = self._create_gce()
    instances = gce_appengine.GceAppEngine().run_gce_request(
        self,
        gce_project.list_instances,
        'Error listing instances: ',
        filter='name eq ^%s-.*' % self.instance_prefix())

    # A map of instanceName -> (ip, RPC)
    health_rpcs = {}

    # Convert instance info to dict and check server status.
    num_running = 0
    instance_dict = {}
    if instances:
      for instance in instances:
        instance_record = {}
        instance_dict[instance.name] = instance_record
        if instance.status:
          instance_record['status'] = instance.status
        else:
          instance_record['status'] = 'OTHER'
        ip = None
        for interface in instance.network_interfaces:
          for config in interface.get('accessConfigs', []):
            if 'natIP' in config:
              ip = config['natIP']
              instance_record['externalIp'] = ip
              break
          if ip: break

        # Ping the instance server. Grab stats from /debug/vars.
        if ip and instance.status == 'RUNNING':
          num_running += 1
          health_url = 'http://%s/debug/vars?t=%d' % (ip, int(time.time()))
          logging.debug('Health checking %s', health_url)
          rpc = urlfetch.create_rpc(deadline = HEALTH_CHECK_TIMEOUT)
          urlfetch.make_fetch_call(rpc, url=health_url)
          health_rpcs[instance.name] = rpc

    # Ping through a LBs too.  Only if we get success there do we know we are
    # really serving.
    loadbalancers = []
    lb_rpcs = {}
    if instances and len(instances) > 1:
      loadbalancers = self._get_lb_servers(gce_project)
    if num_running > 0 and loadbalancers:
      for lb in loadbalancers:
        health_url = 'http://%s/health?t=%d' % (lb, int(time.time()))
        logging.debug('Health checking %s', health_url)
        rpc = urlfetch.create_rpc(deadline = HEALTH_CHECK_TIMEOUT)
        urlfetch.make_fetch_call(rpc, url=health_url)
        lb_rpcs[lb] = rpc

    # wait for RPCs to complete and update dict as necessary
    vars_aggregator = ServerVarsAggregator()

    # TODO: there is significant duplication here.  Refactor.
    for (instance_name, rpc) in health_rpcs.items():
      result = None
      instance_record = instance_dict[instance_name]
      try:
        result = rpc.get_result()
        if result and "memstats" in result.content:
          logging.debug('%s healthy!', instance_name)
          instance_record['status'] = 'SERVING'
          instance_vars = {}
          try:
            instance_vars = json.loads(result.content)
            instance_record['vars'] = instance_vars
            vars_aggregator.aggregate_vars(instance_vars)
          except ValueError as error:
            logging.error('Error decoding vars json for %s: %s', instance_name, error)
        else:
          logging.debug('%s unhealthy. Content: %s', instance_name, result.content)
      except urlfetch.Error as error:
        logging.debug('%s unhealthy: %s', instance_name, str(error))

    # Check health status through the load balancer.
    loadbalancer_healthy = bool(lb_rpcs)
    for (lb, lb_rpc) in lb_rpcs.items():
      result = None
      try:
        result = lb_rpc.get_result()
        if result and "ok" in result.content:
          logging.info('LB %s healthy: %s\n%s', lb, result.headers, result.content)
        else:
          logging.info('LB %s result not okay: %s, %s', lb, result.status_code, result.content)
          loadbalancer_healthy = False
          break
      except urlfetch.Error as error:
        logging.info('LB %s fetch error: %s', lb, str(error))
        loadbalancer_healthy = False
        break

    response_dict = {
      'instances': instance_dict,
      'vars': vars_aggregator.get_aggregate(),
      'loadbalancers': loadbalancers,
      'loadbalancer_healthy': loadbalancer_healthy,
    }
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json.dumps(response_dict))

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def set_instances(self):
    """Start/stop instances so we have the requested number running."""

    gce_project = self._create_gce()

    self._setup_firewall(gce_project)
    image = self._get_image(gce_project)
    disks = self._get_disks(gce_project)

    # Get the list of instances to insert.
    num_instances = int(self.request.get('num_instances'))
    target = self._get_instance_list(
        gce_project, num_instances, image, disks)
    target_set = set()
    target_map = {}
    for instance in target:
      target_set.add(instance.name)
      target_map[instance.name] = instance

    # Get the list of instances running
    current = gce_appengine.GceAppEngine().run_gce_request(
        self,
        gce_project.list_instances,
        'Error listing instances: ',
        filter='name eq ^%s-.*' % self.instance_prefix())
    current_set = set()
    current_map = {}
    for instance in current:
      current_set.add(instance.name)
      current_map[instance.name] = instance

    # Add the new instances
    to_add_set = target_set - current_set
    to_add = [target_map[name] for name in to_add_set]
    if to_add:
      gce_appengine.GceAppEngine().run_gce_request(
          self,
          gce_project.bulk_insert,
          'Error inserting instances: ',
          resources=to_add)

    # Remove the old instances
    to_remove_set = current_set - target_set
    to_remove = [current_map[name] for name in to_remove_set]
    if to_remove:
      gce_appengine.GceAppEngine().run_gce_request(
          self,
          gce_project.bulk_delete,
          'Error deleting instances: ',
          resources=to_remove)

    logging.info("current_set: %s", current_set)
    logging.info("target_set: %s", target_set)
    logging.info("to_add_set: %s", to_add_set)
    logging.info("to_remove_set: %s", to_remove_set)

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def cleanup(self):
    """Stop instances using the gce_appengine helper class."""
    gce_project = self._create_gce()
    gce_appengine.GceAppEngine().delete_demo_instances(
        self, gce_project, self.instance_prefix())

  def _get_lb_servers(self, gce_project):
    return LB_PROJECTS.get(gce_project.project_id, [])

  def instance_prefix(self):
    """Return a prefix based on a request/query params."""
    tag = self.request.get('tag')
    prefix = DEMO_NAME
    if tag:
      prefix = prefix + '-' + tag
    return prefix

  def _create_gce(self):
    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
    return gce.GceProject(oauth_decorator.credentials,
                          project_id=gce_project_id,
                          zone_name=gce_zone_name)

  def _setup_firewall(self, gce_project):
    "Create the firewall if it doesn't exist."
    firewalls = gce_project.list_firewalls()
    firewall_names = [firewall.name for firewall in firewalls]
    if not FIREWALL in firewall_names:
      firewall = gce.Firewall(
          name=FIREWALL,
          target_tags=[DEMO_NAME],
          description=FIREWALL_DESCRIPTION)
      gce_project.insert(firewall)

  def _get_image(self, gce_project):
    """Returns the appropriate image to use.  def _has_custom_image(self, gce_project):

    Args:
      gce_project: An instance of gce.GceProject

    Returns: (project, image_name) for the image to use.
    """
    images = gce_project.list_images(filter='name eq ^%s$' % CUSTOM_IMAGE)
    if images:
      return (gce_project.project_id, CUSTOM_IMAGE)
    return ('google', None)

  def _get_disks(self, gce_project):
    """Get boot disks for VMs."""
    disks_array = gce_project.list_disks(
      filter='name eq ^boot-%s-.*' % self.instance_prefix())

    disks = {}
    for d in disks_array:
      disks[d.name] = d
    return disks

  def _get_instance_metadata(self, gce_project, instance_names):
    """The metadata values to pass into the instance."""
    inline_values = {
      'goargs': GO_ARGS,
    }

    file_values = {
      'startup-script': STARTUP_SCRIPT,
      'goprog': GO_PROGRAM,
    }

    # Try and use LBs if we have any.  But only do that if we have more than one
    # instance.
    if instance_names:
      tile_servers = ''
      if len(instance_names) > 1:
        tile_servers = self._get_lb_servers(gce_project)
      if not tile_servers:
        tile_servers = instance_names
      tile_servers = ','.join(tile_servers)
      inline_values['goargs'] += ' %s%s' %(GO_TILESERVER_FLAG, tile_servers)

    metadata = []
    for k, v in inline_values.items():
      metadata.append({'key': k, 'value': v})

    for k, fv in file_values.items():
      v = open(fv, 'r').read()
      metadata.append({'key': k, 'value': v})
    return metadata

  def _get_instance_list(self, gce_project, num_instances, image, disks):
    """Get a list of instances to start.

    Args:
      gce_project: An instance of gce.GceProject.
      num_instances: The number of instances to start.
      image: tuple with (project_name, image_name) for the image to use.
      disks: A dictionary of disk_name -> disk resources

    Returns:
      A list of gce.Instances.
    """


    instance_names = []
    for i in range(num_instances):
      instance_names.append('%s-%02d' % (self.instance_prefix(), i))

    instance_list = []
    for instance_name in instance_names:
      disk_name = 'boot-%s' % instance_name
      disk = disks.get(disk_name, None)
      disk_mounts = []
      image_project_id = None
      image_name = None
      kernel = None
      if disk:
        dm = gce.DiskMount(disk=disk, boot=True)
        kernel = gce_project.settings['compute']['kernel']
        disk_mounts.append(dm)
      else:
        image_project_id, image_name = image


      gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
      instance = gce.Instance(
          name=instance_name,
          machine_type_name=MACHINE_TYPE,
          zone_name=gce_zone_name,
          image_name=image_name,
          image_project_id=image_project_id,
          disk_mounts=disk_mounts,
          kernel=kernel,
          tags=[DEMO_NAME, self.instance_prefix()],
          metadata=self._get_instance_metadata(gce_project, instance_names),
          service_accounts=gce_project.settings['cloud_service_account'])
      instance_list.append(instance)
    return instance_list


app = webapp2.WSGIApplication(
    [
        ('/%s' % DEMO_NAME, Fractal),
        webapp2.Route('/%s/instance' % DEMO_NAME,
          handler=Fractal, handler_method='get_instances',
          methods=['GET']),
        webapp2.Route('/%s/instance' % DEMO_NAME,
          handler=Fractal, handler_method='set_instances',
          methods=['POST']),
        webapp2.Route('/%s/cleanup' % DEMO_NAME,
          handler=Fractal, handler_method='cleanup',
          methods=['POST']),
        (data_handler.url_path, data_handler.data_handler),
    ], debug=True)
