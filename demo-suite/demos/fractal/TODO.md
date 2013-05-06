* Improve health checks.  Either move them to the client, parallelize on the
server or do in a queue on the server.

* Start the map when a minimal number of servers are up.

* Better map zooming - currently, the left map controls both maps. Both maps
should have the same control.

* Look at using SPDY to speed up image download

* Make it easier to update program on VMs without restarting.  Push new
program/params and have something in guest quit and be restarted.

* Figure out a way to have smaller tiles load well so that we can show
incremental/shared behavior.  Chrome seems to have a limit of ~10 images in
flight at a time. The 'single server' cluster gets its images loaded first and
ends up looking faster.

* Add a memcached layer for caching tiles

* Start exporting/collecting statistics on # of tiles served, avg latency, etc.

* Pound on the thing with apache bench
