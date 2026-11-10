"""The HTTP fixture has no model, accounts, filesystem tools or external network."""
import asyncio
from importlib.util import find_spec
import json
import os
import unittest
from unittest.mock import patch

from tools.codex_aux.proxy import ProxyClient, ProxyError


class ProxyConfigurationTests(unittest.TestCase):
    def test_credentials_only_go_to_literal_loopback(self):
        for url in ("https://example.org", "http://127.0.0.1.example.org",
                    "http://key@localhost", "http://127.0.0.1:80/?key=secret",
                    "http://localhost/some/path", "http://[::1]:0"):
            with self.subTest(url=url), self.assertRaisesRegex(ProxyError, "^unsafe_endpoint$"):
                ProxyClient(url)
        self.assertEqual(ProxyClient("http://localhost:4222").base_url, "http://127.0.0.1:4222")


@unittest.skipUnless(find_spec("httpx"), "optional httpx transport")
class LocalProxyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.model = "fixture-text"
        self.accounts = [{"eligible_now": True}]
        self.report = {"summary": "A pose usa o quadro informado.", "evidence": ["rig.ts:3"]}
        self.completion = {
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(self.report)}}],
            "usage": {"prompt_tokens": 87, "completion_tokens": 21,
                      "prompt_tokens_details": {"cached_tokens": 32}},
        }
        self.status = 200
        self.fail = False
        self.pause = False
        self.barrier = False
        self.peak = self.active = self.posts = 0
        self.started = asyncio.Event()
        self.both = asyncio.Event()
        self.disconnected = asyncio.Event()
        self.requests = []
        self.server = await asyncio.start_server(self._serve, "127.0.0.1", 0)
        port = self.server.sockets[0].getsockname()[1]
        self.client = ProxyClient(f"http://127.0.0.1:{port}", "fixture-secret", timeout=3)

    async def asyncTearDown(self):
        self.server.close()
        await self.server.wait_closed()

    async def _serve(self, reader, writer):
        try:
            header = (await reader.readuntil(b"\r\n\r\n")).decode("ascii")
            first, *fields = header.strip().split("\r\n")
            method, path, _ = first.split()
            headers = dict(field.lower().split(": ", 1) for field in fields)
            body = await reader.readexactly(int(headers.get("content-length", "0")))
            self.requests.append((method, path))
            status = 200
            if path == "/health/live":
                self.assertNotIn("authorization", headers)
                response = {"status": "ok"}
            elif headers.get("authorization") != "bearer fixture-secret":
                status, response = 401, {"private_error": "fixture-secret"}
            elif path == "/admin/accounts":
                response = {"accounts": self.accounts}
            elif path == "/v1/models":
                response = {"data": [{"id": self.model}, {"id": "gpt-image-2"}]}
            elif path == "/v1/chat/completions" and method == "POST":
                payload = json.loads(body)
                self.assertEqual(payload["model"], self.model)
                self.assertTrue(payload["response_format"]["json_schema"]["strict"])
                self.assertNotIn("tools", payload)
                self.assertNotIn("fixture-secret", body.decode())
                self.posts += 1
                self.active += 1
                self.peak = max(self.peak, self.active)
                self.started.set()
                try:
                    if self.peak == 2:
                        self.both.set()
                    if self.barrier:
                        await asyncio.wait_for(self.both.wait(), 2)
                    if self.pause:
                        await reader.read()
                        self.disconnected.set()
                        return
                    status = self.status
                    response = {"private_error": "fixture-secret"} if self.fail else self.completion
                finally:
                    self.active -= 1
            else:
                status, response = 404, {}
            raw = json.dumps(response).encode()
            frame = f"HTTP/1.1 {status} Fixture\r\nContent-Length: {len(raw)}\r\nConnection: close\r\n\r\n"
            writer.write(frame.encode() + raw)
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

    async def analyze(self):
        return await self.client.analyze(self.model, "Qual pose é usada?", "rig.ts:3 pose=walk")

    async def test_nondefault_port_cannot_receive_automatically_discovered_key(self):
        client = ProxyClient(self.client.base_url)
        with patch.dict(os.environ, {"PROXY_API_KEY": "fixture-secret"}):
            with self.assertRaisesRegex(ProxyError, "^explicit_key_required$"):
                await client.preflight(self.model)
        self.assertEqual(self.requests, [("GET", "/health/live")])

    async def test_two_independent_in_flight_and_reported_usage(self):
        self.barrier = True
        self.assertEqual(await self.client.preflight(self.model), [self.model])
        first, second = await asyncio.gather(self.analyze(), self.analyze())
        self.assertEqual(first, second)
        self.assertEqual(first, (self.report, {"input_tokens": 87, "output_tokens": 21,
                                             "cached_input_tokens": 32}))
        self.assertEqual((self.peak, self.posts), (2, 2))
        self.assertEqual(self.requests.count(("GET", "/v1/models")), 1)

    async def test_quota_stops_future_dispatch_without_replay(self):
        self.status, self.fail = 429, True
        for attempted in (True, False):
            with self.assertRaisesRegex(ProxyError, "^rate_limit$") as raised:
                await self.analyze()
            self.assertEqual(raised.exception.attempted, attempted)
            self.assertFalse(raised.exception.uncertain)
        self.assertEqual(self.posts, 1)

    async def test_server_redirect_and_permanent_failures_cannot_leak_bodies(self):
        self.fail = True
        for status, code in ((302, "request_rejected"), (401, "authentication"),
                             (400, "request_rejected"), (503, "server_error")):
            self.status = status
            with self.assertRaisesRegex(ProxyError, "^" + code + "$") as raised:
                await self.analyze()
            self.assertTrue(raised.exception.attempted)
            self.assertEqual(raised.exception.uncertain, status >= 500)
        self.assertEqual(self.posts, 4)

    async def test_rotation_cooldown_and_model_validation_before_inference(self):
        for accounts, code in (([], "no_account"), ([{"eligible_now": False}], "account_unavailable"),
                               ([{"eligible_now": True}, {"eligible_now": False}], "account_rotation")):
            self.accounts = accounts
            with self.assertRaisesRegex(ProxyError, "^" + code + "$"):
                await self.analyze()
        self.accounts = [{"eligible_now": True}]
        for model in ("unavailable", "gpt-image-2"):
            with self.assertRaisesRegex(ProxyError, "^model_unavailable$"):
                await self.client.preflight(model)
        self.assertEqual(self.posts, 0)

    async def test_unknown_usage_remains_unknown_and_partial_responses_are_rejected(self):
        del self.completion["usage"]
        self.assertEqual((await self.analyze())[1], {"input_tokens": None, "output_tokens": None,
                                                   "cached_input_tokens": None})
        self.completion["choices"][0]["finish_reason"] = "length"
        with self.assertRaisesRegex(ProxyError, "^incomplete_response$") as raised:
            await self.analyze()
        self.assertIsNone(raised.exception.usage["input_tokens"])
        self.completion["choices"][0] = {"finish_reason": "stop", "message": {"content": "fixture-secret"}}
        with self.assertRaisesRegex(ProxyError, "^invalid_report$"):
            await self.analyze()
        self.completion["choices"][0]["message"]["content"] = json.dumps(
            {"summary": "An accidentally echoed fixture-secret", "evidence": []}
        )
        with self.assertRaisesRegex(ProxyError, "^unsafe_report$"):
            await self.analyze()

    async def test_cancellation_closes_http_socket(self):
        self.pause = True
        task = asyncio.create_task(self.analyze())
        await asyncio.wait_for(self.started.wait(), 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(self.disconnected.wait(), 1)
        self.assertEqual(self.posts, 1)

    async def test_wall_timeout_closes_http_socket_and_never_reposts(self):
        self.pause = True
        self.client.timeout = 1
        with self.assertRaisesRegex(ProxyError, "^timeout$") as raised:
            await self.analyze()
        self.assertTrue(raised.exception.attempted)
        self.assertTrue(raised.exception.uncertain)
        await asyncio.wait_for(self.disconnected.wait(), 2)
        self.assertEqual(self.posts, 1)
