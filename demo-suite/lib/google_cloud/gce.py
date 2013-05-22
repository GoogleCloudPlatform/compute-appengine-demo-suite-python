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

"""Gce classes and methods to manage Compute Engine resources."""

__author__ = 'kbrisbin@google.com (Kathryn Hurley)'

import logging
import os

import lib_path
from apiclient import discovery
from apiclient import errors as api_errors
from apiclient import http
import httplib2
import oauth2client.client as client
try:
  import simplejson as json
except ImportError:
  import json

import gce_exception as error

API = 'compute'
GCE_URL = 'https://www.googleapis.com/%s' % API
GOOGLE_PROJECT = 'google'


class GceProject(object):
  """Gce classes and methods to work with Compute Engine.

  Attributes:
    settings: Dictionary of settings as set in the settings.json file.
    gce_url: The string URL of the Compute Engine API endpoint.
    project_id: A string name for the Compute Engine project.
    zone_name: A string name for the default zone.
    service: An apiclient.discovery.Resource object for Compute Engine.
  """

  def __init__(
      self, credentials, project_id=None, zone_name=None, settings=None):
    """Initializes the GceProject class.

    Sets default values for class attributes. See the instance resource for
    more information:

    https://developers.google.com/compute/docs/reference/v1beta14/instances

    Args:
      credentials: An oauth2client.client.Credentials object.
      project_id: A string name for the Compute Engine project.
      zone_name: The string name of the zone.
      settings: A dictionary of GCE settings. These settings will override
          any settings in the settings.json file. See the settings.json file for
          key names.
    """

    settings_file = os.path.join(
        os.path.dirname(__file__), '../../settings.json')
    self.settings = json.loads(open(settings_file, 'r').read())
    if settings:
      self.settings.update(settings)

    self.gce_url = '%s/%s' % (GCE_URL, self.settings['compute']['api_version'])

    discovery_doc_path = 'discovery/compute/%s.json' % self.settings['compute']['api_version']
    discovery_doc = open(discovery_doc_path, 'r').read()

    auth_http = self._auth_http(credentials)
    self.service = discovery.build_from_document(
        discovery_doc, self.settings['compute']['api_version'], http=auth_http)

    self.project_id = project_id
    if not self.project_id:
      self.project_id = self.settings['project']

    self.zone_name = zone_name
    if not self.zone_name:
      self.zone_name = self.settings['compute']['zone']

  def list_instances(self, zone_name=None, **args):
    """Lists all instances for a project and zone with an optional filter.

    Args represent any optional parameters for the list instances request.
    See the API documentation:

    https://developers.google.com/compute/docs/reference/v1beta14/instances/list

    Args:
      zone_name: The zone in which to query.

    Returns:
      A list of Instance objects.
    """
    return self._list(Instance, zone_name=zone_name, **args)

  def list_firewalls(self, **args):
    """Lists all firewalls for a project.

    Args represent any optional parameters for the list firewalls request.
    See the API documentation:

    https://developers.google.com/compute/docs/reference/v1beta14/firewalls/list

    Returns:
      A list of Firewall objects.
    """

    return self._list(Firewall, **args)

  def list_images(self, **args):
    """Lists all images for a project.

    Args represent any optional parameters for the list images request.
    See the API documentation:

    https://developers.google.com/compute/docs/reference/v1beta14/images/list

    Returns:
      A list of Image objects.
    """

    return self._list(Image, **args)

  def list_disks(self, **args):
    """Lists all disks for a project.

    Args represent any optional parameters for the list disks request.
    See the API documentation:

    https://developers.google.com/compute/docs/reference/v1beta14/disks/list

    Returns:
      A list of Disk objects.
    """

    return self._list(Disk, **args)

  def insert(self, resource):
    """Insert a resource into the GCE project.

    Args:
      resource: A GceResource object.

    Raises:
      GceError: Raised when API call fails.
      GceTokenError: Raised when the access token fails to refresh.
    """

    resource.gce_project = self
    request = self._insert_request(resource)

    try:
      self._run_request(request)
    except error.GceError:
      raise
    except error.GceTokenError:
      raise

  def bulk_insert(self, resources):
    """Insert multiple resources using a batch request.

    Args:
      resources: A list of GceResource objects.

    Raises:
      GceError: Raised when API call fails.
      GceTokenError: Raised when the access token fails to refresh.
    """

    batch = http.BatchHttpRequest()
    for resource in resources:
      resource.gce_project = self
      batch.add(self._insert_request(resource), callback=self._batch_response)

    try:
      self._run_request(batch)
    except error.GceError:
      raise
    except error.GceTokenError:
      raise

  def bulk_delete(self, resources):
    """Delete resources using a batch request.

    Args:
      resources: A list of GceResource objects.

    Raises:
      GceError: Raised when API call fails.
      GceTokenError: Raised when the access token fails to refresh.
    """

    batch = http.BatchHttpRequest()
    for resource in resources:
      resource.gce_project = self
      batch.add(self._delete_request(resource), callback=self._batch_response)

    try:
      self._run_request(batch)
    except error.GceError:
      raise
    except error.GceTokenError:
      raise

  def _list(self, resource_class, zone_name=None, **args):
    """Get a list of all project resources of type resource_class.

    Args:
      resource_class: A class of type GceResource.
      zone_name: A string zone to apply to the request, if applicable.

    Returns:
      A list of resource_class objects.

    Raises:
      GceError: Raised when API call fails.
      GceTokenError: Raised when the access token fails to refresh.
    """

    resources = []
    resource = resource_class()
    resource.gce_project = self

    request = self._list_request(resource, zone_name=zone_name, **args)
    while request:
      results = {}
      try:
        results = self._run_request(request)
      except error.GceError:
        raise
      except error.GceTokenError:
        raise

      for result in results.get('items', []):
        new_resource = resource_class()
        new_resource.from_json(result)
        resources.append(new_resource)

      request = resource.service_resource().list_next(
          self._list_request(resource, zone_name=zone_name, **args),
          results)

    return resources

  def _insert_request(self, resource):
    """Construct an insert request for the resource.

    Args:
      resource: A GceResource object.

    Returns:
      The insert method of the apiclient.discovery.Resource object.
    """

    resource.set_defaults()
    params = {'project': self.project_id, 'body': resource.json}
    if resource.scope == 'zonal':
      params['zone'] = self.zone_name
    return resource.service_resource().insert(**params)

  def _list_request(self, resource, zone_name=None, **args):
    """Construct an insert request for the resource.

    Args:
      resource: A GceResource object.
      zone_name: The string zone name. Only applicable for zonal resources.

    Returns:
      The list method of the apiclient.discovery.Resource object.
    """

    params = {'project': self.project_id}
    if args:
      params.update(args)
    if resource.scope == 'zonal':
      if not zone_name:
        zone_name = self.zone_name
      params['zone'] = zone_name
    return resource.service_resource().list(**params)

  def _delete_request(self, resource):
    """Return the delete method of the apiclient.discovery.Resource object.

    Args:
      resource: A GceResource object.

    Returns:
      The delete method of the apiclient.discovery.Resource object.
    """

    resource.set_defaults()
    params = {'project': self.project_id, resource.type: resource.name}
    if resource.scope == 'zonal':
      params['zone'] = self.zone_name
    return resource.service_resource().delete(**params)

  def _run_request(self, request):
    """Run API request and handle any errors.

    Args:
      request: An apiclient.http.HttpRequest object.

    Returns:
      Dictionary results of the API call.

    Raises:
      GceError: Raised if API call fails.
      GceTokenError: Raised if there's a failure refreshing the access token.
    """

    result = {}
    try:
      result = request.execute()
    except httplib2.HttpLib2Error, e:
      logging.error(e)
      raise error.GceError('Transport Error occurred')
    except client.AccessTokenRefreshError, e:
      logging.error(e)
      raise error.GceTokenError('Access Token refresh error')
    except api_errors.BatchError, e:
      logging.error(e)
      logging.error('BatchError: %s %s' % (e.resp.status, e.content))
      if e.resp.status != 200:
        raise error.GceError(
            'Batch Error: %s %s' % (e.resp.status, e.resp.reason))
    except api_errors.HttpError, e:
      logging.error(e)
      raise error.GceError(
          'HttpError: %s %s' % (e.resp.status, e.resp.reason))
    return result

  def _batch_response(self, request_id, response, exception):
    """Log information about the batch request response.

    Args:
      request_id: The string request id.
      response: A deserialized response object.
      exception: An apiclient.errors.HttpError exception object if an error
          occurred while processing the request.
    """

    if exception is not None:
      logging.error(exception)
      logging.error('API Request Error! ' + str(response))

  def _auth_http(self, credentials):
    """Authorize an instance of httplib2.Http using credentials.

    Args:
      credentials: An oauth2client.client.Credentials object.

    Returns:
      An authorized instance of httplib2.Http.
    """

    http = httplib2.Http(timeout=30)
    auth_http = credentials.authorize(http)
    return auth_http


