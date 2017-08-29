from requests.adapters import BaseAdapter, Response
from requests import Timeout
from six.moves.urllib.parse import urlparse
from webtest.app import TestApp
import threading

__all__ = ['WSGIAdapter']

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
    '''
    def __init__(self, app, extra_environ=None):
        super(BaseAdapter, self).__init__()
        if not isinstance(app, TestApp):
            app = TestApp(app, extra_environ=extra_environ)
        elif extra_environ:
            raise ValueError('cannot pass extra_environ and a TestApp instance'
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

        for key, value in wtresp.headerlist:
            if key not in resp.headers:
                resp.headers[key] = value

        resp.request = request
        resp._content = wtresp.body
        return resp

    def _invoke_handler(self, handler, params, timeout):
        # Handle synchronously if there's no timeout.
        if not timeout:
            return handler(**params)

        # If there is a timeout, we'll execute it in a separate thread.
        result = [None]
        def invoke_request():
            try:
                result[0] = handler(**params)
            except Exception as e: # pragma: no cover
                result[0] = e

        thread = threading.Thread(target=invoke_request)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            raise Timeout()
        if isinstance(result[0], Exception): # pragma: no cover
            raise result[0]
        return result[0]
