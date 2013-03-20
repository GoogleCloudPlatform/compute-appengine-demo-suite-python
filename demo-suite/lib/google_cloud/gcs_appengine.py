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

"""Gce App Engine helper methods to work with Compute Engine."""

__author__ = 'kbrisbin@google.com (Kathryn Hurley)'

import cs
import lib_path

from google.appengine.ext import deferred


class GcsAppEngineHelper(object):
  """Some helpful methods for working with Cloud Storage.

  Attributes:
    credentials: An oauth2client.client.Credentials object.
    project_id: A string name for the Cloud Storage project (this is a
        string of numbers).
  """

  def __init__(self, credentials, project_id):
    """Initializes the GcsAppEngineHelper class.

    Sets default values for class attributes.

    Args:
      credentials: An oauth2client.client.Credentials object.
      project_id: A string name for the Cloud Storage project (this is a
          string of numbers).
    """
    self.credentials = credentials
    self.project_id = project_id

  def delete_bucket_contents(self, bucket, directory=None, file_regex=None):
    """Deletes all the contents from a given bucket and directory path.

    Args:
      bucket: A string name of the Cloud Storage bucket.
      directory: A string name of the Cloud Storage 'directory'.
      file_regex: A regular expression to match against object names.
    """
    deferred.defer(cleanup_queue, self.credentials, self.project_id, bucket,
                   directory, file_regex)


def cleanup_queue(credentials, project_id, bucket, directory, file_regex=None):
  """Deletes all the contents from a given bucket and directory path.

  Args:
    credentials: An oauth2client.client.Credentials object.
    project_id: A string name for the Cloud Storage project (this is a
        string of numbers).
    bucket: A string name of the Cloud Storage bucket.
    directory: A string name of the Cloud Storage 'directory'.
    file_regex: A regular expression to match against object names.
  """
  cs.Cs(project_id).delete_bucket_contents(
      credentials.access_token, bucket, directory, file_regex)
