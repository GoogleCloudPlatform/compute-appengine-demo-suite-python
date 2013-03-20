/**
 * @fileoverview Quick Start JavaScript.
 *
 * Initializes instances, updates UI display to show running time and number
 * of running instances. Stops running instances.
 */

$(document).ready(function() {
  var quickStart = new QuickStart();
  quickStart.initialize();
});

/**
 * Quick Start class.
 * @constructor
 */
var QuickStart = function() { };

/**
 * Initialize the UI and check if there are instances already up.
 */
QuickStart.prototype.initialize = function() {
  var gce = new Gce('/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/cleanup');
  gce.checkIfAlive(function(data, numAlive) {
    if (numAlive != 0) {
      $('#start').addClass('disabled');
      $('#reset').removeClass('disabled');
      alert('Some instances are already running! Hit reset.');
    }
  });

  var counter = new Counter(document.getElementById('counter'));
  var timer = new Timer(document.getElementById('timer'));
  this.initializeButtons_(gce, counter, timer);
};

/**
 * Initialize UI controls.
 * @param {Object} gce Instance of Gce class.
 * @param {Object} counter Instance of the Counter class.
 * @param {Object} timer Instance of the Timer class.
 * @private
 */
QuickStart.prototype.initializeButtons_ = function(gce, counter, timer) {
  $('.btn').button();

  $('#start').click(function() {
    $('#start').addClass('disabled');

    // Get the number of instances entered by the user.
    var numInstances = parseInt($('#num-instances').val(), 10);
    if (numInstances > 1000) {
      alert('Max instances is 1000, starting 1000 instead.');
      numInstances = 1000;
    }
    if (numInstances <= 0) {
      alert('At least one instance needs to be started, starting 1 instead.');
      numInstances = 1;
    }

    var instanceNames = [];
    for (var i = 0; i < numInstances; i++) {
      instanceNames.push(DEMO_NAME + '-' + i);
    }

    // Initialize the squares, set the Gce options, and start the instances.
    var squares = new Squares(
        document.getElementById('instances'), instanceNames, {
          drawOnStart: true
        });
    gce.setOptions({
      squares: squares,
      counter: counter,
      timer: timer
    });
    gce.startInstances(numInstances, {
      data: {'num_instances': numInstances},
      callback: function() {
        $('#reset').removeClass('disabled');
      }
    });
  });

  // Initialize reset button click event to stop instances.
  $('#reset').click(function() {
    gce.stopInstances(function() {
      $('#start').removeClass('disabled');
      $('#reset').addClass('disabled');
    });
  });
};
