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

// Recovery mode flag, initialized to false.
var Recovering = false;

// Starting and resetting notification strings.
var STARTING = 'Starting...';
var RESETTING = 'Resetting...';

/**
 * Initialize the UI and check if there are instances already up.
 */
QuickStart.prototype.initialize = function() {
  var gce = new Gce('/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/cleanup');

  gce.getInstanceStates(function(data) {
    var numInstances = parseInt($('#num-instances').val(), 10);
    var currentInstances = data['stateCount']['TOTAL'];
    if (currentInstances != 0) {
      // Instances are already running so we're in recovery mode. Calculate 
      // current elapsed time and set timer element accordingly.
      var startTime = parseInt($('#start-time').val(), 10);
      var currentTime = Math.round(new Date().getTime() / 1000)
      var elapsedTime = currentTime - startTime;
      Timer.prototype.setOffset(elapsedTime);

      // In order to draw grid, maintain counter and timer, and start 
      // status polling, we simulate start click with number of instances 
      // last started, but we set Recovering flag to true to inhibit 
      // sending of start request to GCE.
      Recovering = true;
      $('#start').click();
      var targetInstances = parseInt($('#target-instances').val(), 10);
      if (targetInstances == 0) {
        $('#reset').click();
      }

      // In recovery mode, resets are ok but don't let user resend start,
      // because duplicate starts can cause confusion and perf problems.
      $('#start').addClass('disabled');
      $('#reset').removeClass('disabled');
    }
  });

  this.counter_ = new Counter(document.getElementById('counter'), 'numRunning');
  this.timer_ = new Timer(document.getElementById('timer'));
  this.initializeButtons_(gce);
};

/**
 * Initialize UI controls.
 * @param {Object} gce Instance of Gce class.
 * @private
 */
QuickStart.prototype.initializeButtons_ = function(gce) {
  $('.btn').button();

  var that = this;
  $('#start').click(function() {
    // Get the number of instances entered by the user.
    var numInstances = parseInt($('#num-instances').val(), 10);
    if (numInstances > 1000) {
      alert('Max instances is 1000, starting 1000 instead.');
      numInstances = 1000;
    } else if (numInstances < 0) {
      alert('At least one instance needs to be started.');
      return;
    } else if (numInstances === 0) {
      return;
    }

    // Start requested, disable start button but allow reset while starting.
    $('#start').addClass('disabled');
    $('#reset').removeClass('disabled');
    $('#in-progress').text(STARTING);

    var instanceNames = [];
    for (var i = 0; i < numInstances; i++) {
      instanceNames.push(DEMO_NAME + '-' + i);
    }

    // Initialize the squares, set the Gce options, and start the instances.
    var squares = new Squares(
        document.getElementById('instances'), instanceNames, {
          drawOnStart: true
        });
    that.counter_.targetState = 'RUNNING';
    gce.setOptions({
      squares: squares,
      counter: that.counter_,
      timer: that.timer_
    });
    gce.startInstances(numInstances, {
      data: {'num_instances': numInstances},
      callback: function() {
        // Start completed, start button should already be disabled, and
        // reset button should already be enabled.
        $('#in-progress').text('');
        if (Recovering) {
          Recovering = false;
        }
      }
    });
  });

  // Initialize reset button click event to stop instances.
  $('#reset').click(function() {
    that.counter_.targetState = 'TOTAL';
    //$('#num-instances').val(0);
    // Reset requested, disable start button but allow resending of reset.
    $('#start').addClass('disabled');
    $('#reset').removeClass('disabled');
    $('#in-progress').text(RESETTING);
    gce.stopInstances(function() {
      // Reset completed, allow start button and disallow reset button.
      $('#start').removeClass('disabled');
      $('#reset').addClass('disabled');
      $('#in-progress').text('');
      if (Recovering) {
        Recovering = false;
      }
    });
  });
};
