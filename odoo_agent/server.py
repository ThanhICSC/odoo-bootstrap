"""
Local HTTP server nhận lệnh từ UI và chạy agent.
Chạy: python server.py
Sau đó mở: ui.html trong trình duyệt
"""
from __future__ import annotations
import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


def run_agent_sync(url, user, password, gemini_key, scenario):
    """Wrapper chạy async agent trong sync context."""
    async def _run():
        try:
            from browser_use import Agent
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            yield "❌ Thiếu thư viện. Chạy: pip install browser-use langchain-google-genai playwright"
            yield "Sau đó: playwright install chromium"
            return

        from agent import DEMO_SCENARIOS
        os.environ["GEMINI_API_KEY"] = gemini_key

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=gemini_key,
            temperature=0.1,
        )

        task = DEMO_SCENARIOS.get(scenario, DEMO_SCENARIOS["full"])
        task = task.format(url=url, user=user, password=password)

        yield f"🤖 Khởi tạo agent Gemini..."
        yield f"🌐 Mở Chrome → {url}"

        agent = Agent(
            task=task,
            llm=llm,
            max_actions_per_step=10,
        )

        result = await agent.run(max_steps=200)
        yield f"✅ Kết quả: {result}"

    return _run()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Tắt log mặc định

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/run":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def write(msg):
            data = (msg + "\n").encode("utf-8")
            self.wfile.write(f"{len(data):x}\r\n".encode())
            self.wfile.write(data)
            self.wfile.write(b"\r\n")
            self.wfile.flush()

        write(f"🚀 Bắt đầu kịch bản: {body.get('scenario', 'full')}")

        try:
            import subprocess, sys
            result = subprocess.run(
                [
                    sys.executable, "agent.py",
                    "--url", body["url"],
                    "--user", body.get("user", "admin"),
                    "--password", body["password"],
                    "--gemini-key", body["gemini_key"],
                    "--scenario", body.get("scenario", "full"),
                ],
                capture_output=True, text=True, timeout=600,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            for line in result.stdout.split("\n"):
                if line.strip():
                    write(line)
            if result.returncode != 0:
                write(f"❌ Lỗi: {result.stderr[:500]}")
        except Exception as e:
            write(f"❌ Exception: {e}")

        # End chunked
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()


if __name__ == "__main__":
    port = 7788
    server = HTTPServer(("localhost", port), Handler)
    print(f"✅ Server đang chạy tại http://localhost:{port}")
    print(f"📂 Mở file ui.html trong trình duyệt để sử dụng")
    print(f"   Hoặc: xdg-open ui.html")
    print(f"\nCtrl+C để dừng")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDừng server")
