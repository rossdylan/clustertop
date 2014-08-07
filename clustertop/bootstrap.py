from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool
from clustertop.types import create_hosts
import json


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
    if 'system.cpu.num' not in host.items:
        host.add_item(name='Number of CPUs',
                      key_='system.cpu.num',
                      type=0,
                      value_type=0,
                      delay=180)
    host.get_items()
    numcpus = host.items.get('system.cpu.num', {'lastvalue': 0})
    numcpus = int(float(numcpus['lastvalue']))
    print('{0} has {1} CPUs'.format(host.name, numcpus))
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


def _clean_key(key):
    return key.replace(',', '.').replace('[', '.').replace(']', '').replace('..', '.')


def bootstrapper(config):
    """
    Function to go through the given hosts and make sure
    they have the items cluster top requires. Cluster top really
    only needs system.cpu.util[*,user] where * is an integer 1-n
    where n is the number of cpus in that host
    :param config: The clustertop configparser instance
    :type config: ConfigParser
    """
    hosts = create_hosts(config)
    thread_pool = ThreadPool(min(cpu_count(), len(hosts)))
    thread_pool.map(lambda h: add_check(h), hosts)


def output_tasseo_json(host):
    """
    Generate a tasseo dashboard file for all the cpu utilization
    metrics for this host
    :param host: The Host object we are generating a dashboard for
    :type host: Host
    """
    host.get_items()
    blobs = []
    reversed_dns = reversed(host.default_interface['dns'].split('.'))
    reversed_dns = '.'.join(reversed_dns)
    shortname = host.name.split('.')[0]
    for key, item in host.items.iteritems():
        graphite_path = '{0}.{1}'.format(reversed_dns, _clean_key(key))
        if 'system.cpu.util' in graphite_path and graphite_path.endswith('user'):
            cpu_num = graphite_path.split('.')[-2]
            if cpu_num != 'util':
                cpu_num = int(cpu_num)
            else:
                continue
            d = {'alias': '{0} CPU {1} Util'.format(shortname, cpu_num),
                 'target': graphite_path}
            blobs.append(d)
    return sorted(blobs, key=lambda x: x['target'])


def create_tasseo_dashboards(config):
    """
    Create a series of .js files that correspond to a tasseo dashboard
    per host. Each dashboard has all the system.cpu.util.<cpu num>.user metrics
    for that host
    :param config: The clustertop configparser instance
    :type config: ConfigParser
    """
    hosts = create_hosts(config)
    for host in hosts:
        metrics = json.dumps(output_tasseo_json(host))
        shortname = host.name.split('.')[0]
        dashboard = 'var title = "\\"Near Real Time\\" Data for {0}"; var metrics = {1};'.format(shortname, metrics)
        with open('{0}.js'.format(shortname), 'w') as fd:
            fd.write(dashboard)
            print("Wrote dashboard file for {0}".format(shortname))
