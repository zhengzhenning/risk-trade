#!/usr/bin/env python3
"""本地静态服务（L1 实时层的页面入口）：默认只读 archives/，禁缓存 live.json

用法：
  python3 scripts/serve_live.py --dir archives --port 8777
  # 浏览器打开 http://127.0.0.1:8777/market-briefing-YYYY-MM-DD.html

仅在本地回环地址监听；live.json 与 *.html 一律 no-store，确保每分钟拿到新数据。
"""
import argparse, functools, http.server, os, socketserver


class Handler(http.server.SimpleHTTPRequestHandler):
    """路由：/ → 实时看板，/history → 历史索引，/d/<date> → 指定日期看板，其余静态文件。"""
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        root = self.directory
        if path in ("/", "/live", "/live.html"):
            return self._serve(os.path.join(root, "live.html"))
        if path in ("/history", "/history.html"):
            return self._serve(os.path.join(root, "history.html"))
        m = __import__("re").match(r"^/d/(\d{4}-\d{2}-\d{2})/?$", path)
        if m:
            return self._serve(os.path.join(root, "market-briefing-%s.html" % m.group(1)))
        return super().do_GET()

    def _serve(self, file_path):
        if not os.path.isfile(file_path):
            self.send_error(404, "Not found: " + os.path.basename(file_path))
            return
        data = open(file_path, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # 静默访问日志


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="archives")
    ap.add_argument("--port", type=int, default=8777)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    root = os.path.abspath(args.dir)
    if not os.path.isdir(root):
        raise SystemExit("目录不存在: " + root)
    handler = functools.partial(Handler, directory=root)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((args.host, args.port), handler) as httpd:
        print("[INFO] serving %s at http://%s:%d/" % (root, args.host, args.port))
        httpd.serve_forever()


if __name__ == "__main__":
    main()
