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
 s WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
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
 * @param {Object} commonQueryData Common parameters to pass with each request.
 */
var Gce = function(startInstanceUrl, listInstanceUrl, stopInstanceUrl,
    gceUiOptions, commonQueryData) {

  /**
   * The URL to start instances.
   * @type {string}
   * @private
   */
  this.startInstanceUrl_ = startInstanceUrl;

  /**
   * The URL to list instances.
   * @type {string}
   * @private
   */
  this.listInstanceUrl_ = listInstanceUrl;

  /**
   * The URL to stop instances.
   * @type {string}
   * @private
   */
  this.stopInstanceUrl_ = stopInstanceUrl;

  /**
   * Object mapping Ajax response code to handler.
   * @type {Object}
   * @private
   */
  this.statusCodeResponseFunctions_ = {
    401: function(jqXHR, textStatus, errorThrown) {
      alert('Refresh token revoked! ' + textStatus + ':' + errorThrown);
    },
    500: function(jqXHR, textStatus, errorThrown) {
      alert('Unknown error! ' + textStatus + ':' + errorThrown);
    }
  };

  /**
   * Query data to be passed with every request.
   * @type {Object}
   * @private
   */
  this.commonQueryData_ = commonQueryData;

  /**
   * Are we doing continuous heartbeats to the server?  If yes, we don't do
   * heartbeats specifically for start/stop operations and so never generate UI
   * start/stop messages.
   * @type {Boolean}
   * @private
   */
  this.doContinuousHeartbeat_ = false;

  this.setOptions(gceUiOptions);
};



/**
 * Time (ms) between calls to server to check for running instances.
 * @type {number}
 * @private
 */
Gce.prototype.HEARTBEAT_TIMEOUT_ = 2000;


/**
 * The various states (status in the GCE API) that an instance can be in. The
 *    UNKNOWN and SERVING states are synthetic.
 * @type {Array}
 * @private
 */
Gce.prototype.STATES = [
  'UNKNOWN',
  'PROVISIONING',
  'STAGING',
  'RUNNING',
  'SERVING',
  'STOPPING',
  'STOPPED',
  'TERMINATED',
];

/**
 * Sets the GCE UI options. Options include colored squares to indicate
 * status, timer, and counter.
 * @param {Object} gceUiOptions UI options for demos.
 */
Gce.prototype.setOptions = function(gceUiOptions) {
  this.gceUiOptions = gceUiOptions;
};

/**
 * Send the Ajax request to start instances. Init UI controls with start
 *    method.
 * @param {number} numInstances The number of instances to start.
 * @param {Object} startOptions Consists of startOptions.data and
 *    startOptions.callback.
 */
Gce.prototype.startInstances = function(numInstances, startOptions) {
  for (var gceUi in this.gceUiOptions) {
    if (this.gceUiOptions[gceUi].start) {
      this.gceUiOptions[gceUi].start();
    }
  }

  if ((typeof Recovering !== 'undefined') && (!Recovering)) {
    var ajaxRequest = {
      type: 'POST',
      url: this.startInstanceUrl_,
      dataType: 'json',
      statusCode: this.statusCodeResponseFunctions_,
      complete: startOptions.ajaxComplete,
    };
    ajaxRequest.data = {}
    if (startOptions.data) {
      ajaxRequest.data = startOptions.data;
    }
    if (this.commonQueryData_) {
      $.extend(ajaxRequest.data, this.commonQueryData_)
    }
    $.ajax(ajaxRequest);
  }
  if (!this.doContinuousHeartbeat_
    && (this.gceUiOptions || startOptions.callback)) {
    var terminalState = 'RUNNING'
    if (startOptions.checkServing) {
      terminalState = 'SERVING'
    }
    this.heartbeat_(numInstances, startOptions.callback, terminalState);
  }
};

/**
 * Send the Ajax request to stop instances.
 * @param {function} callback A callback function to call when instances
 *     have stopped.
 */
Gce.prototype.stopInstances = function(callback) {
  var data = {}

  if (this.gceUiOptions.timer.start) {
    this.gceUiOptions.timer.start();
  }

  if (this.commonQueryData_) {
    $.extend(data, this.commonQueryData_)
  }

  $.ajax({
    type: 'POST',
    url: this.stopInstanceUrl_,
    statusCode: this.statusCodeResponseFunctions_,
    data: data
  });
  if (!this.doContinuousHeartbeat_
    && (this.gceUiOptions || startOptions.callback)) {
    this.heartbeat_(0, callback, 'TOTAL');
  }
};


