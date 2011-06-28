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

    def status(self, *args, **kwargs):
        """
        Returns the status of the service as a dict.
        """
        uri = '%s/_status?format=xml' % self.uri
        res = url.urlopen(uri, timeout=1)
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
        else:
            stat = {}
            service = services[0]
            stat['state'] = parse_monit_status(service)
            pid = service.find('pid')
            if pid:
                stat['pid'] = int(pid.text)
            uptime = service.find('uptime')
            if uptime:
                stat['uptime'] = int(uptime.text)
            return stat

    def enable(self, wait=False, *args, **kwargs):
        """
        If the service is already enabled, this is a no-op. If the
        service is not enabled, run any pre-enable hooks. If these
        hooks ran sucessfully, attempt to enable the service. After
        enabling the service, run any post-enable hooks. Finally,
        return the result of calling status() on the service. If the
        kwarg 'wait' is True, block until the state change is
        confirmed in the API.
        """
        state = self.status()['state']
        if state[0]:
            return self.status()
        uri = '%s/%s' % (self.uri, self.control_name)
        url.urlopen(uri, urlencode({'action': 'monitor'}), timeout=1)
        if not wait:
            return self.status()
        else:
            sleep(.1)
            state = self.status()['state']
            while not state[0]:
                sleep(.1)
                state = self.status()['state']
            return self.status()

    def disable(self, wait=False, *args, **kwargs):
        """
        If the service is already disabled, this is a no-op. If the
        service is enabled, run any pre-disable hooks. If these hooks
        ran sucessfully, attempt to disable the service. After
        disabling the service, run any post-disable hooks. Finally,
        return the result of calling status() on the service. If the
        kwarg 'wait' is True, block until the state change is
        confirmed in the API.
        """
        state = self.status()['state']
        if not state[0]:
            return self.status()
        uri = '%s/%s' % (self.uri, self.control_name)
        url.urlopen(uri, urlencode({'action': 'unmonitor'}), timeout=1)
        if not wait:
            return self.status()
        else:
            sleep(.1)
            state = self.status()['state']
            while state[0]:
                sleep(.1)
                state = self.status()['state']
            return self.status()

    def reload(self, *args, **kwargs):
        """
        Reload is not supported by Monit.
        """
        raise MonitAPIError('Reload is not supported by Monit.')

    def start(self, wait=False, *args, **kwargs):
        """
        If the service is already running, this is a no-op. If the
        service is not running, run any pre-start hooks. If these
        hooks ran sucessfully, attempt to start the service. Next, run
        any post-start hooks. Finally, return the result of calling
        status() on the service. If the kwarg 'wait' is True, block
        until the state change is confirmed in the API.
        """
        state = self.status()['state']
        if state[1]:
            return self.status()
        uri = '%s/%s' % (self.uri, self.control_name)
        url.urlopen(uri, urlencode({'action': 'start'}), timeout=1)
        if not wait:
            return self.status()
        else:
            sleep(.1)
            state = self.status()['state']
            while not state[1]:
                sleep(.1)
                state = self.status()['state']
            return self.status()

    def stop(self, wait=False, *args, **kwargs):
        """
        If the service is already stopped, this is a no-op. If the
        service is running, run any pre-stop hooks. If these hooks ran
        sucessfully, attempt to stop the service. Next, run any
        post-stop hooks. Finally, return the result of calling
        status() on the service. If the kwarg 'wait' is True, block
        until the state change is confirmed in the API.
        """
        state = self.status()['state']
        if not state[1]:
            return self.status()
        uri = '%s/%s' % (self.uri, self.control_name)
        url.urlopen(uri, urlencode({'action': 'stop'}), timeout=1)
        if not wait:
            return self.status()
        else:
            sleep(.1)
            state = self.status()['state']
            while state[1]:
                sleep(.1)
                state = self.status()['state']
            return self.status()
