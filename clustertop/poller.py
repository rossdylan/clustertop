from pyzabbix import ZabbixAPI
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
import time


class Host(object):
    """
    This is an abstraction around a Host in zabbix
    Each host has multiple items
    """
    def __init__(self, name, zapi):
        self.zapi = zapi
        self.name = name
        self.items = {}
        self.interfaces = {}
        self.host_data = self.zapi.host.get(
            output="extend",
            search={
                "name": name
            })[0]
        self._dinter = None  # Default interface

    def get_interfaces(self):
        """
        Grab the latest information on this hosts interfaces
        using the zabbix api
        """
        interfaces = self.zapi.hostinterface.get(
            output='extend',
            hostids=self.host_data['hostid']
        )
        for inter in interfaces:
            self.interfaces[inter['ip']] = inter

    @property
    def default_interface(self):
        """
        Property function to grab the default interface for this host
        It makes sure its an actual interface with a IP
        """
        if self._dinter is None:
            self.get_interfaces()
            for ip, val in self.interfaces.iteritems():
                if ip != '127.0.0.1' and ip != '0.0.0.0':
                    self._dinter = val
                    break
            self._dinter = None
        return self._dinter

    def get_items(self, subset=""):
        """
        Grab the latest information on this hosts items
        using the zabbix api
        :param subset: Specify an item _key that limits what items to update
        :type subset: str
        """
        search = {
            "hostid": self.host_data['hostid'],
        }
        if subset != "":
            search['key_'] = subset
        items = self.zapi.item.get(
            output="extend",
            search=search)

        for item in items:
            self.items[item['key_']] = item

    def add_item(self, **properties):
        """
        Add an item to this host
        """
        properties['hostid'] = self.host_data['hostid']
        properties['interfaceid'] = self.default_interface['interfaceid']
        self.zapi.item.create(**properties)


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
