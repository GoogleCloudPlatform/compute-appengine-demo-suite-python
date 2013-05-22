# Design

This AppEngine app is designed to provide visual demos for using the GCE API.

## Server Side
Generally it consists of a python driver that launches and manages information.
A simple GCE library is included in `lib/google_cloud/gce.py`.  This is built on
the [Google API Python Library][python-lib].

The discovery document is checked in (`demo-
suite/discovery/compute/v1beta14.json`).  When updating to a new version a new
discovery doc will have to be fetched and used.  An easy way to do this is to
grab it from the gcutil tarball.

Individual demo handlers should have a method that returns a JSON dictionary of
instance state and data.  It might look like this:

```JSON
{
   "instances":{
      "quick-start-3":{
         "status":"PROVISIONING"
      },
      "quick-start-2":{
         "status":"STAGING"
      },
      "quick-start-1":{
         "status":"RUNNING"
      },
      "quick-start-0":{
         "status":"RUNNING"
      },
      "quick-start-4":{
         "status":"RUNNING"
      }
   },
}
```

There is a helper for doing common simple operations and generating this type of
output. That is located at `lib/google_cloud/gce_appengine.py`

## Client Side

There is a corresponding `gce.js` that helps to drive this stuff on the client.
It knows how to start VMs, stop VMs and get status information.

There are a set of `gceUi` objects that can be installed into a `Gce` object to
receive update notifications.  There are three methods that can be called on one
of these objects:

  1. `start()` -- Called when an operation is started.  This includes creating
     and deleting instances.
  2. `stop()` -- Called when the operation is completed.
  3. `update(data)` -- Called when new information available.  This includes the
     data structure above along with some extra information like a histogram of
     the number of VMs in each state.

There are currently 3 UI widgets you can use:

  1. `squares.js` -- Display a square for each VM.  Great for showing the status
     of a cluster.
  2. `counter.js` -- Show how many VMs are running.
  3. `timer.js` -- Time the amount of time it takes for an operation to
     complete.

[python-lib]: https://code.google.com/p/google-api-python-client/
