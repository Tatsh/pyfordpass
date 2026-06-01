Typing
======

Response and configuration shapes used by the FordPass library, split by category. Internal
pyfordpass code imports from the specific submodule (for example
``from fordpass.typing.service import ServiceActionDetail``); the package ``__init__`` re-exports
each symbol so external consumers can use the flat ``from fordpass.typing import
ServiceActionDetail`` form without knowing the internal categorisation.

Submodules
----------

.. toctree::
   :maxdepth: 1

   alerts
   api_config
   auth
   commands
   common
   config
   dealer
   departure
   drivers
   electrification
   guard
   lighting
   messages
   profile
   rcc
   release
   roadside
   schedule
   service
   telemetry
   vehicle