class GceResource(object):
  """A GCE resource belonging to a GCE project.

  Attributes:
    type: The string name of the resource type (ex: instance, firewall).
    scope: The string name of the scope (ex: zonal, global).
  """

  def __init__(self, type, scope):
    """Initializes the GceResource class.

    Args:
      type: The string name of the resource type (ex: instance, firewall).
      scope: The string name of the scope (ex: zonal, global).
    """

    self.type = type
    self.scope = scope

  @property
  def url(self):
    """Generate the fully-qualified URL of the resource.

    Returns:
      The string fully-qualified URL.
    """

    project_id = None
    if self.type == 'image':
      project_id = self.project_id
    else:
      project_id = self.gce_project.project_id

    if self.scope == 'zonal':
      return '%s/projects/%s/zones/%s/%ss/%s' % (
          self.gce_project.gce_url,
          project_id,
          self.zone.name,
          self.type,
          self.name)

    if self.scope == 'global':
      return '%s/projects/%s/global/%ss/%s' % (
          self.gce_project.gce_url,
          project_id,
          self.type,
          self.name)

  def set_defaults(self):
    """Set any defaults."""

    if not self.name:
      if self.type == 'machineType':
        self.name = self.gce_project.settings['compute']['machine_type']
      else:
        self.name = self.gce_project.settings['compute'][self.type]

