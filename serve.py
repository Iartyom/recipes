#!/usr/bin/env python3
"""Local mode: serve the site on http://127.0.0.1:8770 and let the "add" button save directly.

POST /api/add | /api/save | /api/delete → recipes.json → rebuild index.html → git commit (+ push if a remote
exists). The browser can't do this alone: a static page can't write files or fetch other sites (CORS).
Stdlib only.
"""
import http.server
import json
import pathlib
import subprocess
import sys
import webbrowser

import add_recipe
import build_html

ROOT = pathlib.Path(__file__).resolve().parent
PORT = 8770


def git_save(message):
    """Commit the change; push only when a remote is configured. Git failures never lose the saved data."""
    def run(*a):
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    run("add", "recipes.json", "index.html")
    if run("commit", "-m", message).returncode != 0:
        return "לא נשמר ב-git"
    if run("remote").stdout.strip():
        return "נשמר ונדחף ל-GitHub" if run("push", "-q").returncode == 0 else "נשמר ב-git (הדחיפה נכשלה)"
    return "נשמר ב-git (אין remote עדיין)"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def do_POST(self):
        """/api/add (raw URL/text), /api/save (recipe JSON with id), /api/delete ({"id"})."""
        if self.path not in ("/api/add", "/api/save", "/api/delete"):
            return self.send_error(404)
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0)).decode("utf-8")
        try:
            data = add_recipe.load()
            if self.path == "/api/add":
                rec = add_recipe.add(add_recipe.parse_input(raw), data)
                label, rid = f"מתכון: {rec['title']}", rec["id"]
            elif self.path == "/api/save":
                rec = add_recipe.update(json.loads(raw), data)
                label, rid = f"עריכת מתכון: {rec['title']}", rec["id"]
            else:
                rid = json.loads(raw)["id"]
                add_recipe.delete(rid, data)
                label, rid = f"מחיקת מתכון: {rid}", ""
            add_recipe.save(data)
            out = {"ok": True, "id": rid, "git": git_save(label)}
        except Exception as e:  # report parse/network failures to the page instead of a bare 500
            out = {"ok": False, "error": str(e)}
        body = json.dumps(out, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    build_html.build()
    url = f"http://127.0.0.1:{PORT}/"
    print(f"🍲 {url}  (Ctrl+C לעצירה)")
    webbrowser.open(url)
    # Bound to 127.0.0.1 only: the add endpoint must not be reachable from the network.
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
