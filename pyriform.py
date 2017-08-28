from requests.adapters import BaseAdapter, Response
from six.moves.urllib.parse import urlparse
from webtest.app import TestApp

__all__ = ['WSGIAdapter']

class WSGIAdapter(BaseAdapter):
    
    def __init__(self, app):
        super(BaseAdapter, self).__init__()
        if not isinstance(app, TestApp):
            app = TestApp(app)
        self.app = app
        
    def send(self, request, stream=False, timeout=None, verify=True,
             cert=None, proxies=None):

        # Prepare the request to send to the app.

        # webob will include the port into the HTTP_HOST header by default.
        #
        # It's not desirable, so let's insert it into the environment
        # manually.
        parsed = urlparse(request.url)
        environ = {'HTTP_HOST': parsed.netloc}

        non_body_methods = set('GET HEAD DELETE OPTIONS'.split())
        with_body_methods = set('POST PUT PATCH'.split())

        wtparams = dict(headers=request.headers, extra_environ=environ,
                        url=request.url)
        if request.method in with_body_methods:
            wtparams['params'] = request.body

        # Delegate to the appropriate handler if we have one.
        if request.method in non_body_methods or \
            request.method in with_body_methods:
            handler = getattr(self.app, request.method.lower())
        else:
            # Sort this out later.
            raise NotImplementedError(request.method)

        # Execute the request.
        wtresp = handler(**wtparams)

        # Convert the response.
        resp = Response()
        resp.status_code = wtresp.status_code
        resp.reason = wtresp.status.split(' ')[1]
        resp.url = request.url

        for key, value in wtresp.headerlist:
            if key not in resp.headers:
                resp.headers[key] = value

        resp.request = request
        resp._content = wtresp.body
        return resp
