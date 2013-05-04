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
import logging

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
IMAGE = 'fractal-demo-image'
MACHINE_TYPE='n1-highcpu-4'
FIREWALL = 'www-fractal'
FIREWALL_DESCRIPTION = 'Fractal Demo Firewall'
GCE_SCOPE = 'https://www.googleapis.com/auth/compute'

VM_FILES = os.path.join(os.path.dirname(__file__), 'vm_files')
STARTUP_SCRIPT = os.path.join(VM_FILES, 'startup.sh')
GO_PROGRAM = os.path.join(VM_FILES, 'mandelbrot.go')
GO_ARGS = '--portBase=80 --numPorts=1'

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(''))
oauth_decorator = oauth.decorator
parameters = [
    user_data.DEFAULTS[user_data.GCE_PROJECT_ID],
    user_data.DEFAULTS[user_data.GCE_ZONE_NAME]
]
data_handler = user_data.DataHandler(DEMO_NAME, parameters)


class RequestHandler(webapp2.RequestHandler):
  """Common request handler for the Fractal Demo."""
  def InstancePrefix(self):
    """Return a prefix based on a request/query params."""
    tag = self.request.get('tag')
    prefix = DEMO_NAME
    if tag:
      prefix = prefix + '-' + tag
    return prefix


class Fractal(webapp2.RequestHandler):
  """Show main page of Fractal demo."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get(self):
    """Show main page of Fractal demo."""

    template = jinja_environment.get_template(
        'demos/%s/templates/index.html' % DEMO_NAME)
    self.response.out.write(template.render({'demo_name': DEMO_NAME}))


class Instance(RequestHandler):
  """Start and list instances."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get(self):
    """List instances.

    Uses app engine app identity to retrieve an access token for the app
    engine service account. No client OAuth required. External IP is used
    to determine if the instance is actually running.
    """

    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
    gce_project = gce.GceProject(oauth_decorator.credentials,
                                 project_id=gce_project_id,
                                 zone_name=gce_zone_name)
    instances = gce_appengine.GceAppEngine().run_gce_request(
        self,
        gce_project.list_instances,
        'Error listing instances: ',
        filter='name eq ^%s-.*' % self.InstancePrefix())

    # Convert instance info to dict and check server status.
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

        # Ping the instance server. If result is 'ok', set status to
        # RUNNING. Otherwise, set to STAGING.
        if ip and instance.status == 'RUNNING':
          result = None
          try:
            logging.debug('Health checking %s', ip)
            result = urlfetch.fetch(url='http://%s/health' % ip, deadline=2)
          except urlfetch.Error:
            logging.debug('%s unhealthy', ip)
            instance_record['status'] = 'STAGING'
          if result and result.content.strip() != 'ok':
            logging.debug('%s unhealthy.  Content: %s', ip, result.content)
            instance_record['status'] = 'STAGING'
          else:
            logging.debug('%s healthy!', ip)


    json_instances = json.dumps(instance_dict)
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json_instances)

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def post(self):
    """Start instances with the given startup script.

    Uses app engine app identity to retrieve an access token for the app
    engine service account. No client OAuth required.
    """

    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
    gce_project = gce.GceProject(oauth_decorator.credentials,
                                 project_id=gce_project_id,
                                 zone_name=gce_zone_name)

    # Create the firewall if it doesn't exist.
    firewalls = gce_project.list_firewalls()
    firewall_names = [firewall.name for firewall in firewalls]
    if not FIREWALL in firewall_names:
      firewall = gce.Firewall(
          name=FIREWALL,
          target_tags=[DEMO_NAME],
          description=FIREWALL_DESCRIPTION)
      gce_project.insert(firewall)

    custom_image = self._has_custom_image(gce_project)

    # Get the list of instances to insert.
    num_instances = int(self.request.get('num_instances'))
    instances = self._get_instance_list(
        gce_project, num_instances, custom_image)

    gce_appengine.GceAppEngine().run_gce_request(
        self,
        gce_project.bulk_insert,
        'Error inserting instances: ',
        resources=instances)

  def _has_custom_image(self, gce_project):
    """Returns true if the project has a custom image.

    Args:
      gce_project: An isntance of gce.GceProject
    """
    images = gce_project.list_images(filter='name eq ^%s-$' % IMAGE)
    return bool(images)

  def _get_instance_metadata(self):
    """The metadata values to pass into the instance."""
    inline_values = {
      'goargs': GO_ARGS,
    }

    file_values = {
      'startup-script': STARTUP_SCRIPT,
      'goprog': GO_PROGRAM,
    }

    metadata = []
    for k, v in inline_values.items():
      metadata.append({'key': k, 'value': v})

    for k, fv in file_values.items():
      v = open(fv, 'r').read()
      metadata.append({'key': k, 'value': v})
    return metadata

  def _get_instance_list(self, gce_project, num_instances, custom_image):
    """Get a list of instances to start.

    Args:
      gce_project: An instance of gce.GceProject.
      num_instances: The number of instances to start.
      custom_image: boolean if we should use a custom image

    Returns:
      A list of gce.Instances.
    """

    image_name = None
    image_project_id = 'google'
    if custom_image:
      image_name = IMAGE
      image_project_id = gce.project_id

    instance_list = []
    for i in range(num_instances):
      instance = gce.Instance(
          name='%s-%02d' % (self.InstancePrefix(), i),
          machine_type_name=MACHINE_TYPE,
          image_name=image_name,
          image_project_id=image_project_id,
          tags=[DEMO_NAME],
          metadata=self._get_instance_metadata(),
          service_accounts=gce_project.settings['cloud_service_account'])
      instance_list.append(instance)
    return instance_list


class Cleanup(RequestHandler):
  """Stop instances."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def post(self):
    """Stop instances using the gce_appengine helper class."""
    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
    gce_project = gce.GceProject(oauth_decorator.credentials,
                                 project_id=gce_project_id,
                                 zone_name=gce_zone_name)
    gce_appengine.GceAppEngine().delete_demo_instances(
        self, gce_project, self.InstancePrefix())


app = webapp2.WSGIApplication(
    [
        ('/%s' % DEMO_NAME, Fractal),
        ('/%s/instance' % DEMO_NAME, Instance),
        ('/%s/cleanup' % DEMO_NAME, Cleanup),
        (data_handler.url_path, data_handler.data_handler),
    ], debug=True)
