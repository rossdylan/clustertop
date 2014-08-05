from clustertop.poller import Poller
from clustertop.bootstrap import bootstrapper
from ConfigParser import ConfigParser
import argparse


def main():
    parser = argparse.ArgumentParser(
        description='Control the cluster top backend')
    parser.add_argument('command', choices=['check', 'run', 'bootstrap'])
    parser.add_argument('--config', type=str, default='/etc/clustertop')
    args = parser.parse_args()
    cf = ConfigParser()
    cf.read(args.config)
    zhost = cf.get('main', 'zabbix_host')
    user = cf.get('main', 'zabbix_user')
    passwd = cf.get('main', 'zabbix_pass')
    hosts = cf.get('main', 'hosts').split(',')

    if args.command == 'bootstrap':
        bootstrapper(zhost, user, passwd, hosts)
    elif args.command == 'run':
        poller = Poller(cf)
        poller.poll_loop()
    elif args.command == 'check':
        poller = Poller(cf)
        poller.poll()
