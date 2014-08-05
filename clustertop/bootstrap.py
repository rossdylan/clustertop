from pyzabbix import ZabbixAPI
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from clustertop.types import Host


def add_check(host):
    """
    Add the checks that we care about. Eventually this will need to be
    configured using the config file.
    :param host: The host object we are adding a check to
    :type host: clustertop.types.Host
    """
    host.get_items()
    # Add a check for memory usage
    memory_types = ['total', 'free', 'buffers', 'cached', 'used']
    for mt in memory_types:
        mem_key = 'vm.memory.size[{0}]'.format(mt)
        if mem_key not in host.items:
            print("Adding {0}".format(mem_key))
            host.add_item(name='{0} memory'.format(mt),
                          key_=mem_key,
                          type=0,
                          value_type=0,
                          delay=10)
            print('Added {0} to {1}'.format(mem_key, host.name))

    numcpus = host.items.get('system.cpu.num', {'lastvalue': 0})
    numcpus = int(numcpus['lastvalue'])
    # Cycle through all CPUs this machine has and add utilization checks
    for i in xrange(0, numcpus):
        item_key = 'system.cpu.util[{0},user]'.format(i)
        if item_key not in host.items:
            host.add_item(name='CPU #{0} Utilisation'.format(i),
                          key_=item_key,
                          type=0,
                          value_type=0,
                          delay=10)
            print('Added cpu check to {0}:{1}'.format(host.name, i))


def bootstrapper( zhost, user, passwd, hosts):
    """
    Function to go through the given hosts and make sure
    they have the items cluster top requires. Cluster top really
    only needs system.cpu.util[*,user] where * is an integer 1-n
    where n is the number of cpus in that host
    :param zhost: The hostname of the zabbix server
    :type zhost: str
    :param user: The username to log into zabbix with
    :type user: str
    :param passwd: The password to log into zabbix with
    :type passwd: str
    :param hosts: A list of hosts to bootstrap
    :type hosts: list
    """
    thread_pool = ThreadPool(min(cpu_count(), len(hosts)))
    zapi = ZabbixAPI(zhost)
    zapi.login(user, passwd)
    hosts = [Host(hn, zapi) for hn in hosts]
    thread_pool.map(lambda h: add_check(h), hosts)