/**
 * Get an update on instance states and status.
 * @param {function} callback A function to call when AJAX request completes.
 * @param {Object} optionalData Optional data to send with the request.
 */
Gce.prototype.getInstanceStates = function(callback, optionalData) {
  var that = this;
  var processResults = function(data) {
    callback(data);
  }
  this.getStatuses_(processResults, optionalData)
};

/**
 * Start continuous heartbeat.  If this is activated we no longer do heartbeats
 * specifically for start/stopInstances and UI components no longer get
 * corresponding start/stop calls.
 * @param  {Function} callback A callback invoked on each heartbeat
 */
Gce.prototype.startContinuousHeartbeat = function(callback) {
  if (!this.doContinuousHeartbeat_) {
    this.doContinuousHeartbeat_ = true;
    this.continuousHeartbeat_(callback)
  }
};

/**
 * Send UI update messages when we get data on what is running and how.
 * @param {Object} data Data returned from GCE API with summary data.
 * @private
 */
Gce.prototype.updateUI_ = function(data) {
    for (var gceUi in this.gceUiOptions) {
      if (this.gceUiOptions[gceUi].update) {
        this.gceUiOptions[gceUi].update(data);
      }
    }
};

/**
 * Send the Ajax request to start instances. Update UI controls with an update
 *    method.
 * @param {number} numInstances The number of instances that are starting.
 * @param {function} callback A callback function to call when instances have
 *    started or stopped.
 * @param {string} terminalState Stop the heartbeat when all numInstances are
 *    in this state.
 * @private
 */
Gce.prototype.heartbeat_ = function(numInstances, callback, terminalState) {
  var that = this;
  var success = function(data) {
    isDone = data['stateCount'][terminalState] == numInstances;

    if (isDone) {
      for (var gceUi in that.gceUiOptions) {
        if (that.gceUiOptions[gceUi].stop) {
          that.gceUiOptions[gceUi].stop();
        }
      }

      if (callback) {
        callback(data);
      }
    } else {
      that.heartbeat_(numInstances, callback, terminalState);
    }
  };

  // If we're in recovery mode (i.e. user refresh the page before request
  // is complete), start the polling immediately to refresh state ASAP,
  // instead of waiting 2s to refresh the display.
  var that = this;
  if ((typeof Recovering !== 'undefined') && Recovering) {
    that.getStatuses_(success);
  } else {
    setTimeout(function() {
      that.getStatuses_(success);
    }, this.HEARTBEAT_TIMEOUT_);
  }
};

Gce.prototype.continuousHeartbeat_ = function(callback) {
  var that = this;
  var success = function(data) {
    if (callback) {
      callback(data);
    }
    that.continuousHeartbeat_(callback);
  };

  var that = this;
  setTimeout(function() {
    that.getStatuses_(success);
  }, this.HEARTBEAT_TIMEOUT_);

}

/**
 * Send Ajax request to get instance information.
 * @param {function} success Function to call if request is successful.
 * @param {Object} optionalData Optional data to send with the request. The
 *    data is added as URL parameters.
 * @private
 */
Gce.prototype.getStatuses_ = function(success, optionalData) {
  var that = this;
  var localSuccess = function(data) {
    that.summarizeStates(data);
    that.updateUI_(data);
    success(data);
  }

  var ajaxRequest = {
    type: 'GET',
    url: this.listInstanceUrl_,
    dataType: 'json',
    success: localSuccess,
    statusCode: this.statusCodeResponseFunctions_
  };
  ajaxRequest.data = {}
  if (optionalData) {
    ajaxRequest.data = optionalData;
  }
  if (this.commonQueryData_) {
    $.extend(ajaxRequest.data, this.commonQueryData_)
  }
  $.ajax(ajaxRequest);
};

/**
 * Builds a histogram of how many instances are in what state. It writes it
 *    into data as an item called stateCount
 * @param  {Object} data Data returned from the GCE API formatted into a
 *    dictionary.
 * @return {Object}      A map from state to count.
 */
Gce.prototype.summarizeStates = function(data) {
  var states = {};
  $.each(this.STATES, function(index, value) {
    states[value] = 0;
  });
  states['TOTAL'] = 0;

  $.each(data['instances'], function(i, d) {
    state = d['status'];
    if (!states.hasOwnProperty(state)) {
      state = 'UNKNOWN';
    }
    states[state]++;
    states['TOTAL']++;
  });

  data['stateCount'] = states
};
