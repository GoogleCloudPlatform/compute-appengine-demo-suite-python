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

"""Models and handlers to store users' information in the datastore."""

__author__ = 'kbrisbin@google.com (Kathryn Hurley)'

import json
import logging
import threading

import jinja2
import webapp2

from google.appengine.api import users
from google.appengine.ext import db

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(''))

GCE_PROJECT_ID = 'gce-project-id'
GCE_ZONE_NAME = 'gce-zone-name'
GCS_PROJECT_ID = 'gcs-project-id'
GCS_BUCKET = 'gcs-bucket'
GCS_DIRECTORY = 'gcs-directory'
DEFAULTS = {
    GCE_PROJECT_ID: {
        'type': 'string',
        'required': True,
        'label': 'Compute Engine Project ID (e.g.: compute-engine-project)',
        'name': GCE_PROJECT_ID
    },
    GCE_ZONE_NAME: {
        'type': 'string',
        'required': True,
        'label': 'Compute Engine Zone (e.g.: us-central2-a)',
        'name': GCE_ZONE_NAME
    },
    GCS_PROJECT_ID: {
        'type': 'string',
        'required': True,
        'label': ('Cloud Storage Project ID (e.g.: 123456. Must be the same '
                  'project as the Compute Engine project)'),
        'name': GCS_PROJECT_ID
    },
    GCS_BUCKET: {
        'type': 'string',
        'required': True,
        'label': 'Cloud Storage Bucket Name',
        'name': GCS_BUCKET
    },
    GCS_DIRECTORY: {
        'type': 'string',
        'required': False,
        'label': 'Cloud Storage Directory',
        'name': GCS_DIRECTORY
    }
}

URL_PATH = '/%s/project'


class JsonProperty(db.Property):
  """JSON data stored in database.

  From - http://snipplr.com/view.php?codeview&id=10529
  """

  data_type = db.TextProperty

  def get_value_for_datastore(self, model_instance):
    """Get the value to save in the data store.

    Args:
      model_instance: An dictionary instance of the model.

    Returns:
      The string representation of the database value.
    """
    value = super(JsonProperty, self).get_value_for_datastore(model_instance)
    return self._deflate(value)

  def validate(self, value):
    """Validate the value.

    Args:
      value: The value to validate.

    Returns:
      The dictionary (JSON object).
    """
    return self._inflate(value)

  def make_value_from_datastore(self, value):
    """Create a JSON object from the value in the datastore.

    Args:
      value: The string value in the datastore.

    Returns:
      The dictionary (JSON object).
    """
    return self._inflate(value)

  def _inflate(self, value):
    """Convert the value to a dictionary.

    Args:
      value: The string value to convert to a dictionary.

    Returns:
      The dictionary (JSON object).
    """
    if value is None:
      return {}
    if isinstance(value, unicode) or isinstance(value, str):
      return json.loads(value)
    return value

  def _deflate(self, value):
    """Convert the dictionary to string.

    Args:
      value: A dictionary.

    Returns:
      The string representation of the dictionary.
    """
    return json.dumps(value)


class UserData(db.Model):
  """Store the user data."""
  user = db.UserProperty(required=True)
  user_data = JsonProperty()


class DataHandler(object):
  """Store user data in database."""

  def set_stored_user_data(self, stored_user_data):
    self._tls.stored_user_data = stored_user_data

  def get_stored_user_data(self):
     return self._tls.stored_user_data

  stored_user_data = property(get_stored_user_data, set_stored_user_data)

  def __init__(self, demo_name, parameters, redirect_uri=None):
    """Initializes the DataHandler class.

    An example of default parameters can be seen above. Each parameter is
    a dictionary. Fields include: type (the data type - not currently used,
    but will be useful for validation later), required (whether or not the
    data is required), label (a label for the HTML form), and name (the
    key for the JSON object in the database, and the name attribute in the
    HTML form).

    Demos can create additional parameters as needed. The data will be stored
    in the database indexed by user. All data is available to any other demo.

    Args:
      demo_name: The string name of the demo.
      parameters: A list of dictionaries specifying what data to store in the
          database for the current user.
      redirect_uri: The string URL to redirect to after a successful POST
          to store data in the database. Defaults to /<demo-name> if None.
    """
    self._tls = threading.local()
    self._demo_name = demo_name
    self._parameters = parameters
    if redirect_uri:
      self._redirect_uri = redirect_uri
    else:
      self._redirect_uri = '/' + self._demo_name
    self.stored_user_data = {}

  @property
  def url_path(self):
    """The path for the User Data handler.

    Formatted as /<demo-name>/project.

    Returns:
      The path as a string.
    """
    return URL_PATH % self._demo_name

  def data_required(self, method):
    """Decorator to check if required user information is available.

    Redirects to form if info is not available.

    Args:
      method: callable function.

    Returns:
      Callable decorator function.
    """

    def check_data(request_handler, *args, **kwargs):
      """Checks for required data and redirects to form if not present..

      Args:
        request_handler: The app engine request handler method.
        *args: Any request arguments.
        **kwargs: Any request parameters.

      Returns:
        Callable function.
      """
      user = users.get_current_user()
      if not user:
        return webapp2.redirect(
            users.create_login_url(request_handler.request.uri))

      user_data = UserData.all().filter('user =', user).get()
      if user_data:
        self.stored_user_data = user_data.user_data

      for parameter in self._parameters:
        if parameter['required']:
          if not (user_data and user_data.user_data.get(parameter['name'])):
            return webapp2.redirect(self.url_path)

      try:
        return method(request_handler, *args, **kwargs)
      finally:
        self.stored_user_data = {}

    return check_data

  def data_handler(self, request):
    """Store user project information in the database.

    Args:
      request: The HTTP request.

    Returns:
      The webapp2.Response object.
    """

    response = webapp2.Response()

    user = users.get_current_user()
    if user:
      if request.method == 'POST':
        return self._handle_post(request, user)

      elif request.method == 'GET':
        response = self._handle_get(response, user)

      else:
        response.set_status(405)
        response.headers['Content-Type'] = 'application/json'
        response.out.write({'error': 'Method not allowed.'})

    else:
      response.set_status(401)
      response.headers['Content-Type'] = 'application/json'
      response.write({'error': 'User not logged in.'})

    return response

  def _handle_get(self, response, user):
    """Handles GET requests and displays a form.

    Args:
      response: A webapp2.Response object.
      user: The current user.

    Returns:
      The modified webapp2.Response object.
    """

    user_data = UserData.all().filter('user =', user).get()

    variables = {'demo_name': self._demo_name}
    variables['user_entered'] = {}
    if user_data:
      for data in user_data.user_data:
        variables['user_entered'][data] = user_data.user_data[data]
    variables['parameters'] = self._parameters

    template = jinja_environment.get_template('templates/project.html')
    response.out.write(template.render(variables))
    return response

  def _handle_post(self, request, user):
    """Handles POST requests from the project form.

    Args:
      request: The HTTP request.
      user: The current user.

    Returns:
      A redirect to the redirect URI.
    """

    user_data = UserData.all().filter('user =', user).get()
    new_user_data = {}
    if user_data:
      new_user_data = user_data.user_data

    for data in self._parameters:
      entered_value = request.get(data['name'])
      if not entered_value and data['required']:
        webapp2.redirect(URL_PATH)
      new_user_data[data['name']] = entered_value

    if user_data:
      user_data.user_data = new_user_data
      user_data.save()
    else:
      user_data = UserData(user=user, user_data=new_user_data)
      user_data.put()

    return webapp2.redirect(self._redirect_uri)
