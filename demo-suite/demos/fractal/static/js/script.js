/**
 * @fileoverview Fractal demo JavaScript code.
 *
 * Displays zoomable, panable fractal images, comparing tile load of 1
 * instance to 16.
 */

var fractal1

$(document).ready(function() {
  $('.btn').button();
  configSpinner();
  var fractal16 = new Fractal($('#fractal16'), FAST_MAP_INSTANCE_TAG,
    NUM_FAST_MAP_INSTANCES);
  fractal16.initialize();
  fractal1 = new Fractal($('#fractal1'), SLOW_MAP_INSTANCE_TAG,
    NUM_SLOW_MAP_INSTANCES, fractal16);
  fractal1.initialize();

  $('#start').click(function() {
    fractal1.start();
    fractal16.start();
  });
  $('#reset').click(function() {
    fractal1.reset();
    fractal16.reset();
  });

  fractal1.checkRunning();
  fractal16.checkRunning();
});

/**
 * Total number of instances to start for the 'slow' map.
 * @type {number}
 * @constant
 */
var NUM_SLOW_MAP_INSTANCES = 1;

/**
 * Name for 'slow' map.
 * @type {string}
 * @constant
 */
var SLOW_MAP_INSTANCE_TAG = 'map1';

/**
 * Total number of instances to start for the 'slow' map.
 * @type {number}
 * @constant
 */
var NUM_FAST_MAP_INSTANCES = 16;

/**
 * Name for 'slow' map.
 * @type {string}
 * @constant
 */
var FAST_MAP_INSTANCE_TAG = 'map16';


/**
 * Configure spinner to show when there is an outstanding Ajax request.
 *
 * This really helps to show that something is going on.  It is the
 * simplest blinking light that we can add.
 */
function configSpinner() {
  $('#spinner')
    .css('visibility', 'hidden')
    .ajaxStart(function() {
        $('#spinner').css('visibility', '');
    })
    .ajaxStop(function() {
        $('#spinner').css('visibility', 'hidden');
    })
  ;
}

/**
 * Fractal class.
 * @param {Element} container HTML element in which to display the map.
 * @param {string} tag A unique string ('single') used to identify instances
 * @param {number} num_instances Number of instances to start
 * @param {Fractal} slave_fractal Another fractal instance to sync map
 *  position and zoom to.
 * @constructor
 */
var Fractal = function(container, tag, num_instances, slave_fractal) {
  /**
   * An HTML object that will contain this fractal map.
   * @type {Element}
   * @private
   */
  this.container_ = container;

  /**
   * The element that holds the map itself.
   * @type {Element}
   * @private
   */
  this.mapContainer_ = null;


  /**
   * The squares object that will track the state of the VMs.
   * @type {Squares}
   * @private
   */
  this.squares_ = null;

  /**
   * A unique string to use for naming instances. Also used as a user visible
   *  label on the map.
   * @type {string}
   * @private
   */
  this.tag_ = tag;

  /**
   * The GCE control object.
   * @type {GCE}
   * @private
   */
  this.gce_ = null;

  /**
   * The Map control object
   * @type {Map}
   */
  this.map = null;

  /**
   * The number of instances to launch for this map.
   * @type {[type]}
   * @private
   */
  this.num_instances_ = num_instances;

  /**
   * The other Fractal instance to sync our zoom/position to.
   * @type {Fractal}
   */
  this.slave_fractal_ = slave_fractal;
};

/**
 * The map center latitude.
 * @type {number}
 * @private
 */
Fractal.prototype.LATITUDE_ = -78.35;

/**
 * The map center longitude.
 * @type {number}
 * @private
 */
Fractal.prototype.LONGITUDE_ = 157.5;

/**
 * The default tile size
 * @type {Number}
 */
Fractal.prototype.TILE_SIZE_ = 256;

/**
 * The minimum zoom on the map
 * @type {Number}
 */
Fractal.prototype.MIN_ZOOM_ = 0;

/**
 * The maximum zoom of the map.
 * @type {Number}
 */
Fractal.prototype.MAX_ZOOM_ = 30;

/**
 * Initialize the UI and check if there are instances already up.
 */
Fractal.prototype.initialize = function() {
  // Set up the DOM under container_
  var squaresRow = $('<div>').addClass('row').addClass('squares-row');
  var squaresContainer = $('<div>').addClass('span6').addClass('squares');
  squaresRow.append(squaresContainer);
  $(this.container_).append(squaresRow);

  var mapRow = $('<div>').addClass('row').addClass('map-row');
  $(this.container_).append(mapRow);

  // Initialize the squares
  var instanceNames = [];
  for (var i = 0; i < this.num_instances_; i++) {
    instanceNames.push(DEMO_NAME + '-' + this.tag_ + '-' + padNumber(i, 2));
  }

  this.squares_ = new Squares(
      squaresContainer.get(0), instanceNames, {
        cols: 8
      });
  this.squares_.drawSquares();

  // DEMO_NAME is set in the index.html template file.
  this.gce_ = new Gce('/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/instance',
      '/' + DEMO_NAME + '/cleanup',
      null, { 'tag': this.tag_ });
  this.gce_.setOptions({
      squares: this.squares_
    });
}

/**
 * Check to see if things are already running. If so, start up the map. Good
 *    on a refresh when the map is already loaded.
 */
