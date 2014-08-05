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
            'hostid': self.host_data['hostid'],
            'key_': subset,
        }
        items = self.zapi.item.get(
            output="extend",
            searchByAny=True,
            filter=item_filter)

        for item in items:
            self.items[item['key_']] = item

    def add_item(self, **properties):
        """
        Add an item to this host
        """
        properties['hostid'] = self.host_data['hostid']
        print(self.default_interface)
        properties['interfaceid'] = self.default_interface['interfaceid']
        self.zapi.item.create(**properties)
