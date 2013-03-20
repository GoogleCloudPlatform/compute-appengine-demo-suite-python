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
import google_cloud.oauth as oauth
import jinja2
import webapp2

from google.appengine.api import users

jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(''))
decorator = oauth.decorator


class Main(webapp2.RequestHandler):
  """Show the main page."""

  def get(self):
    """Show the main page."""
    template = jinja_environment.get_template('templates/index.html')
    logout_url = users.create_logout_url('/')
    self.response.out.write(template.render({'logout_url': logout_url}))


app = webapp2.WSGIApplication(
    [
        ('/', Main),
        (decorator.callback_path, decorator.callback_handler()),
    ], debug=True)
