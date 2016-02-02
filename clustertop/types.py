from pyzabbix import ZabbixAPI


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
        self.hosts = self.zapi.host.get(
            output="extend",
            search={
                "name": name
            })
        self.host_data = self.hosts[0]
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
            self.interfaces[inter['dns']] = inter

    @property
    def default_interface(self):
        """
        Property function to grab the default interface for this host
        It makes sure its an actual interface with a IP
        """
        if self._dinter is None:
            self.get_interfaces()
            for ip, val in self.interfaces.iteritems():
                if val['main'] == '1':
                    self._dinter = val
                    break
        return self._dinter

    def get_items(self, subset=[]):
        """
        Grab the latest information on this hosts items
        using the zabbix api
        :param subset: Specify an item _key that limits what items to update
        :type subset: str
        """
        item_filter = {
            'key_': subset,
        }
        items = self.zapi.item.get(
            output="extend",
            hostids=self.host_data['hostid'],
            searchByAny=True,
            filter=item_filter)
        for item in items:
            if item['hostid'] == self.host_data['hostid']:
                self.items[item['key_']] = item

    def add_item(self, **properties):
        """
        Add an item to this host
        """
        properties['hostid'] = self.host_data['hostid']
        properties['interfaceid'] = self.default_interface['interfaceid']
        self.zapi.item.create(**properties)


def create_hosts(config):
    """
    Take in a config and return a list of Host objects
    This is used in all areas of clustertop so its been
    seperated into its own function.
    :param config: The ConfigParser object holding the clustertop config
    :type config: ConfigParser
    """
    zapi = ZabbixAPI(config.get('main', 'zabbix_host'))
    if config.has_option('main', 'zabbix_http_user') and config.has_option('main', 'zabbix_http_pass'):
        zapi.session.auth = (config.get('main', 'zabbix_http_user'),
                             config.get('main', 'zabbix_http_pass'))
    zapi.login(config.get('main', 'zabbix_user'),
               config.get('main', 'zabbix_pass'))
    return [Host(hn, zapi)
            for hn in config.get('main', 'hosts').split(',')]
