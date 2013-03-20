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

"""Cloud Storage library for uploading and deleting files."""

__author__ = 'kbrisbin@google.com (Kathryn Hurley)'

import datetime
import logging
import re
from xml.dom import minidom

from google.appengine.api import urlfetch

BASE_URL = 'https://storage.googleapis.com'
API_VERSION = '2'


class Cs(object):
  """Cloud Storage library.

  Attributes:
    project_id: A string name for the Cloud Storage project (this is a
        string of numbers).
  """

  def __init__(self, project_id):
    """Initializes the Cs object.

    Args:
      project_id: A string name for the Cloud Storage project (this is a
          string of numbers).
    """
    self.project_id = project_id

  def upload(self, oauth_token, bucket, object_name, payload,
             content_type='text/plain'):
    """Uploads an object to Cloud Storage in the given bucket.

    Args:
      oauth_token: String oauth token for sending authorized requests.
      bucket: String name of bucket in which to upload file.
      object_name: String name of the object.
      payload: File contents.
      content_type: String name describing the content type.
    Returns:
      The string result of the API call.
    """
    # TODO(kbrisbin): This hasn't been tested yet.
    url = '%s/%s/%s' % (BASE_URL, bucket, object_name)
    date = datetime.datetime.now()
    str_date = date.strftime('%b %d, %Y %H:%M:%S')
    result = urlfetch.fetch(
        url=url, payload=payload, method=urlfetch.PUT,
        headers={
            'Authorization': 'OAuth %s' % (oauth_token),
            'Date': str_date,
            'x-goog-project-id': self.project_id,
            'x-goog-api-version': API_VERSION,
            'Content-Type': content_type})
    return result.content

  def delete_bucket_contents(self, oauth_token, bucket, directory=None,
                             file_regex=None):
    """Deletes all the contents of a given bucket / directory.

    Args:
      oauth_token: String oauth token for sending authorized requests.
      bucket: String name of bucket in which to upload file.
      directory: A symbolic directory from which to delete objects.
      file_regex: A regular expression to match against object names.
    """
    url = '%s/%s' % (BASE_URL, bucket)
    if directory:
      url = '%s?prefix=%s/' % (url, directory)
    logging.info('Deleting files from: ' + url)
    date = datetime.datetime.now()
    str_date = date.strftime('%b %d, %Y %H:%M:%S')
    result = urlfetch.fetch(
        url=url, headers={
            'Authorization': 'OAuth %s' % (oauth_token),
            'Date': str_date,
            'x-goog-project-id': self.project_id,
            'x-goog-api-version': API_VERSION})
    dom = minidom.parseString(result.content)
    keys = dom.getElementsByTagName('Key')
    for key_element in keys:
      key = self._get_text(key_element.childNodes)
      if file_regex and not re.match(file_regex, key):
        continue
      url = '%s/%s/%s' % (BASE_URL, bucket, key)
      logging.info('Deleting: %s', url)
      result = urlfetch.fetch(
          url=url, method=urlfetch.DELETE, headers={
              'Authorization': 'OAuth %s' % (oauth_token),
              'Date': str_date,
              'x-goog-project-id': self.project_id,
              'x-goog-api-version': API_VERSION})

  def _get_text(self, nodes):
    """Concatenates the text from several XML nodes.

    Args:
      nodes: List of XML nodes.

    Returns:
      A string of concatenated text nodes.
    """
    rc = []
    for node in nodes:
      if node.nodeType == node.TEXT_NODE:
        rc.append(node.data)
    return ''.join(rc)
