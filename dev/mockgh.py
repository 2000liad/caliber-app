"""A local stand-in for the slice of the GitHub REST API the app uses, for testing the page
without a real token or the real repo. Serves the page at / and the API under /gh.

    python3 dev/mockgh.py <repo root> [port]

<repo root> is a folder laid out like caliber-relay (app/data, app/user, relay/state). Writes go
to that folder. The token is "test-token". Blob shas are real git blob shas; the head is a hash
of the tree, so it moves whenever a file changes, the way a commit would.
"""
import base64, hashlib, json, os, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

ROOT = os.path.abspath(sys.argv[1])
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "index.html")
TOKEN = "test-token"
REPO = "/gh/repos/2000liad/caliber-relay"
ISSUES = os.path.join(ROOT, ".mock-issues.json")


def blob_sha(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def head():
    h = hashlib.sha1()
    for d, _, fs in sorted(os.walk(ROOT)):
        for f in sorted(fs):
            if f.startswith(".mock"):
                continue
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, ROOT).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


def load_issues():
    if not os.path.exists(ISSUES):
        return []
    with open(ISSUES, encoding="utf-8") as fh:
        return json.load(fh)


def save_issues(xs):
    with open(ISSUES, "w", encoding="utf-8") as fh:
        json.dump(xs, fh, ensure_ascii=False, indent=1)


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    def send(self, code, body=b"", ctype="application/json", etag=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str):
            body = body.encode()
        if etag and self.headers.get("If-None-Match") == etag and self.command == "GET":
            self.send_response(304)
            self.send_header("ETag", etag)
            self.end_headers()
            return
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if etag:
            self.send_header("ETag", etag)
        self.end_headers()
        self.wfile.write(body)

    def authed(self):
        if self.headers.get("Authorization") != "Bearer " + TOKEN:
            self.send(401, {"message": "Bad credentials"})
            return False
        return True

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            with open(PAGE, "rb") as fh:
                return self.send(200, fh.read(), "text/html; charset=utf-8")
        if not u.path.startswith("/gh/"):
            return self.send(404, {"message": "Not Found"})
        if not self.authed():
            return
        p = u.path
        if p == REPO:
            return self.send(200, {"full_name": "2000liad/caliber-relay", "private": True})
        if p == REPO + "/commits/main":
            h = head()
            return self.send(200, h, "text/plain", etag='"%s"' % h)
        m = re.fullmatch(REPO + r"/git/blobs/([0-9a-f]{40})", p)
        if m:
            for d, _, fs in os.walk(ROOT):
                for f in fs:
                    with open(os.path.join(d, f), "rb") as fh:
                        data = fh.read()
                    if blob_sha(data) == m.group(1):
                        return self.send(200, data, "application/octet-stream")
            return self.send(404, {"message": "Not Found"})
        m = re.fullmatch(REPO + r"/contents/(.+)", p)
        if m:
            fp = os.path.join(ROOT, m.group(1))
            if os.path.isdir(fp):
                out = []
                for f in sorted(os.listdir(fp)):
                    q = os.path.join(fp, f)
                    if f.startswith(".mock"):
                        continue
                    if os.path.isdir(q):
                        out.append({"name": f, "type": "dir", "sha": "0" * 40})
                    else:
                        with open(q, "rb") as fh:
                            out.append({"name": f, "type": "file", "sha": blob_sha(fh.read())})
                return self.send(200, out)
            if os.path.isfile(fp):
                with open(fp, "rb") as fh:
                    data = fh.read()
                return self.send(200, {"type": "file", "sha": blob_sha(data), "encoding": "base64",
                                       "content": base64.encodebytes(data).decode()})
            return self.send(404, {"message": "Not Found"})
        if p == REPO + "/issues":
            q = parse_qs(u.query)
            xs = load_issues()
            if "labels" in q:
                want = q["labels"][0]
                xs = [i for i in xs if want in [l["name"] for l in i["labels"]]]
            xs = sorted(xs, key=lambda i: i["number"], reverse=True)[: int(q.get("per_page", ["30"])[0])]
            tag = '"%s"' % hashlib.sha1(json.dumps(xs, sort_keys=True).encode()).hexdigest()
            return self.send(200, xs, etag=tag)
        return self.send(404, {"message": "Not Found"})

    def do_PUT(self):
        if not self.authed():
            return
        m = re.fullmatch(REPO + r"/contents/(.+)", urlparse(self.path).path)
        if not m:
            return self.send(404, {"message": "Not Found"})
        b = self.body()
        fp = os.path.join(ROOT, m.group(1))
        cur = None
        if os.path.isfile(fp):
            with open(fp, "rb") as fh:
                cur = blob_sha(fh.read())
        if cur and b.get("sha") != cur:
            return self.send(409, {"message": "sha does not match"})
        data = base64.b64decode(b["content"])
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, "wb") as fh:
            fh.write(data)
        return self.send(200, {"content": {"sha": blob_sha(data)}, "commit": {"sha": head(), "message": b.get("message")}})

    def do_POST(self):
        if not self.authed():
            return
        if urlparse(self.path).path != REPO + "/issues":
            return self.send(404, {"message": "Not Found"})
        b = self.body()
        xs = load_issues()
        n = max([i["number"] for i in xs] or [0]) + 1
        i = {"number": n, "title": b["title"], "body": b.get("body", ""), "state": "open", "state_reason": None,
             "labels": [{"name": l} for l in b.get("labels", [])], "created_at": now(), "closed_at": None,
             "html_url": "https://github.com/2000liad/caliber-relay/issues/%d" % n, "user": {"login": "2000liad"}}
        xs.append(i)
        save_issues(xs)
        return self.send(201, i)

    def do_PATCH(self):
        if not self.authed():
            return
        m = re.fullmatch(REPO + r"/issues/(\d+)", urlparse(self.path).path)
        if not m:
            return self.send(404, {"message": "Not Found"})
        b = self.body()
        xs = load_issues()
        for i in xs:
            if i["number"] == int(m.group(1)):
                for k in ("state", "state_reason", "title", "body"):
                    if k in b:
                        i[k] = b[k]
                if "labels" in b:
                    i["labels"] = [{"name": l} for l in b["labels"]]
                if b.get("state") == "closed":
                    i["closed_at"] = now()
                save_issues(xs)
                return self.send(200, i)
        return self.send(404, {"message": "Not Found"})


if __name__ == "__main__":
    print("mock GitHub on http://localhost:%d  repo=%s" % (PORT, ROOT))
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
