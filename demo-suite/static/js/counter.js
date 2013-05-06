/**
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License
 * as published by the Free Software Foundation; either version 2
 * of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
 *
 * @fileoverview Display a counter.
 *
 * Displays a counter representing the number of running instances. Originally
 * developed by Mark Crossley, revision 0.3.0.
 * http://www.wilmslowastro.com/odometer/odometer.html
 */

/**
 * Counter class displays a counter in the given HTML element.
 * @constructor
 * @param {Element} container The HTML element in which to display the
 *    counter.
 * @param {string} targetMetric Either 'numRunning' or 'numAlive' to
 *    differentiate which state class to count.
 * @param {Object} counterOptions Options for the counter object details can
 *    be found here: http://www.wilmslowastro.com/odometer/odometer.html.
 */
var Counter = function(container, targetMetric, counterOptions) {
  if (!counterOptions) {
    counterOptions = {
      height: 30,
      digits: 4,
      decimals: 0,
      wobbleFactor: 0
    };
  }
  var counterElement = container.getContext('2d');
  this.counter_ = new odometer_(counterElement, counterOptions);

  this.targetMetric = 'numRunning';
  if (targetMetric) {
    this.targetMetric = targetMetric;
  }
};

/**
 * The odometer (counter) object.
 * @type {Object}
 * @private
 */
Counter.prototype.counter_ = null;

/**
 * Update the number of running instances. This method is called by the
 * Gce.heartbeat method, and is passed a dictionary containing the instance
 * status list and the num of running instances.
 * @param {Object} updateData Object mapping 'data' to the instance status
 *     information and 'numRunning' to the number of running instances.
 */
Counter.prototype.update = function(updateData) {
  this.counter_.setValue(updateData[this.targetMetric]);
};

/**
 * The odometer class. The following code was developed by Mark Crossley.
 * @param {Element} ctx The canvas element.
 * @param {Object} parameters Optional parameters for the display.
 * @private
 * @this odometer
 */
