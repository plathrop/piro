========================
Writing Plugins for Piro
========================

Piro plugins make use of Python `namespace packages`_. There are two
namespace packages available for your use in extending Piro:
``piro.util`` and ``piro.plugins``. ``piro.util`` is for utility code
that your plugins will make use of. ``piro.plugins`` is for
:py:class:`Service class <piro.service.Service>` subclasses which
allow you to control services that Piro cannot control natively; or to
add pre and post-action hooks.

To create a new Piro plugin, you must set up a new Python project
directory for it. The project must have the following files and
directories, at minimum::

  PROJECT_BASE/
  PROJECT_BASE/setup.py
  PROJECT_BASE/piro
  PROJECT_BASE/piro/__init__.py
  PROJECT_BASE/piro/plugins
  PROJECT_BASE/piro/plugins/__init__.py

If you are also adding functionality to ``piro.util`` you must also
have these files and directories::

  PROJECT_BASE/piro/util
  PROJECT_BASE/piro/util/__init__.py

In the ``setup.py`` for your project, add the following line to the
``setup`` function::

      namespace_packages=['piro', 'piro.plugins', 'piro.util'],

For example, your ``setup.py`` might look like this::

  from setuptools import setup, find_packages

  setup(name='mycompany-piro-plugins',
        version="0.0.1",
        description='MyCompany plugins for piro.',
        author='John Doe',
        author_email='john@mydomain.com',
        url='https://github.com/johndoe/mycompany-piro-plugins',
        namespace_packages=['piro', 'piro.plugins', 'piro.util'],
        packages=find_packages(),
        install_requires=['argparse', 'piro']
  )

Each of the required ``__init__.py`` files must contain only this
line::

  __import__('pkg_resources').declare_namespace(__name__)

You may also include a docstring, but you **MUST NOT** include any
other code. See the `setuptools documentation`_ for details.

Now you may add your code in
``PROJECT_BASE/piro/plugins/myplugin.py``. Utility code may be added
to ``PROJECT_BASE/piro/util/myutil.py``. Most likely, you will want
your plugin to inherit from :py:class:`Service <piro.service.Service>`
and provide implementations of the Service API methods. You may also
want to define action hooks and add them to your services.

Using a custom plugin
=====================

To make use of your new plugin for a service called ``myservice`` you
will need to install the python package of your project using
setuptools (``python setup.py install``), and add a mapping to your
``SERVICE_MAP`` in your piro configuration::

  SERVICE_MAP['myservice'] = 'piro.plugins.myplugin.MyClass'


.. _namespace packages: http://www.python.org/dev/peps/pep-0382/
.. _setuptools documentation: http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
