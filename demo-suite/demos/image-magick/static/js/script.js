 /**
 * @fileoverview Image Magick demo JavaScript code.
 *
 * Displays status of instances in colored blocks, then displays processed
 * images uploaded to Cloud Storage from Compute Engine instances.
 */

$(document).ready(function() {
  var imageMagick = new ImageMagick();
  imageMagick.initialize();
});

/**
 * Image Magick class.
 * @constructor
 */
var ImageMagick = function() { };

/**
 * The interval to ping Cloud Storage for processed images.
 * @type {Object}
 * @private
 */
ImageMagick.prototype.imageInterval_ = null;

/**
 * The time between pings to Cloud Storage.
 * @type {number}
 * @private
 */
ImageMagick.prototype.IMAGE_INTERVAL_TIME_ = 2000;

/**
 * The number of instances to start.
 * @type {number}
 * @private
 */
ImageMagick.prototype.NUM_INSTANCES_ = 50;

/**
 * The Cloud Storage URL where image output is saved.
 * @type {string}
 * @private
 */
ImageMagick.prototype.CS_URL_ =
    'http://' + BUCKET + '.storage.googleapis.com';

/**
 * The URL that deletes CS objects.
 * @type {string}
 * @private
 */
ImageMagick.prototype.CLEAN_CS_URL_ = '/' + DEMO_NAME + '/gcs-cleanup';

/**
 * Initialize the UI and check if there are instances already up.
 */
ImageMagick.prototype.initialize = function() {
  var instanceNames = [];
  for (var i = 0; i < this.NUM_INSTANCES_; i++) {
    instanceNames.push(DEMO_NAME + '-' + i);
  }
  var squares = new Squares(
      document.getElementById('instances'), instanceNames, {
        cols: 25
      });
  squares.drawSquares();

  var gce = new Gce('/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/gce-cleanup', {
        squares: squares
      });
  gce.getInstanceStates(function(data) {
    if (data['stateCount']['TOTAL'] != 0) {
      $('#start').addClass('disabled');
      $('#reset').removeClass('disabled');
      alert('Some instances are already running! Hit reset.');
    }
  });
  this.initializeButtons_(gce, squares);
};

/**
 * Initialize UI controls.
 * @param {Object} gce Instance of Gce class.
 * @param {Object} squares Instance of the Squares class.
 * @private
 */
ImageMagick.prototype.initializeButtons_ = function(gce, squares) {
  $('.btn').button();

  var that = this;
  $('#start').click(function() {
    $('#start').addClass('disabled');

    gce.startInstances(that.NUM_INSTANCES_, {
      data: {'num_instances': that.NUM_INSTANCES_},
      callback: function() {
        that.imageInterval_ = setInterval(function() {
          that.displayImages_(squares);
        }, that.IMAGE_INTERVAL_TIME_);
      }
    });
  });

  $('#reset').click(function() {
    // Remove squares and display shut down message.
    $(document.getElementById('instances')).empty();
    $(document.getElementById('instances')).html('...shutting down...');
    if (that.imageInterval_) {
      clearInterval(that.imageInterval_);
    }

    // Stop instances and remove Cloud Storage contents.
    gce.stopInstances(function() {
      $('#start').removeClass('disabled');
      $('#reset').addClass('disabled');
      $(document.getElementById('instances')).empty();
      squares.drawSquares();
    });
    $.ajax({
      type: 'POST',
      url: that.CLEAN_CS_URL_
    });
  });
};

/**
 * Ping Cloud Storage to get processed images.
 * @param {Object} squares Instance of the Squares class.
 * @private
 */
ImageMagick.prototype.displayImages_ = function(squares) {
  var that = this;
  var url = this.CS_URL_;
  if (DIRECTORY) {
    url += '?prefix=' + DIRECTORY + '/';
  }
  $.ajax({
    url: url,
    dataType: 'xml',
    success: function(xml) {
      var imageCount = 0;
      $(xml).find('Contents').each(function() {
        var imagePath = $(this).find('Key').text();
        // Key = output/<image>.png
        var instanceName = imagePath.replace('.gif', '');
        if (DIRECTORY) {
          instanceName = instanceName.replace(DIRECTORY + '/', '');
        }

        // If the image hasn't been added, add it.
        square = squares.getSquareDiv(instanceName);
        if (square.find('img').length < 1) {
          square.empty();
          img = $('<img>').attr('src', that.CS_URL_ + '/' + imagePath);
          square.append(img);
        }

        imageCount++;
        if (imageCount == that.NUM_INSTANCES_) {
          clearInterval(that.imageInterval_);
          $('#reset').removeClass('disabled');
        }
      });
    }
  });
};
