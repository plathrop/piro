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


def parse_monit_status(element):
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


class Monit(Service):
    """
    Controls a service via the Monit web API.
    """

    auth = url.HTTPBasicAuthHandler()
    opener = None
    uri = ''

    def __init__(self, name, host,
                 control_name=None,
                 username='',
                 password='',
                 port=2812,
                 realm='monit'):
        """
        Initialize a service controlled by Monit.
        """
        Service.__init__(self, name, control_name=control_name)
        self.uri = 'http://%s:%s' % (host, port)
        # Configure HTTP Basic Authentication for the Monit web API.
        self.auth.add_password(realm=realm,
                               uri=self.uri,
                               user=username,
                               passwd=password)
        self.opener = url.build_opener(self.auth)
        url.install_opener(self.opener)

    def _api_call(self, action, check_fn, wait=False):
        """
        Given an action, perform the actual Monit API call for that
        action, optionally waiting for the state change to occur. This
        call is a no-op if the current state already matches the
        desired state. The state is checked via the check_fn
        parameter, which should be a function taking a single argument
        representing a state tuple, and returning a boolean True if
        the state matches the desired state.
        """
        status = self.status()
        if check_fn(status['state']):
            return status
        with closing(url.urlopen('%s/%s' % (self.uri, self.control_name),
                                 urlencode({'action': action}),
                                 timeout=1)) as res:
            # We don't actually want to do anything with the result,
            # but we don't want to leave it just hanging around, so
            # read and discard.
            res.read()
        if wait:
            while not check_fn(status['state']):
                sleep(.1)
                status = self.status()
        return status

    def status(self):
        """
        Returns the status of the service as a dict.
        """
        with closing(url.urlopen('%s/_status?format=xml' % self.uri,
                                 timeout=1)) as res:
            data = res.read()
        if not data:
            raise MonitAPIError('No content from server')
        tree = ElementTree.fromstring(data)
        # Grab all the 'service' elements. We're interested in
        # 'service' elements with a 'type' attribute == 3 because
        # these are the actual services. Monit represents the host
        # itself, (and maybe other things), as 'service' elements with
        # a different 'type' (for example type == 5 is the host itself
        # and contains information about resource usage.
        services = [element for element in tree.getiterator('service')
                    if int(element.get('type')) == 3
                    and s.find('name').text == self.control_name]
        if len(services) < 1:
            raise MonitAPIError('Service %s not found' % self.control_name)
        elif len(services) > 1:
            raise MonitAPIError('Multiple service entries found for %s' %
                                self.control_name)
        status = {}
        service = services[0]
        status['state'] = parse_monit_status(service)
        pid = service.find('pid')
        if pid:
            status['pid'] = int(pid.text)
            uptime = service.find('uptime')
        if uptime:
            status['uptime'] = int(uptime.text)
        return status

    def enable(self, wait=False):
        """
        If the service is already enabled, this is a no-op. If the
        service is not enabled, run any pre-enable hooks. If these
        hooks ran sucessfully, attempt to enable the service. After
        enabling the service, run any post-enable hooks. Finally,
        return the result of calling status() on the service. If the
        kwarg 'wait' is True, block until the state change is
        confirmed in the API.
        """
        return self._api_call('monitor',
                              lambda state: state[0] is True,
                              wait=wait)

    def disable(self, wait=False):
        """
        If the service is already disabled, this is a no-op. If the
        service is enabled, run any pre-disable hooks. If these hooks
        ran sucessfully, attempt to disable the service. After
        disabling the service, run any post-disable hooks. Finally,
        return the result of calling status() on the service. If the
        kwarg 'wait' is True, block until the state change is
        confirmed in the API.
        """
        return self._api_call('unmonitor',
                              lambda state: state[0] is False,
                              wait=wait)

    def reload(self):
        """
        Reload is not supported by Monit.
        """
        raise MonitAPIError('Reload is not supported by Monit.')

    def start(self, wait=False):
        """
        If the service is already running, this is a no-op. If the
        service is not running, run any pre-start hooks. If these
        hooks ran sucessfully, attempt to start the service. Next, run
        any post-start hooks. Finally, return the result of calling
        status() on the service. If the kwarg 'wait' is True, block
        until the state change is confirmed in the API.
        """
        return self._api_call('start',
                              lambda state: state[1] is True,
                              wait=wait)

    def stop(self, wait=False):
        """
        If the service is already stopped, this is a no-op. If the
        service is running, run any pre-stop hooks. If these hooks ran
        sucessfully, attempt to stop the service. Next, run any
        post-stop hooks. Finally, return the result of calling
        status() on the service. If the kwarg 'wait' is True, block
        until the state change is confirmed in the API.
        """
        return self._api_call('stop',
                              lambda state: state[1] is False,
                              wait=wait)