class DiskMount(object):
  """A class for mounting options of a disk into a VM.
  Attributes:
    mount_type: EPHEMERAL or PERSISTENT
    mode: READ_WRITE or READ_ONLY
    disk: A disk resource for persistent disk.
    device_name: A unique device name.
    boot: Is this a boot disk?
  """

  def __init__(self,
               mount_type='PERSISTENT',
               mode='READ_WRITE',
               disk=None,
               device_name=None,
               boot=False):
    """Initialize the DiskMount class."""
    self.mount_type = mount_type
    self.mode = mode
    if type(disk) is Disk:
      self.disk = disk
    else:
      self.disk = Disk(disk)
    self.device_name = device_name
    self.boot = boot

  @property
  def json(self):
    """Create a json representation of the resource.

    Returns:
      A dictionary representing the resource.
    """

    mount = {
        'type': self.mount_type,
        'mode': self.mode,
        'boot': self.boot
    }
    if self.disk:
      mount['source'] = self.disk.url
    if self.device_name:
      mount['deviceName'] = self.device_name
    return mount

  def from_json(self, json_resource):
    """Sets member variables from a dictionary representing an disk mount.

    Args:
      json_resource: A dictionary representing the disk mount.
    """

    self.mount_type = json_resource['type']
    self.mode = json_resource['mode']
    if json_resource.get('boot'):
      self.boot = json_resource['boot']
    if json_resource.get('source'):
      self.disk = Disk(json_resource['source'].split('/')[-1])
    if json_resource.get('device_name'):
      self.device_name = json_resource('deviceName')

  def set_defaults(self):
    """Set any defaults before insert."""
    if self.disk and not self.disk.name:
      self.disk.set_defaults()

  def set_gce_project(self, gce_project):
    """Set the GceProject into this object."""
    if self.disk:
      self.disk.gce_project = gce_project


