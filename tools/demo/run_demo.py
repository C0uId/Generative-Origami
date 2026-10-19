from __future__ import annotations
import json, mimetypes, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).resolve().parents[2]
ENGINE=ROOT/"src"
sys.path.insert(0,str(ENGINE))
from generative_origami.pipeline import generate

APP=ROOT/"app"/"demo"
RUNTIME=ROOT/"runtime_outputs"

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, data, ctype="application/json; charset=utf-8"):
        b=data if isinstance(data,bytes) else data.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type",ctype)
        self.send_header("Content-Length",str(len(b)))
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u=urlparse(self.path)
        if u.path=="/api/health":
            return self._send(200,json.dumps({"ok":True,"service":"generative-origami-mvp"}))
        if u.path=="/api/generate":
            q=parse_qs(u.query).get("q",[""])[0].strip()
            if not q:
                return self._send(400,json.dumps({"error":"missing q"},ensure_ascii=False))
            r=generate(q,RUNTIME)
            # Inline preview for the browser.
            p=Path(r["artifact_dir"])/"preview.svg"
            r["preview_svg_inline"]=p.read_text(encoding="utf-8")
            return self._send(200,json.dumps(r,ensure_ascii=False))
        if u.path in {"/","/index.html"}:
            return self._send(200,(APP/"index.html").read_text(encoding="utf-8"),"text/html; charset=utf-8")
        return self._send(404,"not found","text/plain; charset=utf-8")

if __name__=="__main__":
    addr=("127.0.0.1",8765)
    print(f"Open http://{addr[0]}:{addr[1]}")
    ThreadingHTTPServer(addr,Handler).serve_forever()