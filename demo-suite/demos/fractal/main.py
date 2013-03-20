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
import os

import lib_path
import google_cloud.gce as gce
import google_cloud.gce_appengine as gce_appengine
import jinja2
import oauth2client.appengine as oauth2appengine
import webapp2

from google.appengine.api import urlfetch

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(''))

DEMO_NAME = 'fractal'
IMAGE = 'fractal-demo-image'
FIREWALL = 'www-fractal'
FIREWALL_DESCRIPTION = 'Fractal Demo Firewall'
GCE_SCOPE = 'https://www.googleapis.com/auth/compute'
STARTUP_SCRIPT = os.path.join(os.path.dirname(__file__), 'startup.sh')


class Fractal(webapp2.RequestHandler):
  """Show main page of Fractal demo."""

  def get(self):
    """Show main page of Fractal demo."""

    template = jinja_environment.get_template(
        'demos/%s/templates/index.html' % DEMO_NAME)
    self.response.out.write(template.render({'tag': DEMO_NAME}))


class Instance(webapp2.RequestHandler):
  """Start and list instances."""

  def get(self):
    """List instances.

    Uses app engine app identity to retrieve an access token for the app
    engine service account. No client OAuth required. External IP is used
    to determine if the instance is actually running.
    """

    credentials = oauth2appengine.AppAssertionCredentials(scope=GCE_SCOPE)
    gce_project = gce.GceProject(credentials=credentials)
    instances = gce_appengine.GceAppEngine().run_gce_request(
        self,
        gce_project.list_instances,
        'Error listing instances: ',
        filter='name eq ^%s.*' % DEMO_NAME)

    # Convert instance info to dict and check server status.
    if instances:
      instance_dict = {}
      for instance in instances:
        status = None
        if instance.status:
          status = instance.status
        else:
          status = 'STAGING'
        instance_dict[instance.name] = {'status': status}
        ip = None
        for interface in instance.network_interfaces:
          for config in interface.get('accessConfigs', []):
            if 'natIP' in config:
              ip = config['natIP']
              break
          if ip: break

        # Ping the instance server. If result is 'ok', set status to
        # RUNNING. Otherwise, set to STAGING.
        if ip:
          result = None
          try:
            result = urlfetch.fetch(url='http://%s/health' % ip, deadline=2)
          except urlfetch.Error:
            instance_dict[instance.name]['status'] = 'STAGING'
          if result and result.content != 'ok':
            instance_dict[instance.name]['status'] = 'STAGING'
          instance_dict[instance.name]['externalIp'] = ip

      json_instances = json.dumps(instance_dict)
      self.response.headers['Content-Type'] = 'application/json'
      self.response.out.write(json_instances)

  def post(self):
    """Start instances with the given startup script.

    Uses app engine app identity to retrieve an access token for the app
    engine service account. No client OAuth required.
    """

    credentials = oauth2appengine.AppAssertionCredentials(scope=GCE_SCOPE)
    gce_project = gce.GceProject(credentials=credentials)

    # Create the firewall if it doesn't exist.
    firewalls = gce_project.list_firewalls()
    firewall_names = [firewall.name for firewall in firewalls]
    if not FIREWALL in firewall_names:
      firewall = gce.Firewall(
          name=FIREWALL,
          target_tags=[DEMO_NAME],
          description=FIREWALL_DESCRIPTION)
      gce_project.insert(firewall)

    # Get the list of instances to insert.
    num_slow_map_instances = int(self.request.get('num_slow_map_instances'))
    slow_map_instance_tag = self.request.get('slow_map_instance_tag')
    slow_map_instances = self._get_instance_list(
        gce_project, num_slow_map_instances, slow_map_instance_tag)
    num_fast_map_instances = int(self.request.get('num_fast_map_instances'))
    fast_map_instance_tag = self.request.get('fast_map_instance_tag')
    fast_map_instances = self._get_instance_list(
        gce_project, num_fast_map_instances, fast_map_instance_tag)
    instances = slow_map_instances + fast_map_instances

    gce_appengine.GceAppEngine().run_gce_request(
        self,
        gce_project.bulk_insert,
        'Error inserting instances: ',
        resources=instances)

  def _get_instance_list(self, gce_project, num_instances, tag):
    """Get a list of instances to start.

    Args:
      gce_project: An instance of gce.GceProject.
      num_instances: The number of instances to start.
      tag: A string tag to prepend to the instance name.

    Returns:
      A list of gcelib.Instances.
    """

    instance_list = []
    for i in range(num_instances):
      instance = gce.Instance(
          name='%s-%d' % (tag, i),
          image_name=IMAGE,
          image_project=gce_project.settings['project'],
          machine_type_name=gce_project.settings['compute']['machine_type'],
          tags=[DEMO_NAME],
          metadata=[{
              'key': 'startup-script',
              'value': open(STARTUP_SCRIPT, 'r').read()}],
          service_accounts=gce_project.settings['cloud_service_account'])
      instance_list.append(instance)
    return instance_list


app = webapp2.WSGIApplication(
    [
        ('/%s' % DEMO_NAME, Fractal),
        ('/%s/instance' % DEMO_NAME, Instance)
    ], debug=True)
