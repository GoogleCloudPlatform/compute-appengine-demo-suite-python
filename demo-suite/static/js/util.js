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
