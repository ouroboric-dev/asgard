"""The local server of the choice pages (brand tools spec §5.7): serves the pages in the company's
docs/7-branding/identity/choices/ on 127.0.0.1 and saves the founder's confirmed choice into
docs/7-branding/identity/choices/<step>.json, where the agent reads it.

    serve.py DIR [--port N]

Nothing leaves the machine. A save needs the token the server puts in each page it serves, so another page open in the
same browser cannot save for her; only the design's steps can be saved; a request for another host name is refused.
"""
import datetime
import hmac
import json
import os
import re
import secrets
import signal
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import choicepage  # noqa: E402

MAX_BODY, MAX_REASON = 64 * 1024, 2000
NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CSP = ("default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; font-src data:; "
       "connect-src 'self'; base-uri 'none'; form-action 'none'")


def make_handler(company, token, port):
    folder = os.path.join(company, choicepage.CHOICES)
    hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "choices"

        def log_message(self, *args):
            pass

        def send(self, code, body="", kind="text/plain; charset=utf-8"):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if kind.startswith("text/html"):
                self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            self.wfile.write(data)

        def local(self):
            if self.headers.get("Host", "") not in hosts:
                self.send(421, "This server answers on 127.0.0.1 only.\n")
                return False
            return True

        def page_names(self):
            if not os.path.isdir(folder):
                return []
            return sorted(n[:-5] for n in os.listdir(folder) if n.endswith(".html") and NAME.match(n[:-5]))

        def do_GET(self):
            if not self.local():
                return
            path = self.path.split("?", 1)[0]
            if path == "/":
                links = "".join(f'<li><a href="/page/{n}">{n}</a></li>' for n in self.page_names())
                return self.send(200, f"<!doctype html><meta charset=utf-8><title>Choice pages</title><h1>Choice pages</h1>"
                                      f"<ul>{links or '<li>No page yet.</li>'}</ul>", "text/html; charset=utf-8")
            m = re.match(r"^/page/([a-z0-9-]+)$", path)
            if m and m.group(1) in self.page_names():
                with open(os.path.join(folder, m.group(1) + ".html"), encoding="utf-8") as fh:
                    html = fh.read()
                step = (re.search(r'window.__choiceStep = "([a-z0-9-]+)"', html) or [None, m.group(1)])[1]
                saved = choicepage.saved_choice(company, step)
                html = html.replace(choicepage.TOKEN_PLACEHOLDER, token)
                html = re.sub(r'(<script type="application/json" id="saved">).*?(</script>)',
                              lambda mm: mm.group(1) + choicepage.script_json(saved) + mm.group(2), html, count=1, flags=re.S)
                return self.send(200, html, "text/html; charset=utf-8")
            m = re.match(r"^/choices/([a-z0-9-]+)\.json$", path)
            if m and m.group(1) in choicepage.STEPS:
                saved = choicepage.saved_choice(company, m.group(1))
                if saved is not None:
                    return self.send(200, json.dumps(saved, indent=2) + "\n", "application/json")
            return self.send(404, "Not found.\n")

        def do_POST(self):
            if not self.local():
                return
            m = re.match(r"^/save/([a-z0-9-]+)$", self.path)
            if not m or m.group(1) not in choicepage.STEPS:
                return self.send(404, "Not found.\n")
            if not hmac.compare_digest(self.headers.get("X-Choice-Token", ""), token):
                return self.send(403, "This page cannot save: it was not opened from this server.\n")
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.send(415, "A choice is sent as application/json.\n")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY:
                return self.send(413, "A choice is at most 64 KB.\n")
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                choice, reason = body["choice"], body.get("reason", "")
                if not isinstance(choice, dict) or not isinstance(reason, str) or len(reason) > MAX_REASON:
                    raise ValueError
            except (ValueError, KeyError, TypeError):
                return self.send(400, "A choice is {\"choice\": {...}, \"reason\": \"...\"}.\n")
            step = m.group(1)
            record = {"step": step, "choice": choice, "reason": reason, "date": datetime.date.today().isoformat()}
            os.makedirs(folder, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=folder, suffix=".part")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(record, fh, indent=2, ensure_ascii=False)
                fh.write("\n")
            os.replace(tmp, os.path.join(folder, f"{step}.json"))
            return self.send(200, "Saved.\n")

    return Handler


def main(argv):
    args, port = list(argv), 0
    if "--port" in args:
        i = args.index("--port")
        try:
            port = int(args[i + 1])
            del args[i:i + 2]
        except (IndexError, ValueError):
            print("usage: brand.sh serve DIR [--port N]", file=sys.stderr)
            return 2
    if len(args) != 1:
        print("usage: brand.sh serve DIR [--port N]", file=sys.stderr)
        return 2
    company = args[0]
    if not os.path.isdir(os.path.join(company, "docs", "7-branding", "identity")):
        print(f"brand.sh serve: {company} is not a company folder: no docs/7-branding/identity", file=sys.stderr)
        return 2
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", port), lambda *a: None)
    real = server.server_address[1]
    server.RequestHandlerClass = make_handler(company, token, real)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    print(f"Serving the choice pages: http://127.0.0.1:{real}/  (stop it with Ctrl-C)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
