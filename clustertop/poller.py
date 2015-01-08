from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from clustertop.types import create_hosts
from collections import defaultdict
import time
import socket
import pickle
import struct


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
        self.thread_pool = ThreadPool(min(cpu_count(), len(self.hosts)))
        self.interval = config.getint('main', 'update_interval')
        self.item_keys = config.get('main', 'item_keys').split(',')

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
            print(host.name)
            for key, item in host.items.iteritems():
                if any([k in key for k in self.item_keys]):
                    print("\t{0}: {1}".format(key, item['lastvalue']))

    def poll(self):
        """
        Use our internal threadpool to grab the latest data for each host
        from zabbix. This function then calls self.poll_complete
        """
        def retrieve(host):
            special_keys = self.special_keys[host.name].keys()
            host.get_items(subset=self.item_keys + special_keys)
        self.thread_pool.map(retrieve, self.hosts)
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
        graphite_host = self.config.get('graphite', 'host')
        graphite_port = self.config.getint('graphite', 'port')
        sock = socket.socket()
        sock.connect((graphite_host, graphite_port))
        sock.sendall(self._create_pickles())
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
                combined = self.item_keys + self.special_keys[host.name].keys()
                if any([(k in key or k is key) for k in combined]):
                    if key in self.special_keys[host.name]:
                        graphite_path = self.special_keys[host.name][key]
                    else:
                        graphite_path = '{0}.{1}'.format(reversed_dns, self._clean_key(key))
                    data.append((graphite_path,
                                (time.time(), item['lastvalue'])))
        payload = pickle.dumps(data, protocol=2)
        msg = struct.pack("!L", len(payload)) + payload
        return msg