var odometer_ = function(ctx, parameters) {
  parameters = parameters || {};
  var height =
      (undefined === parameters.height ? 40 : parameters.height);
  var digits = (undefined === parameters.digits ? 6 : parameters.digits);
  var decimals = (undefined === parameters.decimals ? 1 : parameters.decimals);
  var decimalBackColor = (undefined === parameters.decimalBackColor ?
          '#F0F0F0' : parameters.decimalBackColor);
  var decimalForeColor = (undefined === parameters.decimalForeColor ?
      '#F01010' : parameters.decimalForeColor);
  var font = (undefined === parameters.font ? 'sans-serif' : parameters.font);
  var value = (undefined === parameters.value ? 0 : parameters.value);
  var valueBackColor = (undefined === parameters.valueBackColor ?
      '#050505' : parameters.valueBackColor);
  var valueForeColor = (undefined === parameters.valueForeColor ?
      '#F8F8F8' : parameters.valueForeColor);
  var wobbleFactor = (undefined === parameters.wobbleFactor ?
      0.07 : parameters.wobbleFactor);

  var doc = document;
  var initialized = false;

  // Cannot display negative values yet
  if (value < 0) {
    value = 0;
  }

  var digitHeight = Math.floor(height * 0.85);
  var stdFont = '600 ' + digitHeight + 'px ' + font;

  var digitWidth = Math.floor(height * 0.68);
  var width = digitWidth * (digits + decimals);
  var columnHeight = digitHeight * 11;
  var verticalSpace = columnHeight / 12;
  var zeroOffset = verticalSpace * 0.85;

  var wobble = [];

  // Resize and clear the main context
  ctx.canvas.width = width;
  ctx.canvas.height = height;

  // Create buffers
  var backgroundBuffer = createBuffer(width, height);
  var backgroundContext = backgroundBuffer.getContext('2d');

  var foregroundBuffer = createBuffer(width, height);
  var foregroundContext = foregroundBuffer.getContext('2d');

  var digitBuffer = createBuffer(digitWidth, columnHeight * 1.1);
  var digitContext = digitBuffer.getContext('2d');

  var decimalBuffer = createBuffer(digitWidth, columnHeight * 1.1);
  var decimalContext = decimalBuffer.getContext('2d');


  function init() {

    initialized = true;

    // Create the foreground
    foregroundContext.rect(0, 0, width, height);
    gradHighlight = foregroundContext.createLinearGradient(0, 0, 0, height);
    gradHighlight.addColorStop(0, 'rgba(0, 0, 0, 1)');
    gradHighlight.addColorStop(0.1, 'rgba(0, 0, 0, 0.4)');
    gradHighlight.addColorStop(0.33, 'rgba(255, 255, 255, 0.45)');
    gradHighlight.addColorStop(0.46, 'rgba(255, 255, 255, 0)');
    gradHighlight.addColorStop(0.9, 'rgba(0, 0, 0, 0.4)');
    gradHighlight.addColorStop(1, 'rgba(0, 0, 0, 1)');
    foregroundContext.fillStyle = gradHighlight;
    foregroundContext.fill();

    // Create a digit column
    // background
    digitContext.rect(0, 0, digitWidth, columnHeight * 1.1);
    digitContext.fillStyle = valueBackColor;
    digitContext.fill();
    // edges
    digitContext.strokeStyle = '#f0f0f0';
    digitContext.lineWidth = '1px'; //height * 0.1 + "px";
    digitContext.moveTo(0, 0);
    digitContext.lineTo(0, columnHeight * 1.1);
    digitContext.stroke();
    digitContext.strokeStyle = '#202020';
    digitContext.moveTo(digitWidth, 0);
    digitContext.lineTo(digitWidth, columnHeight * 1.1);
    digitContext.stroke();
    // numerals
    digitContext.textAlign = 'center';
    digitContext.textBaseline = 'middle';
    digitContext.font = stdFont;
    digitContext.fillStyle = valueForeColor;
    // put the digits 901234567890 vertically into the buffer
    for (var i = 9; i < 21; i++) {
      digitContext.fillText(i % 10, digitWidth * 0.5,
          verticalSpace * (i - 9) + verticalSpace / 2);
    }

    // Create a decimal column
    if (decimals > 0) {
      // background
      decimalContext.rect(0, 0, digitWidth, columnHeight * 1.1);
      decimalContext.fillStyle = decimalBackColor;
      decimalContext.fill();
      // edges
      decimalContext.strokeStyle = '#f0f0f0';
      decimalContext.lineWidth = '1px'; //height * 0.1 + "px";
      decimalContext.moveTo(0, 0);
      decimalContext.lineTo(0, columnHeight * 1.1);
      decimalContext.stroke();
      decimalContext.strokeStyle = '#202020';
      decimalContext.moveTo(digitWidth, 0);
      decimalContext.lineTo(digitWidth, columnHeight * 1.1);
      decimalContext.stroke();
      // numerals
      decimalContext.textAlign = 'center';
      decimalContext.textBaseline = 'middle';
      decimalContext.font = stdFont;
      decimalContext.fillStyle = decimalForeColor;
      // put the digits 901234567890 vertically into the buffer
      for (var i = 9; i < 21; i++) {
        decimalContext.fillText(i % 10, digitWidth * 0.5,
            verticalSpace * (i - 9) + verticalSpace / 2);
      }
    }
    // wobble factors
    for (var i = 0; i < (digits + decimals); i++) {
      wobble[i] =
          Math.random() * wobbleFactor * height - wobbleFactor * height / 2;
    }
  }

  function drawDigits() {
    var pos = 1;
    var val;

    val = value;
    // do not use Math.pow() - rounding errors!
    for (var i = 0; i < decimals; i++) {
      val *= 10;
    }

    var numb = Math.floor(val);
    var frac = val - numb;
    numb = String(numb);
    var prevNum = 9;

    for (var i = 0; i < decimals + digits; i++) {
      var num = +numb.substring(numb.length - i - 1, numb.length - i) || 0;
      if (prevNum != 9) {
        frac = 0;
      }
      if (i < decimals) {
        backgroundContext.drawImage(decimalBuffer, width - digitWidth * pos,
            -(verticalSpace * (num + frac) + zeroOffset + wobble[i]));
      } else {
        backgroundContext.drawImage(digitBuffer, width - digitWidth * pos,
            -(verticalSpace * (num + frac) + zeroOffset + wobble[i]));
      }
      pos++;
      prevNum = num;
    }
  }

  this.setValue = function(newVal) {
    value = newVal;
    if (value < 0) {
      value = 0;
    }
    this.repaint();
  };

  this.getValue = function() {
    return value;
  };

  this.repaint = function() {
    if (!initialized) {
      init();
    }

    // draw digits
    drawDigits();

    // draw the foreground
    backgroundContext.drawImage(foregroundBuffer, 0, 0);

    // paint back to the main context
    ctx.drawImage(backgroundBuffer, 0, 0);
  };

  this.repaint();

  function createBuffer(width, height) {
    var buffer = doc.createElement('canvas');
    buffer.width = width;
    buffer.height = height;
    return buffer;
  }
};
