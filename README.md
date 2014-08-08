ClusterTop
==========
ClusterTop was created as a way to pull data from zabbix and push it into other systems.
The original use case was to push data from zabbix into graphite to leverage some of the nicer graphite dashboards.
However it has been designed (for the most part) to be pretty much independent of graphite.

Architecture
============
Clustertop is built around the idea of pollers. A poller grabs data from zabbix and in turn pushes it somewhere else.
The base system comes with two pollers. clustertop.pollers.Poller and clustertop.pollers.GraphitePoller. To write your own
poller you simply make a subclass of clustertop.pollers.Poller and write a poll_complete method.


Future Plans
============
Write now there are two bits of code that are very specific to my use case. Those are the bootstrap system and the tasseo
dashboard export system. Eventually these will go away, or be turned into something generic. I also want to change how
pollers work a little bit. Write now you can't mix and match existing pollers to create something new. I want to eventually
create a mixin style system of extending pollers.
