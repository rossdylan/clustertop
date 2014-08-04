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
