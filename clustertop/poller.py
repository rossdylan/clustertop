from pyzabbix import ZabbixAPI
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from clustertop.types import Host
import time


class Poller(object):
    """
    This poller will automatically grab a set of hosts and poll a given set of
    items for their values. This class is designed to be extended.
    Subclasses will implement their own poll_complete which is called
    when a poll is complete
    """

    def __init__(self, zhost, user, passwd, host_names, interval, item_key):
        self.thread_pool = ThreadPool(min(cpu_count(), len(host_names)))
        self.zapi = ZabbixAPI(zhost)
        self.zapi.login(user, passwd)
        self.hosts = [Host(hn, self.zapi) for hn in host_names]
        self.interval = interval
        self.item_key = item_key

    def poll_complete(self):
        """
        This method intentionally left blank
        """
        for host in self.hosts:
            print(host.name)
            for key, item in host.items.iteritems():
                if 'cpu.util[' in key:
                    print("\t{0}: {1}".format(key, item['lastvalue']))

    def poll(self):
        """
        Use our internal threadpool to grab the latest data for each host
        from zabbix. This function then calls self.poll_complete
        """
        self.thread_pool.map(lambda h: h.get_items(subset=self.item_key), self.hosts)
        self.poll_complete()

    def poll_loop(self):
        """
        The main loop for the poller. It executes self.poll() and then sleeps
        self.interval seconds until the next call to self.poll()
        """
        while True:
            self.poll()
            time.sleep(self.interval)
