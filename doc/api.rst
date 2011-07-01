=================
API Documentation
=================

Service API
-----------
.. automodule:: piro.service

Service abstract class
~~~~~~~~~~~~~~~~~~~~~~~~
.. autoclass:: piro.service.Service
   :members:

   .. automethod:: piro.service.Service.__init__

Exceptions
~~~~~~~~~~
.. autoexception:: piro.service.HookError
   :show-inheritance:

Built-in service control classes
--------------------------------

Monit
~~~~~
.. automodule:: piro.service.monit
.. autoclass:: piro.service.monit.Monit
   :members:
   :show-inheritance:
   :inherited-members:

   .. automethod:: piro.service.monit.Monit.__init__

.. autoexception:: piro.service.monit.MonitAPIError
   :show-inheritance:
