"""Live worker board: python orchestration/live.py  ->  http://localhost:8765"""
import json, re, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ORC = Path(__file__).resolve().parent
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
ATTEMPT = re.compile(r"===== attempt (\d+) model (\S+) (.+?) =====")


def pretty(line):
    # agy --output-format stream-json writes one JSON event per line; show the readable part
    if not line.startswith("{"):
        return line
    try:
        ev = json.loads(line)
    except ValueError:
        return line

    def find(o):
        if isinstance(o, dict):
            for k in ("text", "content", "message", "command", "name", "path", "status"):
                if isinstance(o.get(k), str) and o[k].strip():
                    return o[k]
            o = list(o.values())
        if isinstance(o, list):
            for v in o:
                r = find(v)
                if r:
                    return r
        return ""
    kind = ev.get("type") or ev.get("event") or "event"
    return f"[{kind}] {find(ev)[:300]}"


def board_state(recorded, done, log):
    # state.json can be stale when two dispatchers share it, so trust the files first
    if done.exists():
        return "DONE"
    if (done.parent.parent / "claims" / done.stem).exists():
        return "CLAIMED"  # being done by hand, e.g. in Antigravity
    # the dispatcher's state decides "running"; a recent log alone is just a stopped run
    # (e.g. one that ended in KeyboardInterrupt)
    if recorded == "RUNNING":
        return "RUNNING" if log.exists() and time.time() - log.stat().st_mtime < 4 * 3600 else "STALLED"
    return "pending" if recorded == "DONE" else recorded


def snapshot():
    state = json.loads((ORC / "state.json").read_text()) if (ORC / "state.json").exists() else {}
    tasks = []
    for p in sorted((ORC / "tasks").glob("*.md")):
        tid, head = p.stem, p.read_text(encoding="utf-8").split("---")
        meta = dict(l.split(":", 1) for l in (head[1] if len(head) > 2 else "").strip().splitlines() if ":" in l)
        log = ORC / "logs" / f"{tid}.log"
        text = ANSI.sub("", log.read_text(encoding="utf-8", errors="replace")) if log.exists() else ""
        runs = ATTEMPT.findall(text)
        if not runs and text[:200].lstrip().startswith('{"id":"user-turn'):
            # a Vibe worker (WSL) overwrote the attempt header: its journal lines start at byte 0
            pf = ORC / "logs" / f"{tid}.prompt.txt"
            when = time.ctime(pf.stat().st_mtime) if pf.exists() else ""
            runs = [("0", "vibe:ds-flash", when)]
        done = ORC / "done" / f"{tid}.md"
        tasks.append({
            "id": tid, "lane": meta.get("lane", "").strip(), "after": meta.get("after", "").strip(),
            "state": board_state(state.get(tid, "pending"), done, log),
            "attempt": runs[-1][0] if runs else "", "model": runs[-1][1] if runs else "",
            "started": runs[-1][2] if runs else "",
            "tail": "\n".join(pretty(l) for l in text.splitlines()[-60:]),
            "report": done.read_text(encoding="utf-8", errors="replace") if done.exists() else "",
        })
    return {"tasks": tasks}


PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width">
<title>DQXI Workers</title><style>
:root{--bg:#f6f6f4;--fg:#1d1d1b;--card:#fff;--mut:#777;--line:#ddd;--log:#111;--logfg:#cfe8cf}
@media(prefers-color-scheme:dark){:root{--bg:#161616;--fg:#e8e8e6;--card:#202020;--mut:#999;--line:#333}}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui}
h1{font-size:18px;margin:0 0 4px}.sub{color:var(--mut);margin-bottom:12px}
.sum span{margin-right:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:10px 12px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;cursor:pointer}.id{font-weight:600;min-width:130px}
.b{padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600}
.RUNNING,.CLAIMED{background:#d9ecff;color:#0b5394}.DONE{background:#dff3df;color:#1e6b1e}.FAILED{background:#fbdcdc;color:#9b1c1c}.pending{background:#eee;color:#666}
.m{color:var(--mut);font-size:12px}pre{background:var(--log);color:var(--logfg);padding:8px;border-radius:6px;max-height:420px;overflow:auto;font-size:12px;white-space:pre-wrap}
</style></head><body><h1>DQXI worker board</h1><div class=sub>Live · updates every 3 s · click a task to show its log/report · <a href="/progress/progress.html">game progress</a> · <a href="/progress/map.html">coverage map</a> · <a href="/progress/history.html">history</a></div>
<div class=sum id=sum></div><div id=list></div><script>
const open=new Set();
async function tick(){try{const d=await (await fetch('/api')).json();const c={};
d.tasks.forEach(t=>c[t.state]=(c[t.state]||0)+1);
sum.innerHTML=Object.entries(c).map(([k,v])=>`<span class="b ${k}">${k} ${v}</span>`).join('');
const order={RUNNING:0,FAILED:1,pending:2,DONE:3};d.tasks.sort((a,b)=>order[a.state]-order[b.state]);
list.innerHTML=d.tasks.map(t=>`<div class=card><div class=row onclick="tog('${t.id}')"><span class=id>${t.id}</span>
<span class="b ${t.state}">${t.state}</span><span class=m>lane ${t.lane}${t.after?' · after '+t.after:''}</span>
<span class=m>${t.model?t.model+' · try '+t.attempt+' · '+t.started:''}</span></div>
${open.has(t.id)||t.state=='RUNNING'?`<pre>${esc(t.report||t.tail||'(no output yet)')}</pre>`:''}</div>`).join('');
document.querySelectorAll('pre').forEach(p=>p.scrollTop=p.scrollHeight)}catch(e){sum.textContent='board offline: '+e}}
function tog(id){open.has(id)?open.delete(id):open.add(id);tick()}
function esc(s){return s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
tick();setInterval(tick,3000)</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/decomp/readable/"):
            # Read-only view of the human-readable C so map.html cells can open in a tab.
            root = (ORC.parent / "decomp" / "readable").resolve()
            rel = unquote(self.path[len("/decomp/readable/"):].split("?")[0].split("#")[0])
            f = (root / rel).resolve()
            if not f.is_file():
                # files get renamed when names are merged; every name ends in _<address>.c
                m = re.search(r"_([0-9a-fA-F]{8})\.c$", rel)
                hits = sorted(root.glob(f"*/*_{m.group(1).lower()}.c")) if m else []
                f = hits[0].resolve() if hits else f
            if f.is_file() and root in f.parents:
                body = f.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(404, "readable C file not found")
            return
        if self.path.startswith("/progress/"):  # static AnyPS5-style progress pages
            f = (ORC.parent / self.path.lstrip("/").split("?")[0]).resolve()
            if f.is_file() and (ORC.parent / "progress") in f.parents:
                self.send_response(200)
                self.send_header("Content-Type", {".svg": "image/svg+xml", ".json": "application/json"}.get(f.suffix, "text/html; charset=utf-8"))
                self.end_headers(); self.wfile.write(f.read_bytes()); return
        body = json.dumps(snapshot()).encode() if self.path.startswith("/api") else PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if self.path.startswith("/api") else "text/html; charset=utf-8")
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("Worker board on http://localhost:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
