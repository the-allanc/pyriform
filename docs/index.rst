.. include:: ../README.rst
  :end-before: all-content-above-will-be-included-in-sphinx-docs

References
----------

.. toctree::
   :maxdepth: 1

   history
   setup

API
---

.. automodule:: pyriform
    :members:

Alternatives
------------

.. _requests-wsgi-adapter: https://github.com/seanbrant/requests-wsgi-adapter
.. _httpbin: https://httpbin.org/

There is another library very similar to Pyriform called requests-wsgi-adapter_; the API is mostly identical, so you can consider that library as an alternative.

However, version 0.3 of requests-wsgi-adapter_ (most recent at the time of writing) doesn't support non-standard ports, request timeouts, custom status reasons or real-time streamed response content. However, Pyriform supports all of these. [*]_

.. [*] This is based on running a number of tests in Pyriform's test suite (which mostly uses httpbin_ as the test service) using requests-wsgi-adapter_.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

