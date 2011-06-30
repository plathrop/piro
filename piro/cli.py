"""
Command line interface for piro.
"""
from argparse import ArgumentParser
import sys


# This should be set up in a config file. I don't want to fuck with
# writing the config handling code yet, so I'm setting it here for
# now.
SERVICE_MAP = {'DEFAULT': 'piro.service.monit.Monit'}


def get_class(service):
    """
    Given a service name, return the Service class which should handle
    that service according to the configuration. If no Service class
    is specified, check for and return a configured default instead.
    """
    try:
        name = SERVICE_MAP[service]
    except KeyError:
        pass
    try:
        name = SERVICE_MAP['DEFAULT']
    except KeyError:
        print('No custom class configured for service %s, and no DEFAULT '
              'class was found!' % service)
        sys.exit(1)
    mod_name, klass = name.rsplit('.', 1)
    module = __import__(mod_name, globals(), locals(), [klass], 0)
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
    klass = get_class(args.service)
    service = klass(args.service, control_name=args.control_name,
                    svc_args=svc_args)
    # Obviously I need to do something better than just printing out
    # the status dict here, but that polish can happen later.
    print getattr(service, args.action)()