class Instance(GceResource):
  """A class representing a GCE Instance resource.

  Attributes:
    name: The string name of the instance.
    zone: An object of type Zone representing the instance's zone.
    description: A string description of the instance.
    tags: A list of string tags for the instance.
    image: An object of type Image representing the instance's image.
    kernel: The kernel resource to boot from.
    machine_type: An object of type MachineType representing the instance's
        machine type.
    network_interfaces: A list of dictionaries representing the instance's
        network interfaces.
    disk_mounts: A list of disk mount objects
    metadata: A list of dictionaries representing the instance's metadata.
    service_accounts: A list of dictionaries representing the instance's
        service accounts.
  """

  def __init__(self,
               name=None,
               zone_name=None,
               description=None,
               tags=None,
               image_name=None,
               image_project_id=GOOGLE_PROJECT,
               kernel=None,
               machine_type_name=None,
               network_interfaces=None,
               disk_mounts=None,
               metadata=None,
               service_accounts=None):
    """Initializes the Instance class.

    Args:
      name: The string name of the instance.
      zone_name: The string name of the zone.
      description: The string description of the instance.
      tags: A list of string tags for the instance.
      image_name: A string name of the image.
      image_project: The string name of the project owning the image.
      kernel: The kernel resource to boot from.
      machine_type_name: A string name of the machine type.
      network_interfaces: A list of dictionaries representing the instance's
          network interfaces.
      disks: A list of dictionaries representing the instance's disks.
      metadata: A list of dictionaries representing the instance's metadata.
      service_accounts: A list of dictionaries representing the instance's
          service accounts.
    """

    super(Instance, self).__init__('instance', 'zonal')
    self.name = name
    self.zone = Zone(zone_name)
    self.description = description
    self.tags = tags
    if image_name:
      self.image = Image(image_name, image_project_id)
    else:
      self.image = None
    self.kernel = kernel
    self.machine_type = MachineType(machine_type_name)
    self.network_interfaces = network_interfaces
    self.disk_mounts = disk_mounts or []
    self.metadata = metadata
    self.service_accounts = service_accounts

  @property
  def json(self):
    """Create a json representation of the resource.

    Returns:
      A dictionary representing the resource.
    """

    instance = {
        'name': self.name,
        'machineType': self.machine_type.url,
        'networkInterfaces': self.network_interfaces
    }
    if self.description:
      instance['description'] = self.description
    if self.tags:
      instance['tags'] = {'items': self.tags}
    if self.image:
        instance['image'] = self.image.url,
    if self.kernel:
      instance['kernel'] = self.kernel
    if self.disk_mounts:
      instance['disks'] = [m.json for m in self.disk_mounts]
    if self.metadata:
      instance['metadata'] = {'items': self.metadata}
    if self.service_accounts:
      instance['serviceAccounts'] = self.service_accounts
    return instance

  def from_json(self, json_resource):
    """Sets member variables from a dictionary representing an instance.

    Args:
      json_resource: A dictionary representing the instance.
    """

    self.name = json_resource['name']
    self.zone_name = Zone(json_resource['zone'].split('/')[-1])
    self.machine_type = MachineType(json_resource['machineType'].split('/')[-1])
    self.network_interfaces = json_resource['networkInterfaces']
    if json_resource.get('description', None):
      self.description = json_resource['description']
    if json_resource.get('tags', None):
      if json_resource['tags'].get('items', None):
        self.tags = json_resource['tags']['items']
    if json_resource.get('image', None):
      #BUG: Need to get the zone out of the image too
      self.image = Image(json_resource['image'].split('/')[-1])
    if json_resource.get('kernel', None):
      self.kernel = json_resource['kernel']
    if json_resource.get('status', None):
      self.status = json_resource['status']
    if json_resource.get('statusMessage', None):
      self.status_message = json_resource['statusMessage']
    if json_resource.get('disks', None):
      self.disk_mounts = []
      json_mounts = json_resource['disks']
      for jm in json_mounts:
        m = DiskMount()
        m.from_json(jm)
        self.disk_mounts.append(m)
    if json_resource.get('metadata', None):
      if json_resource['metadata'].get('items', None):
        self.metadata = json_resource['metadata']['items']
    if json_resource.get('serviceAccounts', None):
      self.service_accounts = json_resource['serviceAccounts']

  def set_defaults(self):
    """Set any defaults before insert."""

    self.zone.gce_project = self.gce_project
    self.machine_type.gce_project = self.gce_project

    if not self.zone.name:
      self.zone.set_defaults()

    if not self.machine_type.name:
      self.machine_type.set_defaults()

    if not self.network_interfaces:
      network = Network(self.gce_project.settings['compute']['network'])
      network.gce_project = self.gce_project
      self.network_interfaces = [{
          'network': network.url,
          'accessConfigs': self.gce_project.settings[
              'compute']['access_configs']
      }]

    boot_from_pd = False
    for d in self.disk_mounts:
      d.set_gce_project(self.gce_project)
      d.set_defaults()
      if d.boot:
        boot_from_pd = True

    # If we aren't booting from PD and we don't have an image, fix that up now.
    if not boot_from_pd and self.image == None:
      self.image = Image(None, GOOGLE_PROJECT)

    if self.image:
      self.image.gce_project = self.gce_project
      if not self.image.name:
        self.image.set_defaults()

  def service_resource(self):
    """Return the instances method of the apiclient.discovery.Resource object.

    Returns:
      The instances method of the apiclient.discovery.Resource object.
    """

    return self.gce_project.service.instances()


