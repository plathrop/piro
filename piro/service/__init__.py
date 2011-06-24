class HookError(StandardError):
    pass


class Service(object):
    """
    Base class defining the service control API and providing
    methods for manipulating pre/post hooks.
    """

    STAGES = ['pre', 'post']
    HOOK_METHOD_NAMES = ['enable', 'disable', 'reload', 'start', 'stop']

    pre_enable_hooks = []
    post_enable_hooks = []

    pre_disable_hooks = []
    post_disable_hooks = []

    pre_reload_hooks = []
    post_reload_hooks = []

    pre_start_hooks = []
    post_start_hooks = []

    pre_stop_hooks = []
    post_stop_hooks = []

# Services class functionality for use by subclasses.

    def __getattribute__(self, name):
        """
        Overrides attribute lookup for services so that if the
        attribute access is for one of the hooked methods, the
        returned function is one that calls the pre/post hooks.
        """
        if name in self.HOOK_METHOD_NAMES:
            def fn(*args, **kwargs):
                hook_results = []
                for hook in object.__getattribute__(self,
                                                    'pre_%s_hooks' % name):

                    try:
                        hook_results.append(hook(args, kwargs))
                    except:
                        hook_results.append(False)
                if not all(hook_results):
                    raise HookError('pre_%s_hooks failed!' % name)
                result = object.__getattribute__(name)(args, kwargs)
                hook_results = []
                for hook in object.__getattribute__(self,
                                                    'post_%s_hooks' % name):
                    try:
                        hook_results.append(hook(args, kwargs))
                    except:
                        hook_results.append(False)
                if not all(hook_results):
                    raise HookError('post_%s_hooks failed!' % name)
                return result

            return fn
        else:
            return object.__getattribute__(self, name)

    def add_hook(name, fn):
        """
        Adds a pre/post hook to the given service method. pre/post
        hooks are functions which take *args and **kwargs and return a
        boolean. Any exception raised in a hook will be caught and the
        hook will be treated as though it returned False. This means
        you should do your own logging in your hooks!
        """
        stage, sep, action = name.partition('_')
        if stage not in STAGES or action not in HOOK_METHOD_NAMES:
            raise HookError('No such hook: %s' % name)
        self.__getattribute__('%s_hooks' % name).append(fn)

# Methods that define the Service API.

    def status(self, *args, **kwargs):
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

    def enable(self, *args, **kwargs):
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

    def disable(self, *args, **kwargs):
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

    def reload(self, *args, **kwargs):
        """
        First, run any pre-reload hooks. Then, attempt to reload the
        configuration of the service. Next, run any post-reload
        hooks. Finally, return the result of calling status() on the
        service.
        """
        raise NotImplementedError

    def start(self, *args, **kwargs):
        """
        If the service is already running, this is a no-op. If the
        service is not running, run any pre-start hooks. If these
        hooks ran sucessfully, attempt to start the service. Next, run
        any post-start hooks. Finally, return the result of calling
        status() on the service.
        """
        raise NotImplementedError

    def stop(self, *args, **kwargs):
        """
        If the service is already stopped, this is a no-op. If the
        service is running, run any pre-stop hooks. If these hooks ran
        sucessfully, attempt to stop the service. Next, run any
        post-stop hooks. Finally, return the result of calling
        status() on the service.
        """
        raise NotImplementedError

    def restart(self, *args, **kwargs):
        """
        First, call stop() on the service, then call start() on the
        service. Finally return the result of calling status() on the
        service. The restart action does not have any hooks of its own
        - add pre/post start/stop hooks instead.
        """
        self.stop()
        self.start()
        return self.status()