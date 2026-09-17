#!/usr/bin/env python3
"""edge_sub: token-protected subscription reverse proxy."""
from __future__ import annotations
import http.server, socketserver, urllib.parse, urllib.request, sys, os, subprocess, threading, hmac, hashlib, base64

HOST   = os.environ.get("EDGE_SUB_HOST", "0.0.0.0")
PORT   = int(os.environ.get("EDGE_SUB_PORT", "18080"))
_TF    = os.environ.get("EDGE_SUB_TF",  "/etc/edge/sub_token")
BACK   = os.environ.get("EDGE_SUB_BACKEND", "http://127.0.0.1:25500")
SCRIPT = "/opt/edge-sub/mihomo.py"

_lk = threading.Lock()
_a = None

def _lt():
    global _a
    if _a is None:
        with open(_TF) as f:
            _a = f.read().strip()
    return _a

ENABLED_NODES = [
    ("ss2022", "/etc/edge/ss2022_uri"),
    ("reality", "/etc/edge/reality_uri"),
    ("hy2", "/etc/edge/hy2_uri"),
]

def _get_uris() -> list[str]:
    uris = []
    for tag, p in ENABLED_NODES:
        if os.path.exists(p):
            try:
                with open(p) as f:
                    u = f.read().strip()
                    if u:
                        uris.append(u)
            except Exception as e:
                sys.stderr.write(f"[edge_sub] failed to read {p}: {e}\n")
    return uris

def _ct(p):
    if not p:
        return False
    return hmac.compare_digest(p, _lt())

def _fs(uri, target="singbox"):
    qs = urllib.parse.urlencode({"target": target, "url": uri, "list": "false", "new_name": "true"})
    req = urllib.request.Request(BACK + "/sub?" + qs)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "text/plain;charset=utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "text/plain;charset=utf-8")
    except Exception as e:
        return 502, f"backend error: {e}".encode(), "text/plain;charset=utf-8"

def _post_sb(body, c):
    """singbox 后处理: 把第一个 selector/urltest 的 tag 改成 'Proxy',同步引用。"""
    import json as _json
    try:
        doc = _json.loads(body)
    except Exception as e:
        sys.stderr.write(f"[edge_sub] _post_sb parse fail: {e}\n")
        return body, c
    if not isinstance(doc, dict) or "outbounds" not in doc:
        return body, c
    ob = doc["outbounds"]
    target_obj = None
    for o in ob:
        if o.get("type") in ("selector", "urltest"):
            target_obj = o
            break
    if target_obj is None:
        return body, c
    old_tag = target_obj.get("tag", "")
    new_tag = "Proxy"
    if old_tag == new_tag:
        return body, c
    target_obj["tag"] = new_tag
    for o in ob:
        arr = o.get("outbounds")
        if isinstance(arr, list):
            o["outbounds"] = [new_tag if x == old_tag else x for x in arr]
    rf = doc.get("route", {}).get("final")
    if rf == old_tag:
        doc["route"]["final"] = new_tag
    new_body = _json.dumps(doc, ensure_ascii=False).encode("utf-8")
    sys.stderr.write(f"[edge_sub] _post_sb renamed {old_tag!r} -> {new_tag!r}\n")
    return new_body, "application/json;charset=utf-8"

def _fm(uris: list[str]):
    r = subprocess.run([sys.executable, SCRIPT] + uris, capture_output=True, timeout=10)
    if r.returncode != 0:
        return 500, b"mihomo script error:\n" + (r.stderr or b""), "text/plain;charset=utf-8"
    return 200, r.stdout or b"", "text/yaml;charset=utf-8"

USAGE = (
    "edge_sub  --  active\n"
    "Endpoints:\n"
    "  GET /healthz\n"
    "  GET /dbg\n"
    "  GET /whoami  (server token sha256[:12] — 对比客户端期望 token 的 sha256)\n"
    "  GET /sub?token=[REDACTED]&target=singbox  (sing-box JSON, full rules)\n"
    "  GET /sub?token=[REDACTED]&target=clash    (Clash.Meta YAML via subconverter)\n"
    "  GET /sub?token=[REDACTED]&target=mihomo   (Clash.Meta YAML, direct generator)\n"
)

