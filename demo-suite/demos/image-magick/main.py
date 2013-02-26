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

"""Image Magick demo."""

from __future__ import with_statement

__author__ = 'kbrisbin@google.com (Kathryn Hurley)'

import json
import os
import random

import lib_path
import google_cloud.gce as gce
import google_cloud.gce_exception as error
import google_cloud.gcs_appengine as gcs_appengine
import google_cloud.oauth as oauth
import jinja2
import oauth2client.appengine as oauth2client
import user_data
import webapp2

from google.appengine.api import users

DEMO_NAME = 'image-magick'
IMAGE = 'image-magick-demo-image'
IMAGES = ['android', 'appengine', 'apps', 'chrome', 'games', 'gplus',
          'maps', 'wallet', 'youtube']
SEQUENCES = ['5 5 360', '355 -5 0']
DEFAULT_SCOPES = ['https://www.googleapis.com/auth/devstorage.full_control']
MAX_RESULTS = 100

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(''))
oauth_decorator = oauth.decorator
user_data.DEFAULTS[user_data.GCS_BUCKET]['label'] += (' (must have CORS and '
                                                      'public-read ACLs set)')
parameters = [
    user_data.DEFAULTS[user_data.GCE_PROJECT_ID],
    user_data.DEFAULTS[user_data.GCS_PROJECT_ID],
    user_data.DEFAULTS[user_data.GCS_BUCKET],
    user_data.DEFAULTS[user_data.GCS_DIRECTORY],
]
data_handler = user_data.DataHandler(DEMO_NAME, parameters)


class ImageMagick(webapp2.RequestHandler):
  """Show main page for the Image Magick demo."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get(self):
    """Display the main page for the Image Magick demo."""

    if not oauth_decorator.credentials.refresh_token:
      self.redirect(oauth_decorator.authorize_url() + '&approval_prompt=force')

    gcs_bucket = data_handler.stored_user_data[user_data.GCS_BUCKET]
    gcs_directory = data_handler.stored_user_data.get(
        user_data.GCS_DIRECTORY, None)
    variables = {
        'demo_name': DEMO_NAME,
        'bucket': gcs_bucket,
        'directory': gcs_directory,
    }
    template = jinja_environment.get_template(
        'demos/%s/templates/index.html' % DEMO_NAME)
    self.response.out.write(template.render(variables))


class Instance(webapp2.RequestHandler):
  """Start and list instances."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get(self):
    """Get and return the list of instances with names containing the tag."""

    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_project = gce.GceProject(
        oauth_decorator.credentials, project_id=gce_project_id)

    try:
      instances = gce_project.list_instances(
            filter='name eq ^%s.*' % DEMO_NAME, maxResults=MAX_RESULTS)
    except error.GceError, e:
      self.response.set_status(500, 'Error listing instances: ' + e.message)
      self.response.headers['Content-Type'] = 'application/json'
      return
    except error.GceTokenError:
      self.response.set_status(401, 'Unauthorized.')
      self.response.headers['Content-Type'] = 'application/json'
      return

    instance_dict = {}
    for instance in instances:
      instance_dict[instance.name] = {'status': instance.status}
    json_instances = json.dumps(instance_dict)
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json_instances)

  @data_handler.data_required
  def post(self):
    """Insert instances with a startup script, metadata, and scopes.

    Startup script is randomly chosen to either rotate images left or right.
    Metadata includes the image to rotate, the demo name tag, and the machine
    number. Service account scopes include Compute and storage.
    """

    user = users.get_current_user()
    credentials = oauth2client.StorageByKeyName(
        oauth2client.CredentialsModel, user.user_id(), 'credentials').get()
    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_project = gce.GceProject(credentials, project_id=gce_project_id)

    # Get the bucket info for the instance metadata.
    gcs_bucket = data_handler.stored_user_data[user_data.GCS_BUCKET]
    gcs_directory = data_handler.stored_user_data.get(
        user_data.GCS_DIRECTORY, None)
    gcs_path = None
    if gcs_directory:
      gcs_path = '%s/%s' % (gcs_bucket, gcs_directory)
    else:
      gcs_path = gcs_bucket

    instances = []
    num_instances = int(self.request.get('num_instances'))
    for i in range(num_instances):
      startup_script = os.path.join(os.path.dirname(__file__), 'startup.sh')
      instances.append(gce.Instance(
          name='%s-%d' % (DEMO_NAME, i),
          image_name=IMAGE,
          image_project=gce_project_id,
          service_accounts=gce_project.settings['cloud_service_account'],
          metadata=[{
              'key': 'startup-script', 'value': open(startup_script, 'r').read()
          }, {
              'key': 'image', 'value': random.choice(IMAGES)
          }, {
              'key': 'seq', 'value': random.choice(SEQUENCES)
          }, {
              'key': 'machine-num', 'value': i
          }, {
              'key': 'tag', 'value': DEMO_NAME
          }, {
              'key': 'gcs-path', 'value': gcs_path}]))

    try:
      gce_project.bulk_insert(instances)
    except error.GceError, e:
      self.response.set_status(500, 'Error inserting instances: ' + e.message)
      self.response.headers['Content-Type'] = 'application/json'
      return
    except error.GceTokenError:
      self.response.set_status(401, 'Unauthorized.')
      self.response.headers['Content-Type'] = 'application/json'
      return

    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('starting cluster')


