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

    def __init__(self, config):
        self.config = config
        self.zapi = ZabbixAPI(config.get('main', 'zabbix_host'))
        self.zapi.login(config.get('main', 'zabbix_user'),
                        config.get('main', 'zabbix_pass'))
        host_names = config.get('main', 'hosts').split(',')
        self.hosts = [Host(hn, self.zapi) for hn in host_names]
        self.thread_pool = ThreadPool(min(cpu_count(), len(host_names)))
        self.interval = config.getint('main', 'update_interval')
        self.item_keys = config.get('main', 'item_keys').split(',')

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
        self.thread_pool.map(lambda h: h.get_items(subset=self.item_keys), self.hosts)
        self.poll_complete()

    def poll_loop(self):
        """
        The main loop for the poller. It executes self.poll() and then sleeps
        self.interval seconds until the next call to self.poll()
        """
        while True:
            self.poll()
            time.sleep(self.interval)