class H(http.server.BaseHTTPRequestHandler):
    server_version = "edge_sub/1.0"
    def log_message(self, fmt, *args):
        sys.stderr.write("[edge_sub] %s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, status, body, ctype):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def _send_debug(self):
        import json as _json
        info = {
            "method": self.command,
            "path": self.path,
            "raw_request_line": self.raw_requestline.decode("latin1", "replace").rstrip(),
            "headers": dict(self.headers.items()),
            "client": self.address_string(),
        }
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        tk = (qs.get("token") or [""])[0]
        info["parsed"] = {
            "path": u.path,
            "query_keys": sorted(qs.keys()),
            "token_len": len(tk),
            "token_sha256_12": hashlib.sha256(tk.encode()).hexdigest()[:12] if tk else "",
            "target": (qs.get("target") or [""])[0].lower(),
        }
        st = _lt()
        info["server"] = {
            "token_len": len(st),
            "token_sha256_12": hashlib.sha256(st.encode()).hexdigest()[:12],
        }
        body = _json.dumps(info, indent=2, ensure_ascii=False).encode()
        return self._send(200, body, "application/json;charset=utf-8")

    def _send_whoami(self):
        import json as _json
        st = _lt()
        body = _json.dumps({
            "ok": True,
            "server_token_len": len(st),
            "server_token_sha256_12": hashlib.sha256(st.encode()).hexdigest()[:12],
            "note": "把 client 期望 token 做 sha256 取前 12 位,跟 server_token_sha256_12 对比,一致=同 token,不一致=token 已变更/损坏",
        }, ensure_ascii=False).encode()
        return self._send(200, body, "application/json;charset=utf-8")

    def _check_token(self):
        u = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(u.query)
        tk = (qs.get("token") or [""])[0]
        if not tk:
            sys.stderr.write(f"[edge_sub] no token from {self.address_string()}\n")
            return (403, b"missing token\n", "text/plain;charset=utf-8")
        tk_sha = hashlib.sha256(tk.encode()).hexdigest()[:12]
        st_sha = hashlib.sha256(_lt().encode()).hexdigest()[:12]
        if not _ct(tk):
            sys.stderr.write(f"[edge_sub] bad token (len={len(tk)}, sha256[:12]={tk_sha}) from {self.address_string()} — server sha256[:12]={st_sha}\n")
            return (403, b"bad token\n", "text/plain;charset=utf-8")
        sys.stderr.write(f"[edge_sub] token OK (len={len(tk)}, sha256[:12]={tk_sha}) from {self.address_string()}\n")
        return None

    def do_GET(self):
        with _lk:
            u = urllib.parse.urlparse(self.path)

            if u.path == "/healthz":
                return self._send(200, b"ok\n", "text/plain;charset=utf-8")
            if u.path == "/dbg":
                return self._send_debug()
            if u.path == "/whoami":
                return self._send_whoami()
            if u.path == "/":
                return self._send(200, USAGE.encode(), "text/plain;charset=utf-8")

            r = self._check_token()
            if r is not None:
                return self._send(*r)

            uris = _get_uris()
            if not uris:
                return self._send(500, b"server misconfigured (no URI)\n", "text/plain;charset=utf-8")

            qs = urllib.parse.parse_qs(u.query)
            target = ""
            for k, v in qs.items():
                if k.strip().lower() == "target" and v:
                    target = urllib.parse.unquote(v[0]).strip().lower()
                    break
            if target == "singbox":
                s, body, c = _fs("|".join(uris), target="singbox")
                if s == 200:
                    body, c = _post_sb(body, c)
                return self._send(s, body, c)
            elif target in ("clash", "mihomo", "meta"):
                s, body, c = _fm(uris)
                return self._send(s, body, c)
            elif target in ("", "base64", "v2rayn", "raw", "b64"):
                b64 = base64.b64encode(chr(10).join(uris).encode("utf-8")) + bytes([10])
                return self._send(200, b64, "text/plain;charset=utf-8")
            else:
                return self._send(400, b"bad target: choose singbox | clash/mihomo | base64/v2rayn" + bytes([10]), "text/plain;charset=utf-8")
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def main():
    srv = S((HOST, PORT), H)
    st = _lt()
    sys.stderr.write("[edge_sub] listening on %s:%s, backend=%s, token_len=%d, token_sha256_12=%s\n" % (
        HOST, PORT, BACK, len(st), hashlib.sha256(st.encode()).hexdigest()[:12]))
    sys.stderr.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
