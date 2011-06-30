"""
Command line interface for piro.
"""
from argparse import ArgumentParser
import json
import os
import sys

import piro.config as conf


def load_plugins(path):
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith('.py') and not name.startswith('__'):
                path = os.path.join(root, name)
                # Strip .py and convert path separators to .s
                module_name = '.'.join(path.rsplit('.', 1)[0].split(os.sep))
                __import__(module_name)


def get_class(service):
    """
    Given a service name, return the Service class which should handle
    that service according to the configuration. If no Service class
    is specified, check for and return a configured default instead.
    """
    try:
        name = conf.SERVICE_MAP[service]
    except KeyError:
        pass
    try:
        name = conf.SERVICE_MAP['DEFAULT']
    except KeyError:
        print('No custom class configured for service %s, and no DEFAULT '
              'class was found!' % service)
        sys.exit(1)
    module_name, klass = name.rsplit('.', 1)
    __import__(module_name)
    module = sys.modules[module_name]
    return getattr(module, klass)


def main():
    """
    Main entry point for the 'piro' command-line utility.
    """
    parser = ArgumentParser(description='Intelligently control services.')
    parser.add_argument('action',
                        help='Name of the action you wish to perform on the '
                        'given service.')
    parser.add_argument('service',
                        help='Name of the service you wish to control.')
    parser.add_argument('-c', '--control-name', default=None,
                        help='Name used by the underlying service control '
                        'mechanism to identify the given service.')
    args, svc_args = parser.parse_known_args()
    if args.control_name is None:
        args.control_name = args.service
    for dir in conf.PLUGIN_DIRS:
        load_plugins(dir)
    klass = get_class(args.service)
    service = klass(args.service,
                    control_name=args.control_name,
                    svc_args=svc_args)

    # Obviously I need to do something better than just printing out
    # the status dict here, but that polish can happen later.
    print json.dumps(getattr(service, args.action)(),
                     sort_keys=True,
                     indent=4)
