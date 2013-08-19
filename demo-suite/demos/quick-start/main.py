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

"""Main page for the Google Compute Engine demo suite."""

from __future__ import with_statement

__author__ = 'kbrisbin@google.com (Kathryn Hurley)'

import lib_path
import logging
import google_cloud.gce as gce
import google_cloud.gce_appengine as gce_appengine
import google_cloud.oauth as oauth
import jinja2
import oauth2client.appengine as oauth2client
import time
import user_data
import webapp2

from google.appengine.ext import ndb
from google.appengine.api import users

DEMO_NAME = 'quick-start'

class Objective(ndb.Model):
  """ This data model keeps track of work in progress. """
  # Disable caching of objective.
  _use_memcache = False
  _use_cache = False

  # Desired number of VMs and start time. This will be >0 for a start
  # request or 0 for a reset/stop request.
  targetVMs = ndb.IntegerProperty()

  # Number of VMs started by last start request. This is handy when
  # recovering during a reset operation, so we can figure out how many 
  # instances to depict in the UI.
  startedVMs = ndb.IntegerProperty()

  # Epoch time when last/current request was stated.
  startTime = ndb.IntegerProperty()

def getObjective(project_id):
  key = ndb.Key("Objective", project_id)
  return key.get()

@ndb.transactional
def updateObjective(project_id, targetVMs):
  objective = getObjective(project_id)
  if not objective: 
    logging.info('objective not found, creating new, project=' + project_id)
    key = ndb.Key("Objective", project_id)
    objective = Objective(key=key)
  objective.targetVMs = targetVMs
  # Overwrite startedVMs only when starting, skip when stopping.
  if targetVMs > 0:
    objective.startedVMs = targetVMs 
  objective.startTime = int(time.time())
  objective.put()

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(''))
oauth_decorator = oauth.decorator
parameters = [
    user_data.DEFAULTS[user_data.GCE_PROJECT_ID],
    user_data.DEFAULTS[user_data.GCE_ZONE_NAME]
]
data_handler = user_data.DataHandler(DEMO_NAME, parameters)


class QuickStart(webapp2.RequestHandler):
  """Show main Quick Start demo page."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get(self):
    """Displays the main page for the Quick Start demo. Auth required."""

    if not oauth_decorator.credentials.refresh_token:
      self.redirect(oauth_decorator.authorize_url() + '&approval_prompt=force')

    targetVMs = 5
    startedVMs = 5
    startTime = 0

    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    objective = getObjective(gce_project_id)
    if objective:
      (targetVMs, startedVMs, startTime) = (objective.targetVMs, 
        objective.startedVMs, objective.startTime)

    variables = {
      'demo_name': DEMO_NAME,
      'targetVMs': targetVMs,
      'startedVMs': startedVMs,
      'startTime': startTime
    }
    template = jinja_environment.get_template(
        'demos/%s/templates/index.html' % DEMO_NAME)
    self.response.out.write(template.render(variables))


class Instance(webapp2.RequestHandler):
  """List or start instances."""

  @oauth_decorator.oauth_required
  @data_handler.data_required
  def get(self):
    """List instances using the gce_appengine helper class.

    Return the results as JSON mapping instance name to status.
    """

    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
    gce_project = gce.GceProject(
        oauth_decorator.credentials, project_id=gce_project_id,
        zone_name=gce_zone_name)
    gce_appengine.GceAppEngine().list_demo_instances(
        self, gce_project, DEMO_NAME)

  @data_handler.data_required
  def post(self):
    """Start instances using the gce_appengine helper class."""

    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
    user_id = users.get_current_user().user_id()
    credentials = oauth2client.StorageByKeyName(
        oauth2client.CredentialsModel, user_id, 'credentials').get()
    gce_project = gce.GceProject(credentials, project_id=gce_project_id,
        zone_name=gce_zone_name)

    num_instances = int(self.request.get('num_instances'))
    instances = [gce.Instance('%s-%d' % (DEMO_NAME, i))
                 for i in range(num_instances)]
    response = gce_appengine.GceAppEngine().run_gce_request(
        self,
        gce_project.bulk_insert,
        'Error inserting instances: ',
        resources=instances)

    # Record objective in datastore so we can recover work in progress.
    updateObjective(gce_project_id, num_instances)

    if response:
      self.response.headers['Content-Type'] = 'text/plain'
      self.response.out.write('starting cluster')


class Cleanup(webapp2.RequestHandler):
  """Stop instances."""

  @data_handler.data_required
  def post(self):
    """Stop instances using the gce_appengine helper class."""
    gce_project_id = data_handler.stored_user_data[user_data.GCE_PROJECT_ID]
    gce_zone_name = data_handler.stored_user_data[user_data.GCE_ZONE_NAME]
    user_id = users.get_current_user().user_id()
    credentials = oauth2client.StorageByKeyName(
        oauth2client.CredentialsModel, user_id, 'credentials').get()
    gce_project = gce.GceProject(credentials, project_id=gce_project_id,
        zone_name=gce_zone_name)
    gce_appengine.GceAppEngine().delete_demo_instances(
        self, gce_project, DEMO_NAME)

    # Record reset objective in datastore so we can recover work in progress.
    updateObjective(gce_project_id, 0)

app = webapp2.WSGIApplication(
    [
        ('/%s' % DEMO_NAME, QuickStart),
        ('/%s/instance' % DEMO_NAME, Instance),
        ('/%s/cleanup' % DEMO_NAME, Cleanup),
        (data_handler.url_path, data_handler.data_handler),
    ],
    debug=True)
