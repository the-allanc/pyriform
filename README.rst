.. |name| replace:: pyriform
.. |summary| replace:: Connect the requests library to your WSGI app without using sockets.

|name|
======

|summary|

.. _repository: https://github.com/the-allanc/pyriform/
.. _documentation: https://pyriform.readthedocs.io/en/stable/
.. _pypi: https://pypi.python.org/pypi/pyriform
.. _coveralls: https://coveralls.io/github/the-allanc/pyriform
.. _license: https://github.com/the-allanc/pyriform/master/LICENSE.txt
.. _travis: https://travis-ci.org/the-allanc/pyriform
.. _codeclimate: https://codeclimate.com/github/the-allanc/pyriform

.. |Build Status| image:: https://img.shields.io/travis/the-allanc/pyriform.svg
    :target: travis_
    :alt: Build Status
.. |Coverage| image:: https://img.shields.io/coveralls/the-allanc/pyriform.svg
    :target: coveralls_
    :alt: Coverage
.. |Docs| image:: https://readthedocs.org/projects/pyriform/badge/?version=stable&style=flat
    :target: documentation_
    :alt: Docs
.. |Release Version| image:: https://img.shields.io/pypi/pyversions/pyriform.svg
    :target: pypi_
    :alt: Release Version
.. |Python Version| image:: https://img.shields.io/pypi/v/pyriform.svg
    :target: pypi_
    :alt: Python Version
.. |License| image:: https://img.shields.io/pypi/l/pyriform.svg
    :target: license_
    :alt: License
.. |Code Climate| image:: https://img.shields.io/codeclimate/issues/github/the-allanc/pyriform.svg
    :target: codeclimate_
    :alt: Code Climate

.. _requests: http://python-requests.org
.. _webtest: https://docs.pylonsproject.org/projects/webtest/

Linking the Requests_ and WebTest_ libraries together, ``pyriform`` allows you to use the ``requests`` library to interact your WSGI app without needing to have it running on the network; it bonds these two web components together.

It's useful for testing purposes, handles all standard HTTP methods (as well as custom ones), supports request timeouts. and is both Python 2 and 3 compatible.

Example Usage
-------------

.. _cherrypy: http://www.cherrypy.org

Here's an example with a small WSGI app (in this case, using CherryPy_), and how we can use Pyriform to connect to it::

    >>> # Create the WSGI app.
    >>>
    >>> import cherrypy
    >>>
    >>> class SayHello(object):
    ...
    ...     @cherrypy.expose
    ...     def default(self, word):
    ...         return "Hello %s from %s!" % (word, cherrypy.request.headers['X-Location'])
    ...
    >>> cherrypy.config.update({'environment': 'embedded'})  # Suppress logging output.
    >>> app = cherrypy.tree.mount(SayHello(), '/')
    >>>
    >>> # Now use Pyriform to map requests from a particular URL to this app.
    >>>
    >>> import pyriform
    >>> import requests
    >>> adapter = pyriform.WSGIAdapter(app)
    >>> session = requests.Session()
    >>> session.mount('http://helloapp/', adapter)
    >>> resp = session.get('http://helloapp/World', headers={'X-Location': 'London'})
    >>> print (resp.text)
    Hello World from London!


|Docs| |Release Version| |Python Version| |License| |Build Status| |Coverage| |Code Climate|

.. all-content-above-will-be-included-in-sphinx-docs

You can browse the source code and file bug reports at the project repository_. Full documentation can be found `here`__.

__ documentation_
