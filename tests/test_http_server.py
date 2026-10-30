"""Real-socket tests against the same server entry point used by local users."""
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HealthOpsHttpServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='healthops-http-')
        try:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                cls.port = probe.getsockname()[1]
        except PermissionError as exc:
            cls.temp.cleanup()
            raise unittest.SkipTest(f'Execution sandbox denies local socket creation: {exc}')
        env = os.environ.copy()
        env['HEALTHOPS_DB'] = str(Path(cls.temp.name) / 'http-test.sqlite3')
        env['PORT'] = str(cls.port)
        env['HEALTHOPS_READ_ONLY'] = '1'
        env['HEALTHOPS_SECURE_COOKIES'] = '1'
        cls.process = subprocess.Popen(
            [sys.executable, 'api/server.py'], cwd=ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        cls.cookie = ''
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            if cls.process.poll() is not None:
                out, err = cls.process.communicate()
                raise RuntimeError(f'HTTP server exited during startup. stdout={out!r}; stderr={err!r}')
            try:
                status, _, _ = cls.request('GET', '/health')
                if status == 200:
                    break
            except (ConnectionError, OSError):
                time.sleep(0.05)
        else:
            cls.stop_process()
            raise RuntimeError('HTTP server did not become ready on its local port')

    @classmethod
    def request(cls, method, path, body=None, headers=None, use_cookie=False):
        connection = http.client.HTTPConnection('127.0.0.1', cls.port, timeout=3)
        outgoing = dict(headers or {})
        payload = body
        if isinstance(body, (dict, list)):
            payload = json.dumps(body)
            outgoing.setdefault('Content-Type', 'application/json')
        if use_cookie and cls.cookie:
            outgoing['Cookie'] = cls.cookie
        connection.request(method, path, body=payload, headers=outgoing)
        response = connection.getresponse()
        content = response.read()
        result_headers = {key.lower(): value for key, value in response.getheaders()}
        status = response.status
        connection.close()
        if result_headers.get('content-type', '').startswith('application/json'):
            content = json.loads(content)
        return status, content, result_headers

    @classmethod
    def stop_process(cls):
        process = getattr(cls, 'process', None)
        if not process:
            return '', ''
        if process.poll() is None:
            process.terminate()
        try:
            out, err = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            out, err = process.communicate(timeout=5)
        cls.temp.cleanup()
        return out, err

    @classmethod
    def tearDownClass(cls):
        out, err = cls.stop_process()
        if 'Traceback' in err:
            raise AssertionError(f'Unexpected server traceback on stderr: {err}')

    def test_homepage_and_static_assets_are_served_with_security_headers(self):
        status, body, headers = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn(b'HealthOps Intelligence', body)
        self.assertEqual(headers['x-content-type-options'], 'nosniff')
        self.assertIn("frame-ancestors 'none'", headers['content-security-policy'])
        for path, expected in [('/styles.css', b':root'), ('/app.js', b'const')]:
            with self.subTest(path=path):
                status, content, asset_headers = self.request('GET', path)
                self.assertEqual(status, 200)
                self.assertIn(expected, content)
                self.assertIn('text/', asset_headers['content-type'])

    def test_authentication_sets_and_reuses_session_cookie(self):
        status, body, headers = self.request('POST', '/api/auth/login', {
            'email': 'visitor@healthops.local', 'password': 'HealthOpsViewOnly2026!',
        })
        self.assertEqual(status, 200)
        self.assertEqual(body['user']['role'], 'viewer')
        self.assertTrue(body['read_only_mode'])
        cookie_header = headers['set-cookie']
        self.assertIn('HttpOnly', cookie_header)
        self.assertIn('SameSite=Strict', cookie_header)
        self.assertIn('Path=/', cookie_header)
        self.assertIn('Secure', cookie_header)
        self.__class__.cookie = cookie_header.split(';', 1)[0]

        status, body, _ = self.request('GET', '/api/auth/me', use_cookie=True)
        self.assertEqual(status, 200)
        self.assertEqual(body['user']['email'], 'visitor@healthops.local')
        status, body, _ = self.request('GET', '/api/dashboard', use_cookie=True)
        self.assertEqual(status, 200)
        self.assertIn('active_patients', body)
        status, body, _ = self.request('GET', '/api/audit', use_cookie=True)
        self.assertEqual(status, 200)
        self.assertIn('items', body)
        self.assertIsNone(self.process.poll(), 'server process exited during authenticated HTTP requests')

    def test_protected_routes_reject_anonymous_and_enforce_origin_and_role(self):
        status, body, _ = self.request('GET', '/api/patients')
        self.assertEqual(status, 401)
        self.assertIn('error', body)
        status, _, _ = self.request('POST', '/api/auth/login', {
            'email': 'admin@healthops.local', 'password': 'DemoHealthOps!2026',
        })
        self.assertEqual(status, 401, 'public mode must not authenticate a privileged demo account')
        status, _, _ = self.request('POST', '/api/patients', {
            'code': 'HTTP-CSRF', 'full_name': 'Synthetic Person',
            'email': 'person@example.invalid', 'age': 30,
        }, headers={'Origin': 'https://untrusted.invalid'}, use_cookie=True)
        self.assertEqual(status, 403)

        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        connection.request('POST', '/api/patients', json.dumps({
            'code': 'HTTP-RBAC', 'full_name': 'Synthetic Person',
            'email': 'person@example.invalid', 'age': 30,
        }), {'Content-Type': 'application/json', 'Cookie': self.__class__.cookie})
        response = connection.getresponse()
        self.assertEqual(response.status, 403)
        response.read()
        connection.close()

    def test_server_remains_alive_after_rejected_requests(self):
        for method, path in [('GET', '/api/dashboard'), ('POST', '/api/auth/login')]:
            status, _, _ = self.request(method, path, {} if method == 'POST' else None)
            self.assertIn(status, (401, 415))
        self.assertIsNone(self.process.poll())
        status, payload, _ = self.request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertEqual(payload['status'], 'ok')


if __name__ == '__main__':
    unittest.main(verbosity=2)
