"""Exercise a real local server on an OS-assigned port."""
import json
from http.client import HTTPConnection
from urllib.parse import urlsplit
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]
        cls.process=subprocess.Popen([sys.executable,str(root/'src/server.py'),'--port','0','--no-browser'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
        cls.url=cls.process.stdout.readline().split()[1]

    @classmethod
    def tearDownClass(cls):
        cls.process.terminate();cls.process.wait(timeout=5);cls.process.stdout.close()

    def post(self,body,**headers):
        return urlopen(Request(self.url+'/api/run',data=body,headers={'Content-Type':'application/json',**headers}),timeout=5)

    def test_default_json(self):
        with self.post(b'{}') as response:
            result=json.load(response)
        self.assertTrue(result['rows']);self.assertGreaterEqual(len(result['metrics']),6)

    def test_html_and_missing_route(self):
        with urlopen(self.url,timeout=5) as response:
            self.assertIn(b'Run experiment',response.read())
        with self.assertRaises(HTTPError) as context:urlopen(self.url+'/missing',timeout=5)
        self.assertEqual(context.exception.code,404);context.exception.close()

    def test_bad_json_and_parameters(self):
        for body in [b'{',b'[]',b'{"unknown":1}']:
            with self.assertRaises(HTTPError) as context:self.post(body)
            self.assertEqual(context.exception.code,400);context.exception.close()

    def test_cross_origin_rejected(self):
        with self.assertRaises(HTTPError) as context:self.post(b'{}',Origin='https://example.com')
        self.assertEqual(context.exception.code,403);context.exception.close()

    def test_oversized_request_rejected(self):
        connection = HTTPConnection(urlsplit(self.url).netloc, timeout=5)
        try:
            connection.putrequest('POST', '/api/run')
            connection.putheader('Content-Length', '1000001')
            connection.endheaders()
            response = connection.getresponse()
            self.assertEqual(response.status, 400)
            response.read()
        finally:
            connection.close()


if __name__=='__main__':unittest.main()