Fractal.prototype.checkRunning = function() {
  var that = this;
  that.gce_.getInstanceStates(function(data, stateSummary) {
    if (stateSummary['SERVING'] >= that.num_instances_) {
      that.mapIt_(data);
    }
  });
};


/**
 * Start up the instances if necessary. When the instances are confirmed to be
 *  running then show the map.
 */
Fractal.prototype.start = function() {
  this.startInstances_();
};

/**
 * Reset the map.  Shut down the instances and clear the map.
 */
Fractal.prototype.reset = function() {
    this.stopMap_();
    this.gce_.stopInstances();
};

Fractal.prototype.startInstances_ = function() {
  var that = this;
  this.gce_.startInstances(that.num_instances_, {
    data: {
      'num_instances': that.num_instances_
    },
    checkServing: true,
    callback: function(data) {
      that.mapIt_(data);
    }
  })
}

/**
 * Try to cleanup/delete any running map
 */
Fractal.prototype.stopMap_ = function() {
  if (this.map) {
    this.map.unbindAll();
    delete this.map;
  }
  if (this.mapContainer_) {
    $(this.mapContainer_).remove();
    this.mapContainer_ = null;
  }
}

/**
 * Get external IPs, create maps, add listeners to maps.
 * @param {Object} data Data returned from the list instances call to GCE.
 * @private
 */
Fractal.prototype.mapIt_ = function(data) {
  this.stopMap_();
  var ips = this.getIps_(data);
  this.map = this.prepMap_(ips);
  this.addListeners_();
};

/**
 * Set map options and draw a map on HTML page.
 * @param {Array.<string>} ips An array of IPs.
 * @return {google.maps.Map} Returns the map object.
 * @private
 */
Fractal.prototype.prepMap_ = function(ips) {
  var numInstances = ips.length;

  var that = this;
  var fractalTypeOptions = {
    getTileUrl: function(coord, zoom) {
      var url = ['http://'];
//      if (ips.length > 1) {
      if (false) {
        var instanceIdx = Math.abs(coord.x + (4 * coord.y)) % numInstances;
        // var instanceIdx = Math.abs(Math.round(coord.x * Math.sqrt(numInstances) + coord.y)) % numInstances;
        url.push(ips[instanceIdx]);
      } else {
        url.push(ips[0]);
      }
      var params = {
        z: zoom,
        x: coord.x,
        y: coord.y,
        'tile-size': that.TILE_SIZE_,
      };
      url.push('/tile?');
      url.push($.param(params));

      return url.join('');
    },
    tileSize: new google.maps.Size(this.TILE_SIZE_, this.TILE_SIZE_),
    maxZoom: this.MAX_ZOOM_,
    minZoom: this.MIN_ZOOM_,
    name: 'Mandelbrot',
  };

  this.mapContainer_ = $('<div>');
  this.mapContainer_.addClass('span6');
  this.mapContainer_.addClass('map-container');
  $(this.container_).find('.map-row').append(this.mapContainer_);
  var map = this.drawMap_(this.mapContainer_,
      fractalTypeOptions, 'Mandelbrot');
  return map;
};

/**
 * Add listeners to maps so that they zoom and pan in unison.
 * @private
 */
Fractal.prototype.addListeners_ = function() {
  // Add listeners to the map on the left so that the zoom and center
  // is reflected on both maps.
  if (this.slave_fractal_) {
    var that = this;
    google.maps.event.addListener(this.map, 'zoom_changed', function() {
      if (that.slave_fractal_.map) {
        var zoom = that.map.getZoom();
        that.slave_fractal_.map.setZoom(zoom);
      }
    });
    google.maps.event.addListener(this.map, 'center_changed', function() {
      if (that.slave_fractal_.map) {
        var center = that.map.getCenter();
        that.slave_fractal_.map.setCenter(center);
      }
    });
  }
};

/**
 * Get the external IPs of the instances from the returned data.
 * @param {Object} data Data returned from the list instances call to GCE.
 * @return {Object} The list of ips.
 * @private
 */
Fractal.prototype.getIps_ = function(data) {
  var ips = [];
  var slowMapIps = [];
  for (var instanceName in data) {
    ips.push(data[instanceName]['externalIp']);
  }
  return ips;
};

/**
 * Draw the map.
 * @param {JQuery} canvas The HTML element in which to display the map.
 * @param {Object} fractalTypeOptions Options for displaying the map.
 * @param {string} mapTypeId A unique map type id.
 * @return {google.maps.Map} Returns the map object.
 * @private
 */
Fractal.prototype.drawMap_ = function(canvas, fractalTypeOptions, mapTypeId) {
  var fractalMapType = new google.maps.ImageMapType(fractalTypeOptions);

  var mapOptions = {
    center: new google.maps.LatLng(this.LATITUDE_, this.LONGITUDE_),
    zoom: this.MIN_ZOOM_,
    streetViewControl: false,
    mapTypeControlOptions: {
      mapTypeIds: [mapTypeId]
    },
    zoomControlOptions: {
      style: google.maps.ZoomControlStyle.SMALL
    }
  };

  var map = new google.maps.Map(canvas.get(0), mapOptions);
  map.mapTypes.set(mapTypeId, fractalMapType);
  map.setMapTypeId(mapTypeId);
  return map;
};