class Firewall(GceResource):
  """A class representing a GCE Firewall resource.

  Attributes:
    name: The string name of the firewall.
    description: A string description of the firewall.
    network: A Network object representing the network.
    source_ranges: List of string IP ranges from which traffic is
      accepted.
    source_tags: List of string tag names from which traffic is accepted.
      The tag names correspond to instance tag names.
    target_tags: A list of tags that indicate which instances can make
      network connections specified in allowed.
    allowed: A list of dictionaries representing the allowed IP protocols
      and open ports.
  """

  def __init__(self,
               name=None,
               description=None,
               network_name=None,
               source_ranges=None,
               source_tags=None,
               target_tags=None,
               allowed=None):
    """Initialize the Firewall class.

    Args:
      name: The string name of the firewall.
      description: A string description of the firewall.
      network_name: The string name of the network to add the firewall.
      source_ranges: List of string IP ranges from which traffic is
        accepted.
      source_tags: List of string tag names from which traffic is accepted.
        The tag names correspond to instance tag names.
      target_tags: A list of tags that indicate which instances can make
        network connections specified in allowed.
      allowed: A list of dictionaries representing the allowed IP protocols
        and open ports.
    """

    super(Firewall, self).__init__('firewall', 'global')
    self.name = name
    self.description = description
    self.network = Network(network_name)
    self.source_ranges = source_ranges
    self.source_tags = source_tags
    self.target_tags = target_tags
    self.allowed = allowed

  @property
  def json(self):
    """Create a json representation of the resource.

    Returns:
      A dictionary representing the resource.
    """

    firewall = {
        'name': self.name,
        'network': self.network.url,
        'allowed': self.allowed
    }
    if self.source_ranges:
      firewall['sourceRanges'] = self.source_ranges
    if self.source_tags:
      firewall['sourceTags'] = self.source_tags
    if self.target_tags:
      firewall['targetTags'] = self.target_tags
    return firewall

  def from_json(self, json_resource):
    """Sets member variables from a dictionary representing a firewall.

    Args:
      json_resource: A dictionary representing the firewall.
    """

    self.name = json_resource['name']
    self.network = json_resource['network']
    self.allowed = json_resource['allowed']
    if json_resource.get('sourceRanges', None):
      self.source_ranges = json_resource['sourceRanges']
    if json_resource.get('sourceTags', None):
      self.source_tags = json_resource['sourceTags']
    if json_resource.get('targetTags', None):
      self.source_tags = json_resource['targetTags']

  def set_defaults(self):
    """Set any defaults before insert."""

    self.network.gce_project = self.gce_project

    if not self.network.name:
      self.network.set_defaults()

    if not self.source_ranges and not self.source_tags:
      self.source_ranges = self.gce_project.settings[
          'compute']['firewall']['sourceRanges']

    if not self.allowed:
      self.allowed = self.gce_project.settings['compute']['firewall']['allowed']

  def service_resource(self):
    """Return the firewalls method of the apiclient.discovery.Resource object.

    Returns:
      The firewalls method of the apiclient.discovery.Resource object.
    """

    return self.gce_project.service.firewalls()


