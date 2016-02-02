from gevent import monkey
monkey.patch_all()

import gevent
from clustertop.types import create_hosts
from collections import defaultdict
import time
import socket
import pickle
import struct


def retrieve_keys(host, keys):
    """
    Call out to zabbix and grab the keys we are interested in
    """
    host.get_items(subset=keys)


class Poller(object):
    """
    This poller will automatically grab a set of hosts and poll a given set of
    items for their values. This class is designed to be extended.
    Subclasses will implement their own poll_complete which is called
    when a poll is complete
    """

    def __init__(self, config):
        self.config = config
        self.hosts = create_hosts(config)
        self.interval = config.getint('main', 'update_interval')
        # keys are defined as zabbix key:graphite key
        self.item_keys = {}
        for key in config.get('main', 'item_keys').split(','):
            key = key.replace('|', ',')
            zabbix_and_graphite = key.split(':')
            if len(zabbix_and_graphite) == 2:
                self.item_keys[zabbix_and_graphite[0]] = zabbix_and_graphite[1]
            else:
                self.item_keys[zabbix_and_graphite[0]] = None

        """
        special keys are zabbix keys that are unique to a specific host
        they have the format of...
        [special:ion.rc.rit.edu]
        slurm.jobs.running=system.run[squeue | grep " R" | wc -l]
        slurm.jobs.pending=system.run[squeue | grep " PD" | wc -l]
        """
        self.special_keys = defaultdict(dict)
        for section in config.sections():
            parts = section.split(':')
            if len(parts) == 2:
                if parts[0] == 'special':
                    for g_key, z_key in config.items(section):
                        self.special_keys[parts[1]][z_key] = g_key

    def poll_complete(self):
        """
        This method intentionally left blank
        """
        for host in self.hosts:
            for key, item in host.items.iteritems():
                if key in self.item_keys or key in self.special_keys[host.name]:
                    print("{0}: {1} -> {2}".format(host.name, key, item['lastvalue']))

    def poll(self):
        """
        Use our internal threadpool to grab the latest data for each host
        from zabbix. This function then calls self.poll_complete
        """
        coros = []
        for host in self.hosts:
            keys = self.item_keys.keys() + self.special_keys[host.name].keys()
            coros.append(
                gevent.spawn(retrieve_keys, host, keys)
            )
        gevent.joinall(coros)
        self.poll_complete()

    def poll_loop(self):
        """
        The main loop for the poller. It executes self.poll() and then sleeps
        self.interval seconds until the next call to self.poll()
        """
        while True:
            self.poll()
            time.sleep(self.interval)


class GraphitePoller(Poller):
    """
    The Graphite poller takes data and sends it to graphite after each poll
    interval. The graphite server to use is configured using the [graphite]
    section of the config file.
    """
    def poll_complete(self):
        """
        Package up our current item state and send it to graphite
        We pull out graphite connection information from our config file
        """
        pick = self._create_pickles()
        graphite_host = self.config.get('graphite', 'host')
        graphite_port = self.config.getint('graphite', 'port')
        sock = socket.socket()
        sock.connect((graphite_host, graphite_port))
        sock.sendall(pick)
        sock.close()

    def _clean_key(self, key):
        """
        Quick and dirty way to turn a zabbix item key_ into a graphite path
        :param key: The zabbix item key_ to clean
        :type key: str
        :return A graphite compatible path
        :rtype str
        """
        return key.replace(',', '.').replace('[', '.').replace(']', '').replace('..', '.')

    def _create_pickles(self):
        """
        Transform out internal representation of a zabbix item into
        a graphite formatted pickle. The format is (path, (ctime, value))
        The path is reversed(hostname) + '.' + key_
        :return A properly encoded pickle that graphite understands as metrics
        :rtype str
        """
        data = []
        for host in self.hosts:
            reversed_dns = reversed(host.default_interface['dns'].split('.'))
            reversed_dns = '.'.join(reversed_dns)
            for key, item in host.items.iteritems():
                graphite_path = None
                if key in self.item_keys:
                    custom_graphite = self.item_keys[key]
                    if custom_graphite is not None:
                        graphite_path = '{0}.{1}'.format(reversed_dns,
                                                         custom_graphite)
                    else:
                        graphite_path = '{0}.{1}'.format(reversed_dns,
                                                         self._clean_key(key))
                elif key in self.special_keys[host.name]:
                    graphite_path = self.special_keys[host.name][key]
                if graphite_path is not None:
                    print('{0} -> {1}'.format(graphite_path, item['lastvalue']))
                    data.append((graphite_path, (time.time(), item['lastvalue'])))
        payload = pickle.dumps(data, protocol=2)
        msg = struct.pack("!L", len(payload)) + payload
        return msg