class GceCleanup(webapp2.RequestHandler):
  """Stop instances."""

  @data_handler.data_required
  def post(self):
    """Stop instances with names containing the tag."""

    user = users.get_current_user()
    credentials = oauth2client.StorageByKeyName(
        oauth2client.CredentialsModel, user.user_id(), 'credentials').get()
    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_project = gce.GceProject(credentials, project_id=gce_project_id)

    try:
      instances = gce_project.list_instances(
            filter='name eq ^%s.*' % DEMO_NAME, maxResults=MAX_RESULTS)
      gce_project.bulk_delete(instances)
    except error.GceError, e:
      self.response.set_status(500, 'Error inserting instances: ' + e)
      self.response.headers['Content-Type'] = 'application/json'
      return
    except error.GceTokenError:
      self.response.set_status(401, 'Unauthorized.')
      self.response.headers['Content-Type'] = 'application/json'
      return

    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('stopping cluster')


class GcsCleanup(webapp2.RequestHandler):
  """Remove Cloud Storage files."""

  @data_handler.data_required
  def post(self):
    """Remove all cloud storage contents from the given bucket and dir."""

    user_id = users.get_current_user().user_id()
    credentials = oauth2client.StorageByKeyName(
        oauth2client.CredentialsModel, user_id, 'credentials').get()
    gcs_project_id = data_handler.stored_user_data[user_data.GCS_PROJECT_ID]
    gcs_bucket = data_handler.stored_user_data[user_data.GCS_BUCKET]
    gcs_directory = data_handler.stored_user_data.get(
        user_data.GCS_DIRECTORY, None)
    gcs_helper = gcs_appengine.GcsAppEngineHelper(credentials, gcs_project_id)
    file_regex = None
    if gcs_directory:
      file_regex = r'^%s/%s.*' % (gcs_directory, DEMO_NAME)
    else:
      file_regex = r'^%s.*' % DEMO_NAME
    gcs_helper.delete_bucket_contents(
        gcs_bucket, gcs_directory, file_regex)
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write('cleaning cloud storage bucket')


app = webapp2.WSGIApplication(
    [
        ('/%s' % DEMO_NAME, ImageMagick),
        ('/%s/instance' % DEMO_NAME, Instance),
        ('/%s/gce-cleanup' % DEMO_NAME, GceCleanup),
        ('/%s/gcs-cleanup' % DEMO_NAME, GcsCleanup),
        (data_handler.url_path, data_handler.data_handler),
    ], debug=True, config={'config': 'imagemagick'})
