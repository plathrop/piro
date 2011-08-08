============
Introduction
============

Piro is a Python library and command-line interface for intelligently
managing services running on remote hosts. Piro can support service
control on any service system that exposes a remote API (currently
only Monit_ is supported, but we will add other systems as patches are
made!). You can also create plugins for Piro to control services that
aren't supported by the base Piro library.

Piro also makes it possible to add pre/post hooks to service actions;
for example, before restarting a service you may want to call a
function verifying the syntax of its configuration file -- you can do
this by adding a pre-start hook to your service.

Command-Line Interface
----------------------

Piro's command-line interface is the ``piro`` command::

  usage: piro [-h] [-c CONTROL_NAME] action service

  Intelligently control services.

  positional arguments:
    action                Name of the action you wish to perform on the given
                          service.
    service               Name of the service you wish to control.

  optional arguments:
    -h, --help            show this help message and exit
    -c CONTROL_NAME, --control-name CONTROL_NAME
                          Name used by the underlying service control mechanism
                          to identify the given service.

Each plugin can define additional command-line options and/or
arguments. For example, the base :py:class:`Service class
<piro.service.Service>` adds ``--username`` and ``--password`` options
for authenticating to the underlying service control mechanism.

Configuration
-------------

Piro's command-line interface looks for configuration in two places:
``/etc/piro/config.py`` and ``.piro.py`` in the user's home
directory. If both files exists, settings in the user-specific file
over-ride those in ``/etc``. The configuration file is
Python. The available configuration options are:

USERNAME
  The username to use for actions/services which require one. This
  defaults to your username on the local system as returned by
  Python's ``getpass.getuser()`` function.

PASSWORD
  The password to use for actions/services which require one.

SERVICE_MAP
  A dict; keys are service names and values are the
  fully-qualified name of the class which implements control of that
  service. The special key ``DEFAULT`` is used when no
  service-specific key is defined. for example::

    SERVICE_MAP = {'DEFAULT': 'piro.service.monit.Monit',
                   'puppet': 'piro.plugins.puppet.Puppet'}

  would use the class Puppet from the module piro.plugins.puppet to
  control the ``puppet`` service, while all other services would be
  controlled by the build-in Monit class.

ALIAS_MAP
  A dict; keys are service names and values are the name used by the
  underlying service controller. For example::

    ALIAS_MAP = {'nrpe': 'nagios-nrpe-server'}

  would establish an alias 'nrpe' for the service called
  'nagios-nrpe-server' by your service controller. You could then use
  'nrep' as the service name in the command-line interface. Aliases
  are not used if ``--control-name`` is specified in your command-line
  options.

The ``USERNAME`` and ``PASSWORD`` settings can also be set via
the ``PIRO_USERNAME`` and ``PIRO_PASSWORD`` environment variables. If
set in this way, the environment variables will over-ride the values
in the configuration files. If the password is not set in the config
or the environment, and a password is required, it is up to the
individual plugin to get a password from the user.

Controlling a Monit Service
---------------------------

If you are using Monit_, and have set up the `Monit HTTP service`_ you
can use the built-in Monit class to control your services. Set the
``DEFAULT`` key in your ``SERVICE_MAP`` to
'``piro.service.monit.Monit``' and use the command-line interface. For
example, to restart a service called 'nagios-nrpe-server'::

  piro restart nagios-nrpe-server --username admin --password monit myhost.mydomain.com

The `--control-name` argument can be used if you have configured the
underlying service controller with a different name than the one you
wish to use on the command-line. For example::

  piro restart --control-name nagios-nrpe-server nrpe --username admin --password monit myhost.mydomain.com

Control names can also be set using the ``ALIAS_MAP`` configuration
setting, but ``ALIAS_MAP`` is over-ridden by ``--control-name`` if it
is provided.


.. _Monit: http://mmonit.com/monit/
.. _Monit HTTP service: http://mmonit.com/monit/documentation/monit.html#monit_httpd
