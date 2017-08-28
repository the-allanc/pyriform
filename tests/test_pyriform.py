from httpbin import app as binapp
from pyriform import WSGIAdapter
from requests import Session
import pytest


class TestPyriform(object):

    def setup_class(cls):
        adapter = WSGIAdapter(binapp)
        sess = Session()
        sess.mount('http://', adapter)
        sess.mount('https://', adapter)

        cls.session = sess

    def test_url(self):

        # Test that the URL we request is what we end up with.
        def assert_url(the_url):
            resp = self.session.get(the_url)
            resp.raise_for_status()
            assert resp.json()['url'] == the_url

        # Test with default port on simple URL.
        assert_url('http://myapp.local/anything/hello.world')

        # Add query string, ensure that works.
        assert_url('http://myapp2.local/anything/hello.world?how=are+you')

        # Use non-default port.
        assert_url('http://myapp3.local:17180/anything/hello.world')

        # Use HTTPS - webtest should add the de-facto headers for indicating
        # HTTPS connections.
        assert_url('https://myapp4.local/anything/hello.world')

    def test_request_headers(self):
        headers = {'User-Agent': 'me', 'X-HeyBoy': 'HeyGirl'}
        resp = self.session.get('http://myapp.local/headers', headers=headers)
        resp.raise_for_status()

        # Turn this into a case-insensitive dictionary to make it easier to
        # compare.
        from requests.utils import CaseInsensitiveDict
        resp_headers = CaseInsensitiveDict(resp.json()['headers'])

        for h_key, h_value in headers.items():
            assert resp_headers.get(h_key) == h_value

    def test_post_json(self):
        url = 'http://myapp2.local/anything/hello.world?how=are+you'
        resp = self.session.post(url, json=[1, 3])
        resp.raise_for_status()
        jresp = resp.json()
        assert jresp['method'] == 'POST'
        assert jresp['url'] == url
        assert jresp['json'] == [1, 3]

    def test_post_form(self):
        url = 'http://myapp2.local/anything/hello.world?how=are+you'
        resp = self.session.post(url, data={'ab': 'cd'})
        resp.raise_for_status()
        jresp = resp.json()
        assert jresp['method'] == 'POST'
        assert jresp['url'] == url
        assert jresp['form'] == {'ab': 'cd'}

    def test_post_multipart(self):
        import base64
        import os

        # We'll send this for a multipart file upload.
        fpath = os.path.join(os.path.dirname(__file__), 'yellowbg.png')
        bg_image = open(fpath, 'rb')
        bg_base64 = base64.b64encode(bg_image.read()).decode('ascii')
        bg_image.seek(0)

        resp = self.session.post('http://myapp.local/post',
                                 files={'background': bg_image})
        resp_files = resp.json()['files']
        assert 'background' in resp_files
        assert resp_files['background'] == \
            'data:application/octet-stream;base64,' + bg_base64

    @pytest.mark.parametrize('method,with_body', [
        ('HEAD', False), ('DELETE', False), ('OPTIONS', False),
        ('PUT', True), ('PATCH', True),

        # We want to test that we work with custom methods, but none of the
        # httpbin handlers seem to allow for that - but we can use the "TRACE"
        # method (which doesn't have a direct handler on the app, but is listed
        # as an allowed method, so we can use it).
        ('TRACE', False),
    ])
    def test_other_methods(self, method, with_body):
        the_bytes = b'123456' if with_body else None
        url = 'http://myapp.local/anything/blah?yes=no'
        resp = self.session.request(method, url, data=the_bytes)
        resp.raise_for_status()

        if method in ('HEAD', 'OPTIONS'):
            assert not resp.content, 'response had unexpected content'
            return

        jresp = resp.json()
        assert jresp['method'] == method
        assert jresp['url'] == url
        assert jresp['data'] == ''

    @pytest.mark.parametrize('status,reason', [
        (200, 'OK'), (404, 'NOT FOUND'), (410, 'GONE'), (502, 'BAD GATEWAY'),
    ])
    def test_status_code(self, status, reason):
        url = 'http://myapp.local/status/%s' % status
        resp = self.session.get(url)
        assert resp.status_code == status
        assert resp.reason == reason

    def test_response_headers(self):
        pass

    def test_redirect(self):
        '''
        /redirect/:n 302 Redirects n times.
        /redirect-to?url=foo 302 Redirects to the foo URL.
        /redirect-to?url=foo&status_code=307 307 Redirects to the foo URL.
        /relative-redirect/:n 302 Relative redirects n times.
        /absolute-redirect/:n 302 Absolute redirects n times.
        '''
        pass

    def test_stream(self):
        pass

    def test_timeout(self):
        pass

    def test_environ_headers(self):
        pass
