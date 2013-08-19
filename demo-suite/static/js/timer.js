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
 * @fileoverview Timer display shows time formatted as 00:00:00..
 *
 * Start and stop a timer. Timer increments every second.
 *
 */

/**
 * Timer class displays a timer in the given HTML element.
 * @constructor
 * @param {Element} container The HTML element in which to display the timer.
 */
var Timer = function(container) {
  this.container_ = container;
  this.container_.innerHTML = '00:00:00';
};

/**
 * The HTML element to display the timer.
 * @type {Element}
 * @private
 */
Timer.prototype.container_ = null;

/**
 * The timer interval.
 * @type {Object}
 * @private
 */
Timer.prototype.timerInterval_ = null;

/**
 * The timer interval time in milliseconds.
 * @type {number}
 * @private
 */
Timer.prototype.TIMER_INTERVAL_TIME_ = 1000;

/**
 * The timer state.
 * @type {boolean}
 * @private
 */
Timer.prototype.running_ = false;

/**
 * The elapsed seconds.
 * @type {number}
 * @private
 */
Timer.prototype.seconds_ = 0;


/**
 * Start the timer.
 */
Timer.prototype.start = function() {
  var that = this;

  // Start timer if not already running.
  if (!Timer.prototype.running_) { 
    this.timerInterval_ = setInterval(function() {
      that.tick_();
    }, this.TIMER_INTERVAL_TIME_);
    this.tick_();
    Timer.prototype.running_ = true;
  }
};

/**
 * Stop the timer.
 */
Timer.prototype.stop = function() {
  this.seconds_ = 0;
  clearInterval(this.timerInterval_);
  Timer.prototype.running_ = false;
};

/**
 * Set starting offset.
 */
Timer.prototype.setOffset = function(offset) {
  this.seconds_ = offset;
}

/**
 * Increment the timer every second.
 * @private
 */
Timer.prototype.tick_ = function() {
  var secs = this.seconds_++;
  var hrs = Math.floor(secs / 3600);
  secs %= 3600;
  var mns = Math.floor(secs / 60);
  secs %= 60;
  var pretty = (hrs < 10 ? '0' : '') + hrs +
      ':' + (mns < 10 ? '0' : '') + mns +
      ':' + (secs < 10 ? '0' : '') + secs;
  this.container_.innerHTML = pretty;
};
