/**
 * Copyright 2012 Google Inc. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * @fileoverview GCE JavaScript functions.
 *
 * Start, stop, or cleanup instances. Set UI controls.
 *
 */

/**
 * Gce class starts, stops instances and controls UI.
 * @constructor
 * @param {string} startInstanceUrl The URL to start instances.
 * @param {string} listInstanceUrl The URL to list instances.
 * @param {string} stopInstanceUrl The URL to stop instances.
 * @param {Object} gceUiOptions UI options for GCE.
 */
var Gce = function(startInstanceUrl, listInstanceUrl, stopInstanceUrl,
    gceUiOptions) {
  this.startInstanceUrl_ = startInstanceUrl;
  this.listInstanceUrl_ = listInstanceUrl;
  this.stopInstanceUrl_ = stopInstanceUrl;
  this.statusCodeResponseFunctions_ = {
    401: function(jqXHR, textStatus, errorThrown) {
      alert('Refresh token revoked! ' + textStatus + ':' + errorThrown);
    },
    500: function(jqXHR, textStatus, errorThrown) {
      alert('Unknown error! ' + textStatus + ':' + errorThrown);
    }
  };
  this.setOptions(gceUiOptions);
};

/**
 * The URL to start instances.
 * @type {string}
 * @private
 */
Gce.prototype.startInstanceUrl_ = null;

/**
 * The URL to list instances.
 * @type {string}
 * @private
 */
Gce.prototype.listInstanceUrl_ = null;

/**
 * The URL to stop instances.
 * @type {string}
 * @private
 */
Gce.prototype.stopInstanceUrl_ = null;

/**
 * Object mapping Ajax response code to handler.
 * @type {Object}
 * private
 */
Gce.prototype.statusCodeResponseFunctions_ = null;

/**
 * Time (ms) between calls to server to check for running instances.
 * @type {number}
 * private
 */
Gce.prototype.HEARTBEAT_TIMEOUT_ = 2000;

/**
 * Sets the GCE UI options. Options include colored squares to indicate
 * status, timer, and counter.
 * @param {Object} gceUiOptions UI options for demos.
 */
Gce.prototype.setOptions = function(gceUiOptions) {
  this.gceUiOptions = gceUiOptions;
};

/**
 * Send the Ajax request to start instances. Init UI controls with start method.
 * @param {number} numInstances The number of instances to start.
 * @param {Object} startOptions Consists of startOptions.data and
 *     startOptions.callback.
 */
Gce.prototype.startInstances = function(numInstances, startOptions) {
  for (var gceUi in this.gceUiOptions) {
    if (this.gceUiOptions[gceUi].start) {
      this.gceUiOptions[gceUi].start();
    }
  }

  var ajaxRequest = {
    type: 'POST',
    url: this.startInstanceUrl_,
    dataType: 'json',
    statusCode: this.statusCodeResponseFunctions_
  };
  if (startOptions.data) {
    ajaxRequest.data = startOptions.data;
  }
  $.ajax(ajaxRequest);
  if (this.gceUiOptions || startOptions.callback) {
    this.heartbeat_(numInstances, startOptions.callback);
  }
};

/**
 * Send the Ajax request to stop instances.
 * @param {function} callback A callback function to call when instances
 *     have stopped.
 */
Gce.prototype.stopInstances = function(callback) {
  $.ajax({
    type: 'POST',
    url: this.stopInstanceUrl_,
    statusCode: this.statusCodeResponseFunctions_
  });
  if (this.gceUiOptions || callback) {
    this.heartbeat_(0, callback);
  }
};

/**
 * Check for running instances.
 * @param {function} callback A function to call when AJAX request completes.
 * @param {Object} optionalData Optional data to send with the request.
 */
Gce.prototype.checkIfRunning = function(callback, optionalData) {
  var that = this;
  var results = function(data) {
    var numRunning = that.numRunning_(data);
    callback(data, numRunning);
  };
  this.getStatuses_(results, optionalData);
};

/**
 * Check for instances that are in any state.
 * @param {function} callback A function to call when AJAX request completes.
 * @param {Object} optionalData Optional data to send with the request.
 */
Gce.prototype.checkIfAlive = function(callback, optionalData) {
  var that = this;
  var results = function(data) {
    var numAlive = that.numAlive_(data);
    callback(data, numAlive);
  };
  this.getStatuses_(results, optionalData);
};

/**
 * Send the Ajax request to start instances. Update UI controls with an update
 * method.
 * @param {number} numInstances The number of instances that are starting.
 * @param {function} callback A callback function to call when instances
 *     have started or stopped.
 * @private
 */
Gce.prototype.heartbeat_ = function(numInstances, callback) {
  var that = this;
  var success = function(data) {
    var numRunning = null;

    // If doing a shutdown (numInstances == 0), check the
    // number alive rather than the number running. We want
    // them all completely shutdown.
    if (numInstances) {
      numRunning = that.numRunning_(data);
    } else {
      numRunning = that.numAlive_(data);
    }

    for (var gceUi in that.gceUiOptions) {
      if (that.gceUiOptions[gceUi].update) {
        that.gceUiOptions[gceUi].update({
          'numRunning': numRunning,
          'data': data
        });
      }
    }

    if (numRunning == numInstances) {
      for (var gceUi in that.gceUiOptions) {
        if (that.gceUiOptions[gceUi].stop) {
          that.gceUiOptions[gceUi].stop();
        }
      }

      if (callback) {
        callback(data);
      }
    } else {
      setTimeout(function() {
        that.getStatuses_(success);
      }, that.HEARTBEAT_TIMEOUT_);
    }
  };

  var that = this;
  setTimeout(function() {
    that.getStatuses_(success);
  }, this.HEARTBEAT_TIMEOUT_);
};

/**
 * Send Ajax request to get instance information.
 * @param {function} success Function to call if request is successful.
 * @param {Object} optionalData Optional data to send with the request. The data
 *     is added as URL parameters.
 * @private
 */
Gce.prototype.getStatuses_ = function(success, optionalData) {
  var ajaxRequest = {
    type: 'GET',
    url: this.listInstanceUrl_,
    dataType: 'json',
    success: success,
    statusCode: this.statusCodeResponseFunctions_
  };
  if (optionalData) {
    ajaxRequest.data = optionalData;
  }
  $.ajax(ajaxRequest);
};

/**
 * Count the number of running instances.
 * @param {Object} data Data returned from GCE API formatted in a dictionary
 *     mapping instance name to a dictionary with a status parameter.
 * @private
 * @return {number} The number of running instances.
 */
Gce.prototype.numRunning_ = function(data) {
  var numRunning = 0;
  for (var instance in data) {
    if (data[instance]['status'] == 'RUNNING') {
      numRunning++;
    }
  }
  return numRunning;
};

/**
 * Count the number of instances with any status.
 * @param {Object} data Data returned from GCE API formatted in a dictionary
 *     mapping instance name to a dictionary of instance information.
 * @private
 * @return {number} The number of instances that are up.
 */
Gce.prototype.numAlive_ = function(data) {
  var numAlive = 0;
  for (var instance in data) {
    numAlive++;
  }
  return numAlive;
};
