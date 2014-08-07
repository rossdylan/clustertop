from clustertop.poller import Poller
from clustertop.bootstrap import bootstrapper, create_tasseo_dashboards
from ConfigParser import ConfigParser
import argparse
import importlib



def main():
    parser = argparse.ArgumentParser(
        description='Control the cluster top backend')
    parser.add_argument('command', choices=['check', 'run', 'bootstrap', 'tasseo'])
    parser.add_argument('--config', type=str, default='/etc/clustertop')
    args = parser.parse_args()
    cf = ConfigParser()
    cf.read(args.config)
    the_poller = Poller
    if cf.has_option('main', 'poller'):
        mod_path, cls = cf.get('main', 'poller').split(':')
        module = importlib.import_module(mod_path)
        the_poller = getattr(module, cls)

    if args.command == 'bootstrap':
        bootstrapper(cf)
    elif args.command == 'run':
        poller = the_poller(cf)
        poller.poll_loop()
    elif args.command == 'check':
        poller = the_poller(cf)
        poller.poll()
    elif args.command == 'tasseo':
        create_tasseo_dashboards(cf)

