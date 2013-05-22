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
 * @fileoverview Display status squares for instances.
 *
 * Creates color block and updates the colors according to instance status.
 *
 */

/**
 * The Squares class controls the color blocks representing instance statuses
 * in the given HTML container. Each block is given an ID equal to the instance
 * name, using the given instanceNames.
 * Optional options are available to customize the squares including:
 * <ul>
 * <li>statusClasses: custom colors for OTHER, TERMINATED, PROVISIONING,
 * STAGING, and RUNNING. OTHER is used for initial color and if an
 * unknown status is returned.</li>
 * <li>drawOnStart: true or false, true will automatically draw the squares
 * when the start method is run from the Gce startInstances method.
 * Otherwise, the squares need to be manually drawn using drawSquares.</li>
 * <li>cols: the number of columns. If not set, this defaults to the
 * ceil(sqrt) of the number of instances.</li>
 * </ul>
 * @constructor
 * @param {Element} container HTML element in which to display the squares.
 * @param {Array.<string>} instanceNames List of instance names.
 * @param {Object} squareOptions Options for the square (optional).
 */
var Squares = function(container, instanceNames, squareOptions) {
  /**
   * Container for the squares.
   * @type {JQuery}
   * @private
   */
  this.container_ = $(container);

  /**
   * The number of columns in the UI display.  If this is null a value is chosen
   * automatically.
   * @type {number}
   * @private
   */
  this.numCols_ = null;

  /**
   * The default status colors. These are just classNames and can be customized
   * using the squareOptions object during initialization.
   * @type {Object}
   * @private
   */
  this.statusClasses_ = null;

  /**
   * The string of instance names.
   * @type {Array.<string>}
   * @private
   */
  this.instanceNames_ = instanceNames;

  /**
   * If drawOnStart is true, this variable is set equal to the this.drawSquares
   * function. When a Square object is passed as a UI option to the Gce class,
   * the Gce class will call the start method in the startInstances function.
   * @type {Function}
   */
  this.start = null;

  /**
   * A map from the instance name to the JQuery object representing that
   *    instance.
   * @type {Object}
   * @private
   */
  this.squares_ = {};

  if (squareOptions.statusClasses) {
    this.statusClasses_ = squareOptions.statusClasses;
  } else {
    this.statusClasses_ = {
      'OTHER': 'status-other',
      'TERMINATED': 'status-terminated',
      'PROVISIONING': 'status-provisioning',
      'STAGING': 'status-staging',
      'RUNNING': 'status-running',
      'SERVING': 'status-serving',
      'STOPPING': 'status-stopping',
      'STOPPED': 'status-stopped',
    };
  }
  if (squareOptions.drawOnStart) {
    this.start = this.drawSquares;
  }

  // If the num of cols is not set, create up to 25 cols based on the
  // number of instances.
  if (squareOptions.cols) {
    this.numCols_ = squareOptions.cols;
  }
};

/**
 * Set in a new set of instance names.  This will clear the display requiring
 * the user to draw the squares again and update data.
 * @param  {Array} instance_names The list of instance names.
 */
Squares.prototype.resetInstanceNames = function(instance_names) {
  this.reset();
  this.instanceNames_ = instance_names;
};

/**
 * Returns the instance names
 * @return {Array} Returns the instance names.
 */
Squares.prototype.getInstanceNames = function() {
  return this.instanceNames_.slice();
};

/**
 * Draws the squares on the HTML page.
 */
Squares.prototype.drawSquares = function() {
  // First, clean up any old instance squares.
  this.reset();


  // Add the color squares.
  for (var i = 0; i < this.instanceNames_.length; i++) {
    // TAG is defined in the html file as a template variable
    var instanceName = this.instanceNames_[i];
    square = $('<div>')
      .addClass('color-block')
      .addClass(this.statusClasses_['OTHER'])
      .append('<i class="icon-ok icon-2x"></i>');
    this.container_.append(square);
    this.squares_[instanceName] = square;

    if ((i+1) % this.numCols_ == 0) {
      $('<br>').appendTo(this.container_);
    }
  }
};

/**
 * Get the number of columns to use.
 * @return {Number} The number of columns to display.
 */
Squares.prototype.getNumCols_ = function() {
  var numInstances = this.instanceNames_.length;
  var numCols = this.numCols_;
  if (!numCols) {
    numCols = Math.ceil(Math.sqrt(numInstances));
    if (numCols > 25) {
      numCols = 25;
    }
  }
  return numCols;
};

/**
 * Changes the color of the squares according to the instance status. Called
 * during the Gce.heartbeat.
 * @param {Object} updateData The status data returned from the server.
 */
Squares.prototype.update = function(updateData) {
  var instanceStatus = updateData['instances'] || {};
  for (var i = 0; i < this.instanceNames_.length; i++) {
    var instanceName = this.instanceNames_[i];
    var statusClass = null;
    if (instanceStatus.hasOwnProperty(instanceName)) {
      var status = instanceStatus[instanceName]['status'];
      statusClass = this.statusClasses_[status];
      if (!statusClass) {
        statusClass = this.statusClasses_['OTHER'];
      }
    } else {
      statusClass = this.statusClasses_['TERMINATED'];
    }
    this.setStatusClass(instanceName, statusClass);
  }
};

/**
 * Reset the squares.
 */
Squares.prototype.reset = function() {
  this.container_.empty();
  this.squares_ = {};
};

/**
 * Colors the HTML element with the given color / class and jquery id.
 * @param {String} instanceName The name of the instance.
 * @param {String} color Class name to update.
 */
Squares.prototype.setStatusClass = function(instanceName, color) {
  square = this.squares_[instanceName];
  if (square) {
    for (var status in this.statusClasses_) {
      square.removeClass(this.statusClasses_[status]);
    }
    square.addClass(color);
  }
};

/**
 * Get the div for an instance.
 * @param  {string} instanceName The instance.
 * @return {JQuery}              A JQuery object wrapping the div that
 *    represents instanceName.
 */
Squares.prototype.getSquareDiv = function(instanceName) {
  return this.squares_[instanceName];
};
