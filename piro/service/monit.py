"""
The monit module provides a buit-in service control class for
controlling services running under Monit_. This class assumes your
services are exposed remotely by the `Monit HTTP service`_.

.. _Monit: http://mmonit.com/monit/
.. _Monit HTTP service: http://mmonit.com/monit/documentation/monit.html#monit_httpd
"""

from contextlib import closing
from time import sleep
from urllib import urlencode
import urllib2 as url
from xml.etree import ElementTree

from piro.service import Service


class MonitAPIError(StandardError):
    """
    Error raised when encountering problems communicating with the
    Monit web API.
    """
    pass


class Monit(Service):
    """
    Controls a service via the Monit web API.
    """

    @classmethod
    def _init_parser(cls):
        parser = Service._init_parser()
        parser.add_argument('hosts', nargs='+',
                            help='Hosts on which you wish to control the '
                            'monit service.')
        parser.add_argument('-u', '--username', default='',
                            help='Username to use when authenticating to the '
                            'underlying service control mechanism.')
        parser.add_argument('--password', default='',
                            help='Password to use when authenticating to the '
                            'underlying service control mechanism.')
        parser.add_argument('--port', type=int, default=2812,
                            help='Port where the Monit API is listening on '
                            'the given hosts')
        parser.add_argument('--realm', default='monit',
                            help='Authentication realm to use when '
                            'authenticating to the Monit API.')
        return parser

    def __init__(self, name, control_name=None, svc_args=[]):
        """
        Initialize a service controlled by Monit.

        ``name``
          Human-friendly name for the service.
        ``control_name``
          Name that the underlying service control system uses to
          identify the service.
        ``svc_args``
          Command-line arguments specific to this service, in the
          format expected by argparse_. Monit services require that
          ``svc_args`` contains a list of hosts on which you wish to
          control services. Monit services also use the following
          options, if provided:

          ``--username``
            Username to use when authenticating to the Monit HTTP API.
          ``--password``
            Password to use when authenticating to the Monit HTTP API.
          ``--port``
            Port on which to connect to the Monit HTTP API.
          ``--realm``
            Authentication realm to use when authenticating to the Monit
            HTTP API.

        .. _argparse: http://docs.python.org/library/argparse.html
        """
        Service.__init__(self, name, control_name=control_name)
        self.auth = url.HTTPBasicAuthHandler()
        self.opener = None
        self.uri = {}
        parser = self._init_parser()
        args = parser.parse_known_args(svc_args)[0]
        for host in args.hosts:
            self.uri[host] = 'http://%s:%s' % (host, args.port)
            # Configure HTTP Basic Authentication for the Monit web API.
            self.auth.add_password(realm=args.realm,
                                   uri=self.uri[host],
                                   user=args.username,
                                   passwd=args.password)
        self.opener = url.build_opener(self.auth)
        url.install_opener(self.opener)

    def _api_call(self, host, action, check_fn, wait=False):
        """
        Given an action, perform the actual Monit API call for that
        action, optionally waiting for the state change to occur. This
        call is a no-op if the current state already matches the
        desired state. The state is checked via the check_fn
        parameter, which should be a function taking a single argument
        representing a state tuple, and returning a boolean True if
        the state matches the desired state.
        """
        status = self._status(host)
        if check_fn(status['state']):
            return status
        with closing(url.urlopen('%s/%s' % (self.uri[host], self.control_name),
                                 urlencode({'action': action}),
                                 timeout=1)) as res:
            # We don't actually want to do anything with the result,
            # but we don't want to leave it just hanging around, so
            # read and discard.
            res.read()
        if wait:
            while not check_fn(status['state']):
                sleep(.1)
                status = self._status(host)
        return status

    def _parse_monit_status(element):
        """
        Given an XML element representing a service, extract the
        status information and return a tuple representing that
        status. The tuple will be of the form (enable_state,
        run_state) where enable_state is a boolean representing
        whether the service is enabled or not, and run_state is a
        boolean representing whether the service is running or
        not. The value None for either component is to indicate that
        it is either unknown or does not make sense for the service.
        """
        # The 'monitor' element tells us whether Monit is actively
        # controlling the service or not. A 0 means Monit is not
        # controlling the service. Sadly, when the service is stopped
        # by Monit, this element says Monit is *not* controlling the
        # service, even though it is. So, potentially, the service
        # could be running, but Monit has been told not to control
        # it. However, usually that is not the case and we're taking a
        # shortcut here by assuming it isn't.
        monitor = int(element.find('monitor').text)
        if monitor == 0:
            return (False, False)
        # The 'status' element tells us whether the service is running
        # or not. Any value other than 0 means the service is not
        # running. More specific info is available via the web API,
        # but lacking any documentation on what it means, that
        # information is useless and we don't bother looking at it.
        status = int(element.find('status').text)
        if status == 0:
            return (True, True)
        else:
            return (True, False)

    def _status(self, host):
        """
        Returns the status of the service as a dict.
        """
        with closing(url.urlopen('%s/_status?format=xml' % self.uri[host],
                                 timeout=1)) as res:
            data = res.read()
        if not data:
            raise MonitAPIError('No content from server')
        tree = ElementTree.fromstring(data)
        # Grab the relevant 'service' element. We're interested in
        # 'service' elements with a 'type' attribute == 3 because
        # these are the actual services. Monit represents the host
        # itself, (and maybe other things), as 'service' elements with
        # a different 'type' (for example type == 5 is the host itself
        # and contains information about resource usage.
        services = [element for element in tree.getiterator('service')
                    if int(element.get('type')) == 3
                    and element.find('name').text == self.control_name]
        if len(services) < 1:
            raise MonitAPIError('Service %s not found' % self.control_name)
        elif len(services) > 1:
            raise MonitAPIError('Multiple service entries found for %s' %
                                self.control_name)
        status = {}
        service = services[0]
        status['state'] = self._parse_monit_status(service)
        pid = service.find('pid')
        if pid is not None:
            status['pid'] = int(pid.text)
        uptime = service.find('uptime')
        if uptime is not None:
            status['uptime'] = int(uptime.text)
        return status

    def status(self):
        """
        Returns the status of the service on each host as a dict whose
        keys are the host names and values are the status dictionary
        for the service on that host.
        """
        status = {}
        for host in self.uri.keys():
            status[host] = self._status(host)
        return status

    def enable(self, wait=False):
        """
        If monitoring of the service is already enabled, this is a
        no-op. If monitoring is not enabled, run any ``pre-enable``
        hooks. If these hooks ran sucessfully, attempt to enable
        monitoring via a Monit HTTP API call. After enabling
        monitoring, run any ``post-enable`` hooks. Finally, return the
        result of calling calling :py:func:`status()
        <piro.service.monit.Monit.status>` on the service.

        ``wait``
          If ``True``, block until the state change is confirmed in
          the API.
        """
        status = {}
        for host in self.uri.keys():
            status[host] = self._api_call(host, 'monitor',
                                          lambda state: state[0] is True,
                                          wait=wait)
        return status

    def disable(self, wait=False):
        """
        If monitoring of the service is already disabled, this is a
        no-op. If monitoring is not disabled, run any ``pre-disable``
        hooks. If these hooks ran sucessfully, attempt to disable
        monitoring via a Monit HTTP API call. After disabling
        monitoring, run any ``post-disable`` hooks. Finally, return
        the result of calling calling :py:func:`status()
        <piro.service.monit.Monit.status>` on the service.

        ``wait``
          If ``True``, block until the state change is confirmed in
          the API.
        """
        status = {}
        for host in self.uri.keys():
            status[host] = self._api_call(host, 'unmonitor',
                                          lambda state: state[0] is False,
                                          wait=wait)
        return status

    def reload(self):
        """
        Reload is not supported by Monit.
        """
        raise MonitAPIError('Reload is not supported by Monit.')

    def start(self, wait=False):
        """
        If the service is already running, this is a no-op. If the
        service is not running, run any ``pre-start hooks``. If these
        hooks ran sucessfully, attempt to start the service via a
        Monit HTTP API call. Next, run any ``post-start``
        hooks. Finally, return the result of calling
        :py:func:`status() <piro.service.monit.Monit.status>` on the
        service.

        ``wait``
          If ``True``, block until the state change is confirmed in
          the API.
        """
        status = {}
        for host in self.uri.keys():
            status[host] = self._api_call(host, 'start',
                                          lambda state: state[1] is True,
                                          wait=wait)
        return status

    def stop(self, wait=False):
        """
        If the service is already stopped, this is a no-op. If the
        service is running, run any ``pre-stop hooks``. If these hooks
        ran sucessfully, attempt to stop the service via a Monit HTTP
        API call. Next, run any ``post-stop`` hooks. Finally, return
        the result of calling :py:func:`status()
        <piro.service.monit.Monit.status>` on the service.

        ``wait``
          If ``True``, block until the state change is confirmed in
          the API.
        """
        status = {}
        for host in self.uri.keys():
            status[host] = self._api_call(host, 'stop',
                                          lambda state: state[1] is False,
                                          wait=wait)
        return status
