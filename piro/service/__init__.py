"""
Piro provides a basic Service API to define the most-common service
control actions one might wish to perform. The base set of actions
are:

  status
    Check whether the service is enabled/disabled and/or running/stopped.

  enable
    Enable the service. The semantics of what this means is generally
    left up to the sub-classes. The built-in :py:class:`Monit class
    <piro.service.monit.Monit>` uses enable to mean 'enable monitoring
    of the service'.

  disable
    Disable the service. The semantics of what this means is generally
    left up to the sub-classes. The built-in :py:class:`Monit class
    <piro.service.monit.Monit>` uses disable to mean 'disable
    monitoring of the service'.

  reload
    Reload the service. This is intended to be used for reloading the
    configuration of a service without restarting it.

  start
    Start the service.

  stop
    Stop the service.

  restart
    Restart the service.

Piro provides an abstract base class :py:class:`Service
<piro.service.Service>` which defines this basic Service API as well
as providing fucntionality for manipulating hooks - functions which
run before/after the action that must return True for the action to
succeed.

Sub-classes may provide hooks for their own actions by adding
action method names to the class variable ``HOOK_METHOD_NAMES``::

  class MyService(Service):
    HOOK_METHOD_NAMES = Service.HOOK_METHOD_NAMES + ['my_hooked_action']


.. _Monit class: py:class:: piro.service.monit.Monit
"""
from argparse import ArgumentParser


class HookError(StandardError):
    """
    Exception raised when a hook fails.
    """
    pass


class Service(object):
    """
    Base class defining the service control API and providing
    the hook functionality to sub-classes.
    """

    STAGES = ['pre', 'post']
    HOOK_METHOD_NAMES = ['enable', 'disable', 'reload', 'start', 'stop']
    """
    List of methods which allow for the attachment of pre/post action
    hooks.

    Sub-classes may provide hooks for their own actions by adding action
    method names to this class variable
    """

# Services class functionality for use by subclasses.

    @classmethod
    def _init_parser(cls):
        """
        Initializes the service-specific parser with common arguments
        and returns it.
        """
        parser = ArgumentParser()
        return parser

    def _run_hooks(self, name):
        """
        Run the specified hooks. If any hook returns False, raise a
        HookError.
        """
        for hook in object.__getattribute__(self, '%s_hooks' % name):
            if not hook():
                raise HookError('%s hooks failed!' % name)

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
        Initialize a Service object.

        ``name``
          Human-friendly name for the service.

        ``control_name``
          Name that the underlying service control system uses to
          identify the service.
        """
        for stage in self.STAGES:
            for method in self.HOOK_METHOD_NAMES:
                self.__setattr__('%s_%s_hooks' % (stage, method), [])

        self.name = name
        self.control_name = control_name
        self.parser = self._init_parser()

    def add_hook(self, name, fun):
        """
        Adds a hook to the given service method.

        ``name``
          The name of the hook in the form
          ``(pre|post)-<ACTION>``. For example, to add a hook to run
          before the ``start`` action, pass 'pre-start' (or 'pre_start')
          as ``name``.

        ``fun``
          A callable which returns True if the hook succeeds and
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
        returned as a dict. The status dict **MUST** contain the key
        ``state`` whose value **MUST** be a tuple of the form
        ``(enable_state, run_state)`` where ``enable_state`` is a
        boolean representing whether the service is enabled or not,
        and ``run_state`` is a boolean representing whether the
        service is running or not.  The value ``None`` for either
        component is to indicate that it is either unknown or does not
        make sense for the service in question. The status dict may
        contain other service-specific key/value pairs as well.
        """
        raise NotImplementedError('"status" method not available for '
                                  'service %s' % self.name)

    def enable(self):
        """
        If the service is already enabled, this is a no-op. If the
        service is not enabled, run any ``pre-enable`` hooks. If these
        hooks ran sucessfully, attempt to enable the service. The
        semantics of what enabling a service means is left up to the
        individual service implementation. After enabling the service,
        run any ``post-enable hooks``. Finally, return the result of
        calling :py:func:`status() <piro.service.Service.status>` on
        the service.
        """
        raise NotImplementedError('"enable" method not available for '
                                  'service %s' % self.name)

    def disable(self):
        """
        If the service is already disabled, this is a no-op. If the
        service is enabled, run any ``pre-disable`` hooks. If these
        hooks ran sucessfully, attempt to disable the service. The
        semantics of what disabling a service means is left up to the
        individual service implementation. After disabling the
        service, run any ``post-disable hooks``. Finally, return the
        result of calling :py:func:`status()
        <piro.service.Service.status>` on the service.
        """
        raise NotImplementedError('"disable" method not available for '
                                  'service %s' % self.name)

    def reload(self):
        """
        First, run any ``pre-reload`` hooks. Then, attempt to reload
        the configuration of the service. Next, run any
        ``post-reload`` hooks. Finally, return the result of calling
        :py:func:`status() <piro.service.Service.status>` on the
        service.
        """
        raise NotImplementedError('"reload" method not available for '
                                  'service %s' % self.name)

    def start(self):
        """
        If the service is already running, this is a no-op. If the
        service is not running, run any pre-start hooks. If these
        hooks ran sucessfully, attempt to start the service. Next, run
        any post-start hooks. Finally, return the result of calling
        :py:func:`status()
        <piro.service.Service.status>` on the service.
        """
        raise NotImplementedError('"start" method not available for '
                                  'service %s' % self.name)

    def stop(self):
        """
        If the service is already stopped, this is a no-op. If the
        service is running, run any pre-stop hooks. If these hooks ran
        sucessfully, attempt to stop the service. Next, run any
        post-stop hooks. Finally, return the result of calling
        :py:func:`status()
        <piro.service.Service.status>` on the service.
        """
        raise NotImplementedError('"stop" method not available for '
                                  'service %s' % self.name)

    def restart(self):
        """
        First, call :py:func:`stop() <piro.service.Service.stop>` on
        the service, then call :py:func:`start()
        <piro.service.Service.start>` on the service. Finally return
        the result of calling :py:func:`status()
        <piro.service.Service.status>` on the service. The restart
        action does not have any hooks of its own - add hooks to
        :py:func:`start() <piro.service.Service.start>` and/or
        :py:func:`stop() <piro.service.Service.stop>` instead.
        """
        try:
            self.stop()
        except NotImplementedError:
            raise NotImplementedError('"restart" method not available for '
                                      'service %s' % self.name)
        self.start()
        return self.status()
