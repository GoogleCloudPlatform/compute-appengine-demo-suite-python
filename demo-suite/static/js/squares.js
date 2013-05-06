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
   * The number of columns in the UI display.
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
  var numInstances = this.instanceNames_.length;
  if (!this.numCols_) {
    this.numCols_ = Math.ceil(Math.sqrt(numInstances));
    if (this.numCols_ > 25) {
      this.numCols_ = 25;
    }
  }
};


/**
 * Draws the squares on the HTML page.
 */
Squares.prototype.drawSquares = function() {
  // First, clean up any old instace squares.
  this.reset();

  // Add the columns.
  var columns = [];
  for (var i = 0; i < this.numCols_; i++) {
    var col = $('<div>').addClass('span1');
    this.container_.append(col);
    columns.push(col);
  }

  // Add the color squares.
  for (var i = 0; i < this.instanceNames_.length; i++) {
    // TAG is defined in the html file as a template variable
    var instanceName = this.instanceNames_[i];
    square = $('<div>')
      .addClass('color-block')
      .addClass(this.statusClasses_['OTHER'])
      .append('<i class="icon-ok icon-2x"></i>');
    var columnNum = i % this.numCols_;
    columns[columnNum].append(square);
    this.squares_[instanceName] = square;
  }
};

/**
 * Changes the color of the squares according to the instance status. Called
 * during the Gce.heartbeat.
 * @param {Object} updateData The status data returned from the server.
 */
Squares.prototype.update = function(updateData) {
  var data = updateData['data'];
  for (var i = 0; i < this.instanceNames_.length; i++) {
    var instanceName = this.instanceNames_[i];
    var statusClass = null;
    if (data.hasOwnProperty(instanceName)) {
      var status = data[instanceName]['status'];
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
  for (var status in this.statusClasses_) {
    square.removeClass(this.statusClasses_[status]);
  }
  square.addClass(color);
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
