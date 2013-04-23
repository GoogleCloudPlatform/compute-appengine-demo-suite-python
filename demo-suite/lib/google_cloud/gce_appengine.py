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

"""GCE App Engine Helper class."""

import json
import logging

import gce_exception as error

MAX_RESULTS = 100

class GceAppEngine(object):
  """Contains generic GCE methods for demos."""

  def list_demo_instances(self, request_handler, gce_project, demo_name):
    """Retrieves instance list for the demo.

    Sends the instance list in the response as a JSON object, mapping instance
    name to status.

    Args:
      request_handler: An instance of webapp2.RequestHandler.
      gce_project: An object of type gce.GceProject.
      demo_name: The string name of the demo.
    """

    instances = self.run_gce_request(
        request_handler,
        gce_project.list_instances,
        'Error listing instances: ',
        filter='name eq ^%s.*' % demo_name,
        maxResults=MAX_RESULTS)

    # Compare to None here because instances could be an empty dictionary.
    if instances is not None:
      instance_dict = {}
      for instance in instances:
        instance_dict[instance.name] = {'status': instance.status}
      json_instances = json.dumps(instance_dict)
      request_handler.response.headers['Content-Type'] = 'application/json'
      request_handler.response.out.write(json_instances)

  def delete_demo_instances(self, request_handler, gce_project, demo_name):
    """Deletes instances for the demo.

    First retrieves an instance list with instance names starting with the
    demo name. A bulk request is then sent to delete all these instances.

    Args:
      request_handler: An instance of webapp2.RequestHandler.
      gce_project: An object of type gce.GceProject.
      demo_name: The string name of the demo.
    """

    instances = self.run_gce_request(
        request_handler,
        gce_project.list_instances,
        'Error listing instances: ',
        filter='name eq ^%s.*' % demo_name,
        maxResults=MAX_RESULTS)

    if instances:
      response = self.run_gce_request(
          request_handler,
          gce_project.bulk_delete,
          'Error deleting instances: ',
          resources=instances)

      if response:
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('stopping cluster')

  def run_gce_request(self, request_handler, gce_method, error_message, **args):
    """Run a GCE Project list, insert, delete method.

    Any extra args are used as arguments for the gce_method.

    Args:
      request_handler: An instance of webapp2.RequestHandler.
      gce_method: A method within gce.GceProject to run.
      error_message: A string error message to prepend an error message,
          should an error occur.

    Returns:
      The response object, if the API call was successful.
    """

    response = None
    try:
      response = gce_method(**args)
    except error.GceError, e:
      logging.error(error_message + e.message)
      request_handler.response.set_status(500, error_message + e.message)
      return
    except error.GceTokenError:
      request_handler.response.set_status(401, 'Unauthorized.')
      return
    return response
