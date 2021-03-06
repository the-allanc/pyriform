from httpbin import app as binapp
from pyriform import make_session
from pyriform import WSGIAdapter
from requests import Session
import cherrypy
import pytest

# The tests are general enough that other adapter classes could be used instead, but some classes
# are very specific to Pyriform, so we mark these tests.
pyriform_only = pytest.mark.skipif(
    WSGIAdapter.__module__ != 'pyriform',
    reason='Test is only suitable for Pyriform WSGIAdapter only')


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

    @pyriform_only
    def test_make_session(self):

        class JustSayOK(object):
            @cherrypy.expose
            def default(self, *args):
                return 'OK'

        ok_app = cherrypy.tree.mount(JustSayOK(), '/')

        # Like above, but use make_session as the way to create a session.
        def assert_url(session, the_url):
            resp = session.get(the_url)
            resp.raise_for_status()
            assert resp.json()['url'] == the_url

        # Test default behaviour.
        sess = make_session(binapp)
        assert_url(sess, 'http://app.local/anything/hello.me')

        # Test that the explicit mount prefix works.
        sess = make_session(binapp, 'http://this.test/')

        # To prove it, link to a separate app on a different prefix.
        sess.mount('http://that.test/', WSGIAdapter(ok_app))

        assert_url(sess, 'http://this.test/anything/hello.you')
        resp = sess.get('http://that.test/just-say-ok')
        resp.raise_for_status()
        assert resp.text == 'OK'

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
        assert resp.reason.upper() == reason

    def test_response_headers(self):
        # Test that we get a header back in the response, but duplicate headers
        # shouldn't cause anything to break. Requests doesn't support duplicate
        # headers directly - it relies on urllib3 to compile the headers together.
        url = 'http://myapp.local/response-headers?X-Men=Xavier&X-Men=Cyclops'
        resp = self.session.get(url)
        resp.raise_for_status()
        assert resp.headers['X-Men'] == 'Xavier, Cyclops'

    @pytest.mark.parametrize('redir_type', [
        'relative-redirect', 'absolute-redirect',
    ])
    def test_redirect(self, redir_type):
        url = 'http://myapp.local/' + redir_type + '/3'
        resp = self.session.get(url)
        resp.raise_for_status()

        # We should have been redirected to this URL.
        assert resp.url == 'http://myapp.local/get'

        # And the other responses should be present.
        assert resp.history[0].url == url
        assert resp.history[1].url == 'http://myapp.local/' + redir_type + '/2'
        assert resp.history[2].url == 'http://myapp.local/' + redir_type + '/1'

    def test_timeout(self):
        from requests import Timeout

        url = 'http://myapp.local/delay/2'

        # No timeout.
        resp = self.session.get(url, timeout=None)
        resp.raise_for_status()

        # High timeouts - won't trigger an exception.
        for timeout in [3, (1, 3)]:
            resp = self.session.get(url, timeout=timeout)
            resp.raise_for_status()

        # Low timeouts - will trigger an exception.
        for timeout in [1, (3, 1)]:
            with pytest.raises(Timeout):
                self.session.get(url, timeout=timeout)

    @pyriform_only
    def test_environ_headers(self):
        # Force the app to have extra environment settings by default.
        environ = {'HTTP_X_FORWARDED_FOR': '123.123.456.123'}
        adapter = WSGIAdapter(binapp, environ)
        sess = Session()
        sess.mount('http://', adapter)

        url = 'http://myapp.local/anything?high=low'
        resp = sess.get(url)
        assert resp.json()['origin'] == '123.123.456.123'

    @pyriform_only
    def test_environ_headers_http_host(self):
        # Although we do set HTTP_HOST in Pyriform itself, don't let us
        # override an explicit setting given by the client code.
        environ = {'HTTP_HOST': 'yourapp.local'}
        adapter = WSGIAdapter(binapp, environ)
        sess = Session()
        sess.mount('http://', adapter)

        url = 'http://myapp.local/anything?back=front'
        resp = sess.get(url)
        assert resp.json()['url'] == url.replace('myapp', 'yourapp')

    @pyriform_only
    def test_cannot_mix_testapp_and_environ(self):
        from webtest.app import TestApp

        # You can wrap an application with the testapp library, but don't
        # do that *and* try to set an environment together.
        WSGIAdapter(TestApp(binapp))  # This is allowed.

        with pytest.raises(ValueError):
            WSGIAdapter(TestApp(binapp), {'HTTP_HOST': 'thisapp.local'})

        with pytest.raises(ValueError):
            # Also test the lint argument too.
            WSGIAdapter(TestApp(binapp), lint=True)

    def test_custom_status_reason(self):
        # We'll create a custom CherryPy app to do this.
        class MyReason(object):
            @cherrypy.expose
            def default(self, reason_text):
                cherrypy.response.status = '200 ' + reason_text

        app = cherrypy.tree.mount(MyReason(), '/')

        # Now use Pyriform to map requests from a particular URL to this app.
        sess = Session()
        sess.mount('http://app.local', WSGIAdapter(app))

        resp = sess.get('http://app.local/Hi There')
        assert resp.status_code == 200
        assert resp.reason == 'Hi There'

    @pytest.mark.parametrize('stream', [False, True])
    def test_can_iterate(self, stream):
        # This test shows that you can iterate over content.
        resp = self.session.get('http://httpbin/image/png', stream=stream)
        chunks = []
        chunk_iterator = resp.iter_content(chunk_size=6)
        for _, chunk in zip(range(3), chunk_iterator):
            chunks.append(chunk)
        expected = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00'
        assert b''.join(chunks) == expected
        chunks.extend(list(chunk_iterator))
        assert len(b''.join(chunks)) == 8090

    def test_can_use_raw(self):
        # Like above, but we use the 'raw' attribute on the response instead
        # of using iter_content. This only works when stream = True, we're
        # not expected to work when stream = False.
        resp = self.session.get('http://httpbin/image/png', stream=True)
        data = resp.raw.read(18)
        expected = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00'
        assert data == expected

    def test_iterate_in_real_time(self):
        # Show that we iterate over content as it is being emitted, and we're
        # not just reading the entire content body first.
        import time
        then = time.time()

        # We want the first four bytes - we should get them in under 2.5
        # seconds (it should be fractionally more than 2).  If we are reading
        # the entire content body in, it will take us at least 5 seconds to get
        # the four bytes we want.
        url = 'http://server/drip?duration=5&numbytes=10'
        resp = self.session.get(url, stream=True)
        assert len(resp.raw.read(4)) == 4

        wait = time.time() - then
        assert wait <= 5, 'all content is being read before streaming starts'
        assert wait <= 2.5, 'reading content took longer than expected'
        assert wait >= 1, 'resource did not appear to be delaying content'

    def test_multiple_cookies(self):
        session = Session()
        session.mount('http://localhost', WSGIAdapter(binapp))
        session.get("http://localhost/cookies/set?flimble=floop&flamble=flaap")
        response = session.get("http://localhost/cookies")
        assert response.json() == {'cookies': {'flimble': 'floop', 'flamble': 'flaap'}}

    def test_warn_if_streaming_with_custom_testapp(self):
        # Show that we generate a warning if you try to stream content, but you've set up the
        # adapter in a way which prevents us from streaming it in real time.
        from webtest.app import TestApp
        session = make_session(TestApp(binapp))
        with pytest.warns(RuntimeWarning) as w:
            session.get('http://httpbin/image/png', stream=True)

        assert str(w[0].message) == (
            'Passing a TestApp instance to WSGIAdapter prevents '
            'streamed requests from streaming content in real time.'
        )
