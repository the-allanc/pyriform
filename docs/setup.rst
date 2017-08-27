Installing
----------

.. _repo: |url|

You can install |projname| using pip:

.. parsed-literal::
   
   pip install |projname|

Or cloning the |projname| repository from the repo_, and in an `activated virtualenv <http://docs.python-guide.org/en/latest/>`_, run this command::

    pip install .


Developing
----------

If you want to work on the project, clone the repository from the repo_, creating a `virtualenv <https://virtualenv.pypa.io/>`_, and running::

    pip install -r requirements-dev.txt

Testing
~~~~~~~

You can just `tox <https://tox.readthedocs.io/en/latest/>`_ to run tests::

    tox
    
Documentation
~~~~~~~~~~~~~

You can generate documentation using `Sphinx <http://www.sphinx-doc.org>`_::

    sphinx-build docs/ built-docs/

