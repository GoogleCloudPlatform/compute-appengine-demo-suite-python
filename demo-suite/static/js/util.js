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
 * @fileoverview Various generic utilities .
 */

/**
 * Repeat a string n times.
 * @param  {string} string The string to repeat.
 * @param  {number} length The number of times to repeat.
 * @return {string}        A string containing {@code length} repetitions of
 *  {@code string}.
 */
stringRepeat = function(string, length) {
  return new Array(length + 1).join(string);
}

/**
 * Pads a number with preceeding zeros.
 * @param  {number} num    The number to pad.
 * @param  {number} length The total string length to return.
 * @return {string}        {@code num} as a string padded with zeros.
 */
padNumber = function(num, length) {
  var s = String(num);
  index = s.length;
  return stringRepeat('0', Math.max(0, length - index)) + s;
};

/**
 * Determine if 2 maps (associative arrays) are equal.
 * @param  {Object} a
 * @param  {Object} b
 * @return {boolean}      True if they are equal.
 */
mapsEqual = function(a, b) {
  if (a == b) {
    return true;
  }

  if (a == null || b == null) {
    return false;
  }

  if (Object.keys(a).length != Object.keys(b).length) {
    return false;
  }

  for (key in a) {
    if (a[key] != b[key]) {
      return false;
    }
  }

  return true;
}

/**
 * Compare two arrays to see if they are equal.
 * @param  {Array} a
 * @param  {Array} b
 * @return {boolean}   true if a and b are equal.
 */
function arraysEqual(a, b) {
  if (a == b) {
    return true;
  }
  if (a == null || b == null) {
    return false;
  }

  if (a.length != b.length) {
    return false;
  }

  for (var i = 0; i < a.length; i++) {
    if (a[i] != b[i]) {
      return false;
    }
  }
  return true;
}
