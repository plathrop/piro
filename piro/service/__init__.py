"""
Base Service class and related helpers.
"""
from argparse import ArgumentParser

class HookError(StandardError):
    """
    Error raised by problems with pre/post hooks.
    """
    pass


class Service(object):
    """
    Base class defining the service control API and providing
    methods for manipulating pre/post hooks.
    """

    STAGES = ['pre', 'post']
    HOOK_METHOD_NAMES = ['enable', 'disable', 'reload', 'start', 'stop']

# Services class functionality for use by subclasses.

    def _init_parser(self):
        """
        Initializes the service-specific parser with common arguments
        and returns it.
        """
        parser = ArgumentParser()
        parser.add_argument('-u', '--username', default='',
                            help='Username to use when authenticating to the '
                          'underlying service control mechanism.')
        parser.add_argument('--password', default='',
                            help='Password to use when authenticating to the '
                            'underlying service control mechanism.')
        return parser

    def _run_hooks(self, name):
        """
        Run the specified hooks. If any hook returns False, raise a
        HookError.
        """
        for hook in object.__getattribute__(self, '%s_hooks' % name):
            if not hook():
                raise HookError('%s_hooks failed!' % name)

    def __getattribute__(self, name):
        """
        Overrides attribute lookup for services so that if the
        attribute access is for one of the hooked methods, the
        returned function is one that calls the pre/post hooks.
        """
        # We only want to muck with method lookup for our API methods.
        if name in object.__getattribute__(self, 'HOOK_METHOD_NAMES'):
            def fun():
                """
                Wraps a method call with pre/post hooks.
                """
                # This function will be returned instead of the API
                # method that was originally called.
                self._run_hooks('pre_%s' % name)
                # Store the result of calling the originally-requested
                # method so we can return it as the return value of
                # this function that wraps it.
                result = object.__getattribute__(self, name)()
                self._run_hooks('post_%s' % name)
                return result
            return fun
        else:
            # Just do normal attribute lookup on attributes that are
            # not part of the API.
            return object.__getattribute__(self, name)

    def __init__(self, name, control_name=None):
        """
        Initialize a Service object. Services have a human-friendly
        'name' and a 'control_name' that the underlying service
        control system uses for the Service.
        """
        for stage in self.STAGES:
            for method in self.HOOK_METHOD_NAMES:
                self.__setattr__(self, '%s_%s_hooks' % (stage, method), [])

        self.name = name
        self.control_name = control_name
        self.parser = self._init_parser()

    def add_hook(self, name, fun):
        """
        Adds a pre/post hook to the given service method. pre/post
        hooks are functions which return True if the hook succeeds and
        False otherwise.
        """
        name = name.replace('-', '_')
        stage, sep, action = name.partition('_')
        if stage not in self.STAGES or action not in self.HOOK_METHOD_NAMES:
            raise HookError('No such hook: %s' % name)
        self.__getattribute__('%s_hooks' % name).append(fun)

# Methods that define the Service API.

    def status(self):
        """
        Return the status of the service. Service status should be
        returned as a dict. The status dict MUST contain the key
        'state' whose value MUST be a tuple of the form (enable_state,
        run_state) where enable_state is a boolean representing
        whether the service is enabled or not, and run_state is a
        boolean representing whether the service is running or not.
        The value None for either component is to indicate that it is
        either unknown or does not make sense for the service in
        question. The status dict may contain other service-specific
        key/value pairs as well.
        """
        raise NotImplementedError

    def enable(self):
        """
        If the service is already enabled, this is a no-op. If the
        service is not enabled, run any pre-enable hooks. If these
        hooks ran sucessfully, attempt to enable the service. The
        semantics of what enabling a service means is left up to the
        individual service implementation. After enabling the service,
        run any post-enable hooks. Finally, return the result of
        calling status() on the service.
        """
        raise NotImplementedError

    def disable(self):
        """
        If the service is already disabled, this is a no-op. If the
        service is enabled, run any pre-disable hooks. If these hooks
        ran sucessfully, attempt to disable the service. The semantics
        of what disabling a service means is left up to the individual
        service implementation. After disabling the service, run any
        post-disable hooks. Finally, return the result of calling
        status() on the service.
        """
        raise NotImplementedError

    def reload(self):
        """
        First, run any pre-reload hooks. Then, attempt to reload the
        configuration of the service. Next, run any post-reload
        hooks. Finally, return the result of calling status() on the
        service.
        """
        raise NotImplementedError

    def start(self):
        """
        If the service is already running, this is a no-op. If the
        service is not running, run any pre-start hooks. If these
        hooks ran sucessfully, attempt to start the service. Next, run
        any post-start hooks. Finally, return the result of calling
        status() on the service.
        """
        raise NotImplementedError

    def stop(self):
        """
        If the service is already stopped, this is a no-op. If the
        service is running, run any pre-stop hooks. If these hooks ran
        sucessfully, attempt to stop the service. Next, run any
        post-stop hooks. Finally, return the result of calling
        status() on the service.
        """
        raise NotImplementedError

    def restart(self):
        """
        First, call stop() on the service, then call start() on the
        service. Finally return the result of calling status() on the
        service. The restart action does not have any hooks of its own
        - add pre/post start/stop hooks instead.
        """
        self.stop()
        self.start()
        return self.status()
