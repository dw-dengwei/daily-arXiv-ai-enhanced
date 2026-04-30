import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import tempfile


class _FakeLlamaHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/v1/models":
            body = json.dumps({"data": [{"id": "Qwen3.5-9B-Q4_K_M.gguf"}]}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/v1/chat/completions":
            body = json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": '{"tldr":"a","motivation":"b","method":"c","result":"d","conclusion":"e"}'
                            }
                        }
                    ]
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        return


class TestLocalIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLlamaHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_enhance_process_single_item(self):
        import ai.enhance as enhance

        base_url = f"http://127.0.0.1:{self.port}/v1"
        item = {"id": "1234.5678", "summary": "abc"}
        out = enhance.process_single_item(
            base_url=base_url,
            model="Qwen3.5-9B-Q4_K_M.gguf",
            item=item,
            language="Chinese",
            temperature=0.2,
            max_tokens=100,
        )
        self.assertEqual(out["AI"]["tldr"], "a")
        self.assertEqual(set(out["AI"].keys()), {"tldr", "motivation", "method", "result", "conclusion"})

    def test_llama_model_check(self):
        import local_arxiv.__main__ as cli

        base_url = f"http://127.0.0.1:{self.port}/v1"
        cli._check_llama_server(base_url, "Qwen3.5-9B-Q4_K_M.gguf")
        with self.assertRaises(RuntimeError):
            cli._check_llama_server(base_url, "missing-model")

    def test_write_file_list(self):
        import local_arxiv.__main__ as cli

        old = os.getcwd()
        with tempfile.TemporaryDirectory() as d:
            os.chdir(d)
            Path("data").mkdir()
            Path("data/a.jsonl").write_text("{}\n")
            Path("data/b.jsonl").write_text("{}\n")
            cli._write_file_list()
            out = Path("assets/file-list.txt").read_text().splitlines()
            self.assertEqual(out, ["a.jsonl", "b.jsonl"])
        os.chdir(old)


if __name__ == "__main__":
    unittest.main()
