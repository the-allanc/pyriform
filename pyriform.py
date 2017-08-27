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

        # Execute the request.
        wtresp = self.app.get(request.url, extra_environ=environ)

        # Convert the response.
        resp = Response()
        resp.url = request.url

        for key, value in wtresp.headerlist:
            if key not in resp.headers:
                resp.headers[key] = value

        resp.request = request
        resp._content = wtresp.body
        return resp
