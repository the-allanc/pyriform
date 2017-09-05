import itertools as it
from io import TextIOBase
from requests.adapters import BaseAdapter, Response
from requests import Session, Timeout
from six.moves.urllib.parse import urlparse
import six
from urllib3.response import HTTPHeaderDict
import warnings
from webtest.app import TestApp, TestRequest
from webtest.response import TestResponse
from webob.response import iter_close
import threading

__all__ = ['WSGIAdapter', 'make_session']


def make_session(app, prefix='http://'):
    '''Convenience function for creating a session which maps the app to a particular URL.

    If you need to have more control over the :py:class:`WSGIAdapter` instance that's created,
    or you need to generate a session in a different way, then you can just do it manually.

    Args:
        app (WSGI application): The app to send requests to - this should be a
            callable which takes two arguments: *environ* and *start_response*.

            Alternatively, you can pass a :py:class:`~webtest.app.TestApp` object.
        prefix (string): The URL prefix to mount the app to. Defaults to ``http://`` (e.g. for
            all HTTP traffic).

    Returns:
        A :py:class:`~requests.Session` object which has the application mounted to the desired
        URL prefix.
    '''
    session = Session()
    session.mount(prefix, WSGIAdapter(app))
    return session


class WSGIAdapter(BaseAdapter):

    '''A Requests adapter that will connect to a WSGI app.

    This object should be mounted as a transport adapter to a
    :py:class:`~requests.Session` object to have all matching requests sent to
    it; read more about using transport adapters :ref:`here <transport-adapters>`.

    Args:
        app (WSGI application): The app to send requests to - this should be a
            callable which takes two arguments: *environ* and *start_response*.

            Alternatively, you can pass a :py:class:`~webtest.app.TestApp` object.
        extra_environ (dict of string -> string): Extra environment values that
            the WSGI app will inherit for every request that it handles.
        lint (boolean): Enables the :py:mod:`webtest.lint` module for the WSGI application.

            By default, this is disabled - it's useful if you want to test the WSGI app itself,
            but not if you are testing client-side behaviour.
    '''
    def __init__(self, app, extra_environ=None, lint=False):
        super(BaseAdapter, self).__init__()
        if not isinstance(app, TestApp):
            app = TestApp(app, extra_environ=extra_environ, lint=lint)
            app.RequestClass = PyriformTestRequest
        elif extra_environ:
            raise ValueError('cannot pass extra_environ and a TestApp instance'
                             ' at the same time')
        elif lint:
            raise ValueError('cannot use lint and pass a TestApp instance'
                             ' at the same time')
        self.app = app

    def send(self, request, stream=False, timeout=None, verify=True,
             cert=None, proxies=None):

        # Prepare the request to send to the app.

        # webob will include the port into the HTTP_HOST header by default.
        #
        # It's not desirable, so let's insert it into the environment
        # manually. But only do this if the user hasn't set an explicit host
        # name.
        environ = {}
        if 'HTTP_HOST' not in self.app.extra_environ:
            parsed = urlparse(request.url)
            environ['HTTP_HOST'] = parsed.netloc

        non_body_methods = set('GET HEAD DELETE OPTIONS'.split())
        with_body_methods = set('POST PUT PATCH'.split())

        wtparams = dict(headers=request.headers, extra_environ=environ,
                        url=request.url, expect_errors=True)
        if request.method in with_body_methods:
            wtparams['params'] = request.body

        if stream and not issubclass(self.app.RequestClass, PyriformTestRequest):
            warnings.warn('Passing a TestApp instance to WSGIAdapter prevents '
                          'streamed requests from streaming content in real time.',
                          RuntimeWarning)

        # Delegate to the appropriate handler if we have one.
        if request.method in non_body_methods or \
                request.method in with_body_methods:
            handler = getattr(self.app, request.method.lower())
        else:
            # This is an internal method, but most handlers delegate to it, so
            # we'll just make use of it for unknown methods.
            wtparams['method'] = request.method
            handler = self.app._gen_request

        # We only care about the read timeout.
        if isinstance(timeout, tuple):
            _, timeout = timeout

        wtresp = self._invoke_handler(handler, wtparams, timeout)

        # Convert the response.
        resp = Response()
        resp.status_code = wtresp.status_code
        resp.reason = wtresp.status.split(' ', 1)[1]
        resp.url = request.url

        # Although HTTPHeaderDict is better positioned to handle multiple headers with the same
        # name, requests doesn't use this type for responses. Instead, it uses its own dictionary
        # type for headers (which doesn't have multiple header value support).
        #
        # But because it uses the HTTPHeaderDict object, all multiple value headers will be
        # compiled together, so that's what we store here (to be consistent with requests).
        #
        # It would be nice to use HTTPHeaderDict for the response, but we don't want to provide a
        # different object with a different API.
        resp.headers.update(HTTPHeaderDict(wtresp.headerlist))

        resp.request = request
        resp.raw = IterStringIO(wtresp._app_iter)
        return resp

    def _invoke_handler(self, handler, params, timeout):
        # Handle synchronously if there's no timeout.
        if not timeout:
            return handler(**params)

        # As there is a timeout, we'll execute it in a separate thread.

        # We store the result at index 0, and the current thread will signal to the
        # spawned thread if it has cancelled its request at index 1.
        result = [None, False]

        def invoke_request():
            try:
                result[0] = handler(**params)
            except Exception as e:  # pragma: no cover
                result[0] = e
            else:
                # This prevents the webtest linter from generating a warning about the iterable
                # response not being closed properly.
                if result[1]:  # Request has been cancelled.
                    iter_close(result[0]._app_iter)  # Tidy up the request.

        thread = threading.Thread(target=invoke_request)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            result[1] = True  # tell the thread we don't want the result
            raise Timeout()
        if isinstance(result[0], Exception):  # pragma: no cover
            raise result[0]
        return result[0]


class PyriformTestResponse(TestResponse):

    # This suppresses the entire body content being consumed before being
    # returned.
    body = property(lambda self: None)


class PyriformTestRequest(TestRequest):
    ResponseClass = PyriformTestResponse


if six.PY2:
    _join_bytes = b''.join
else:
    _join_bytes = bytearray


# Brilliant solution for this taken from here (and then tweaked by me):
#  https://stackoverflow.com/questions/12593576/adapt-an-iterator-to-behave-like-a-file-like-object-in-python/32020108#32020108
class IterStringIO(TextIOBase):
    def __init__(self, iterable):
        self.iterable = iterable
        self.iter = it.chain.from_iterable(iterable)

    def not_newline(self, s):  # pragma: no cover
        return s not in {'\n', '\r', '\r\n'}

    def read(self, n=None):
        return _join_bytes(it.islice(self.iter, None, n))

    def readline(self, n=None):  # pragma: no cover
        to_read = it.takewhile(self.not_newline, self.iter)
        return _join_bytes(it.islice(to_read, None, n))

    def close(self):
        if hasattr(self, 'iterable'):
            iter_close(self.iterable)
            del self.iterable
            del self.iter