class Image(GceResource):
  """A class representing a GCE Image resource.

  Attributes:
    name: The string name of the image.
    description: A string description of the image.
    source_type: The string source of the image.
    preferred_kernel: The string URL of the kernel to use.
    raw_disk: A dictionary representing the raw disk.
  """

  def __init__(self,
               name=None,
               project_id=GOOGLE_PROJECT,
               description=None,
               source_type=None,
               preferred_kernel=None,
               raw_disk=None):
    """Initialize the Image class.

    Args:
      name: The string name of the image.
      project: The string name of the project owning the image.
      description: A string description of the image.
      source_type: The string source of the image.
      preferred_kernel: The string URL of the kernel to use.
      raw_disk: A dictionary representing the raw disk.
    """

    super(Image, self).__init__('image', 'global')
    self.name = name
    self.project_id = project_id
    self.description = description
    self.source_type = source_type
    self.preferred_kernel = preferred_kernel
    self.raw_disk = raw_disk

  @property
  def json(self):
    """Create a json representation of the resource.

    Returns:
      A dictionary representing the resource.
    """

    image = {
        'name': self.name
    }
    if self.description:
      image['description'] = self.description
    if self.source_type:
      image['sourceType'] = self.source_type
    if self.preferred_kernel:
      image['preferredKernel'] = self.preferred_kernel
    if self.raw_disk:
      image['rawDisk'] = self.raw_disk

  def from_json(self, json_resource):
    """Sets member variables from a dictionary representing a image.

    Args:
      json_resource: A dictionary representing the image.
    """

    self.name = json_resource['name']
    if json_resource.get('description', None):
      self.description = json_resource['description']
    if json_resource.get('sourceType', None):
      self.source_type = json_resource['sourceType']
    if json_resource.get('preferredKernel', None):
      self.preferred_kernel = json_resource['preferredKernel']
    if json_resource.get('rawDisk', None):
      self.raw_disk = json_resource['rawDisk']

  def service_resource(self):
    """Return the images method of the apiclient.discovery.Resource object.

    Returns:
      The images method of the apiclient.discovery.Resource object.
    """

    return self.gce_project.service.images()


class Disk(GceResource):
  """A class representing a GCE Disk resource.

  Attributes:
    name: The string name of the disk.
    zone: An object of type Zone representing the disks's zone.
    description: A string description of the disk.
    size_gb: The size of the disk in GB
  """

  def __init__(self,
               name=None,
               zone_name=None,
               description=None,
               size_gb=None):
    """Initialize the Disk class.

    Args:
      name: The string name of the disk.
      zone_name: The name of the zone for the disk.
      description: A string description of the disk.
      size_gb: The size of the disk in GB
    """

    super(Disk, self).__init__('disk', 'zonal')
    self.name = name
    self.zone = Zone(zone_name)
    self.description = description
    self.size_gb = size_gb

  @property
  def json(self):
    """Create a json representation of the resource.

    Returns:
      A dictionary representing the resource.
    """

    disk = {
        'name': self.name,
    }
    if self.description:
      instance['description'] = self.description
    if self.size_gb:
      instance['sizeGb'] = self.size_gb
    return disk

  def from_json(self, json_resource):
    """Sets member variables from a dictionary representing a disk.

    Args:
      json_resource: A dictionary representing the disk.
    """

    self.name = json_resource['name']
    self.zone = Zone(json_resource['zone'].split('/')[-1])
    self.size_gb = json_resource['sizeGb']
    if json_resource.get('description', None):
      self.description = json_resource['description']

  def set_defaults(self):
    """Set any defaults before insert."""
    self.zone.gce_project = self.gce_project
    if not self.zone.name:
      self.zone.set_defaults()

  def service_resource(self):
    """Return the disks method of the apiclient.discovery.Resource object.

    Returns:
      The disks method of the apiclient.discovery.Resource object.
    """

    return self.gce_project.service.disks()


class MachineType(GceResource):
  """A class representing a GCE Machine Type resource.

  Attributes:
    name: The string name of the machine type.
  """

  def __init__(self, name=None):
    """Initialize the MachineType class.

    Args:
      name: The string name of the machine type.
    """

    super(MachineType, self).__init__('machineType', 'global')
    self.name = name

  def service_resource(self):
    """Return the machineTypes method of apiclient.discovery.Resource object.

    Returns:
      The machineTypes method of the apiclient.discovery.Resource object.
    """

    return self.gce_project.service.machineTypes()


class Zone(GceResource):
  """A class representing a GCE Zone resource.

  Attributes:
    name: The string name of the zone.
  """

  def __init__(self, name=None):
    """Initialize the Zone class.

    Args:
      name: The string name of the zone.
    """

    super(Zone, self).__init__('zone', 'global')
    self.name = name

  def service_resource(self):
    """Return the zones method of apiclient.discovery.Resource object.

    Returns:
      The zones method of the apiclient.discovery.Resource object.
    """

    return self.gce_project.service.zones()


class Network(GceResource):
  """A class representing a GCE Network resource.

  Attributes:
    name: The string name of the network.
  """

  def __init__(self, name=None):
    """Initialize the Network class.

    Args:
      name: The string name of the network.
    """

    super(Network, self).__init__('network', 'global')
    self.name = name

  def service_resource(self):
    """Return the networks method of apiclient.discovery.Resource object.

    Returns:
      The networks method of the apiclient.discovery.Resource object.
    """

    return self.gce_project.service.networks()
