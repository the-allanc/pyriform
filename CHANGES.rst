0.5
===

* Handle multiple response headers with the same name in a consistent way to how
  the standard requests adapter works (by compiling the headers together).
* Added lint argument to :py:class:`~.WSGIAdapter`.

0.4
===

* Added support for iterative responses.
* Added support for streamed responses (including reading data in real-time).
* New ``make_session`` convenience function.

0.3
===

Initial version.
