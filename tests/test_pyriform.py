from httpbin import app as testapp
from pyriform import WSGIAdapter


class TestPyriform(object):

    def test_url(self):
        adapter = WSGIAdapter(testapp)
        from requests import Session
        sess = Session()
        sess.mount('http://myapp.local/', adapter)
        url = 'http://myapp.local/anything/hello.world?how=are+you'
        assert sess.get(url).json()['url'] == url
