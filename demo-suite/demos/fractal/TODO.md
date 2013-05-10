* Start the map when a minimal number of servers are up.

* Better map zooming - currently, the left map controls both maps. Both maps
should have the same control.

* Make it easier to update program on VMs without restarting.  Push new
program/params and have something in guest quit and be restarted.

* build a new image map that will only load N tiles at a time. This should make
this more fair between the two maps.

* Add a memcached layer for caching tiles

* Start exporting/collecting statistics on # of tiles served, avg latency, etc.

* Pound on the thing with apache bench

* Run the 16 servers across 2 zones.
