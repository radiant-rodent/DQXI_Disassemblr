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


_LOGCACHE = {}   # log path -> ((mtime, size), text, runs, tail): the board polls every 3 s, most logs never change


def log_info(log):
    """(text, attempt headers) of a task log, re-parsed only when the file changed."""
    if not log.exists():
        return "", []
    st = log.stat()
    key = (st.st_mtime_ns, st.st_size)
    hit = _LOGCACHE.get(log)
    if hit and hit[0] == key:
        return hit[1], hit[2]
    text = ANSI.sub("", log.read_text(encoding="utf-8", errors="replace"))
    runs = ATTEMPT.findall(text)
    _LOGCACHE[log] = (key, text, runs, None)
    return text, runs


def tail_of(log, text):
    hit = _LOGCACHE.get(log)
    if hit and hit[3] is not None:
        return hit[3]
    t = "\n".join(pretty(l) for l in text.splitlines()[-60:])
    if hit:
        _LOGCACHE[log] = hit[:3] + (t,)
    return t


def snapshot(open_ids=()):
    state = json.loads((ORC / "state.json").read_text()) if (ORC / "state.json").exists() else {}
    tasks = []
    for p in sorted((ORC / "tasks").glob("*.md")):
        tid, head = p.stem, p.read_text(encoding="utf-8").split("---")
        meta = dict(l.split(":", 1) for l in (head[1] if len(head) > 2 else "").strip().splitlines() if ":" in l)
        log = ORC / "logs" / f"{tid}.log"
        text, runs = log_info(log)
        if not runs and text[:200].lstrip().startswith('{"id":"user-turn'):
            # a Vibe worker (WSL) overwrote the attempt header: its journal lines start at byte 0
            pf = ORC / "logs" / f"{tid}.prompt.txt"
            when = time.ctime(pf.stat().st_mtime) if pf.exists() else ""
            runs = [("0", "vibe:ds-flash", when)]
        done = ORC / "done" / f"{tid}.md"
        st_ = board_state(state.get(tid, "pending"), done, log)
        want = st_ == "RUNNING" or tid in open_ids
        tasks.append({
            "id": tid, "lane": meta.get("lane", "").strip(), "after": meta.get("after", "").strip(),
            "state": board_state(state.get(tid, "pending"), done, log),
            "attempt": runs[-1][0] if runs else "", "model": runs[-1][1] if runs else "",
            "started": runs[-1][2] if runs else "",
            "tail": tail_of(log, text) if want else "",
            "report": done.read_text(encoding="utf-8", errors="replace")[:20000] if (want and done.exists()) else "",
            "has_report": done.exists(),
        })
    return {"tasks": tasks}


PAGE = r"""<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width">
<title>DQXI Workers</title><style>
:root{--bg:#f6f6f4;--fg:#1d1d1b;--card:#fff;--mut:#777;--line:#ddd;--log:#111;--logfg:#cfe8cf;--link:#1a5fb4}
@media(prefers-color-scheme:dark){:root{--bg:#161616;--fg:#e8e8e6;--card:#202020;--mut:#999;--line:#333;--link:#8ab4f8}}a{color:var(--link)}a:visited{color:var(--link)}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px system-ui}
h1{font-size:18px;margin:0 0 4px}.sub{color:var(--mut);margin-bottom:12px}
.sum span{margin-right:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:10px 12px}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;cursor:pointer}.id{font-weight:600;min-width:130px}
.b{padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600}
.RUNNING,.CLAIMED{background:#d9ecff;color:#0b5394}.DONE{background:#dff3df;color:#1e6b1e}.FAILED{background:#fbdcdc;color:#9b1c1c}.pending{background:#eee;color:#666}
.m{color:var(--mut);font-size:12px}.md{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:4px 14px;max-height:480px;overflow:auto;line-height:1.5}.md h1,.md h2,.md h3{margin:14px 0 6px}.md h1{font-size:17px}.md h2{font-size:15px}.md h3{font-size:14px}.md code{background:rgba(127,127,127,.18);padding:1px 4px;border-radius:3px;font-size:12.5px}.md pre{background:var(--log);color:var(--logfg);padding:8px;border-radius:6px;max-height:none;overflow:auto}.md pre code{background:none;padding:0}.md table{border-collapse:collapse;margin:8px 0}.md td,.md th{border:1px solid var(--line);padding:3px 8px;font-size:13px}.md blockquote{margin:6px 0;padding-left:10px;border-left:3px solid var(--line);color:var(--mut)}.md ul,.md ol{padding-left:22px}.md a{color:var(--link)}.bar{margin:8px 0;display:flex;gap:14px;align-items:center}.bar input[type=text],#q{padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);min-width:260px}.dd{position:relative}.ddb{font:13px system-ui;padding:5px 12px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);cursor:pointer}.ddb.act{border-color:#0b5394;background:#d9ecff;color:#0b5394}.ddm{display:none;position:absolute;z-index:10;top:34px;left:0;min-width:230px;background:var(--card);border:1px solid var(--line);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.25);padding:6px}.ddm.on{display:block}.ddm label{display:flex;gap:8px;align-items:center;padding:5px 8px;border-radius:5px;cursor:pointer}.ddm label:hover{background:rgba(127,127,127,.15)}.ddm .n{margin-left:auto;color:var(--mut);font-size:12px}.ddm hr{border:0;border-top:1px solid var(--line);margin:4px 0}.ddm a{display:inline-block;padding:3px 8px;font-size:12px;color:var(--link);cursor:pointer}.dbtn{margin-left:auto;font:12px system-ui;padding:2px 10px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--fg);cursor:pointer}.dbtn.on{background:#d9ecff;color:#0b5394}.desc{border-left:3px solid #0b5394}pre{background:var(--log);color:var(--logfg);padding:8px;border-radius:6px;max-height:420px;overflow:auto;font-size:12px;white-space:pre-wrap}
</style></head><body><h1>DQXI worker board</h1><div class=sub>Live · updates every 3 s · click a task to show its log/report · <a href="/progress/progress.html">game progress</a> · <a href="/progress/map.html">coverage map</a> · <a href="/progress/history.html">history</a></div>
<div class=sum id=sum></div>
<div class=bar><input id=q placeholder="Search id, lane, model..." oninput="render()">
<div class=dd id=dd><button class=ddb id=ddb onclick="ddt(event)"></button><div class=ddm id=ddm onclick="event.stopPropagation()"></div></div></div>
<div id=list></div><script>
const open=new Set(),dopen=new Set(),descs={};let D=[],last='',busy=false,sel;
try{sel=new Set(JSON.parse(localStorage.getItem('dqxiSel')||'null'))}catch(e){sel=new Set()}
if(!sel.size)sel=new Set(['RUNNING','STALLED','FAILED','CLAIMED','pending']);
const ALL=['RUNNING','STALLED','FAILED','CLAIMED','pending','DONE'];
const ORDER={RUNNING:0,STALLED:1,FAILED:2,CLAIMED:3,pending:4,DONE:5};
function counts(){const c={};D.forEach(t=>c[t.state]=(c[t.state]||0)+1);return c}
function render(){
 const c=counts(),q=document.getElementById('q').value.toLowerCase().trim();
 sum.innerHTML=Object.entries(c).sort((a,b)=>(ORDER[a[0]]??9)-(ORDER[b[0]]??9)).map(([k,v])=>`<span class="b ${k}">${k} ${v}</span>`).join('');
 const n=ALL.filter(k=>sel.has(k)).length;ddb.textContent='Status'+(n<ALL.length?' · '+n+' of '+ALL.length:' · all')+' ▾';ddb.className='ddb'+(n<ALL.length?' act':'');
 if(!ddm.dataset.built||ddm.classList.contains('on')===false){ddm.innerHTML=ALL.map(k=>`<label><input type=checkbox ${sel.has(k)?'checked':''} onchange="ddc('${k}',this.checked)"><span class="b ${k}">${k}</span><span class=n>${c[k]||0}</span></label>`).join('')+'<hr><a onclick="ddp(ALL)">All</a><a onclick="ddp([\'RUNNING\',\'STALLED\',\'FAILED\',\'CLAIMED\'])">Active</a><a onclick="ddp([\'RUNNING\'])">Running only</a><a onclick="ddp([\'pending\'])">Pending</a>';ddm.dataset.built=1}
 const keep={};document.querySelectorAll('[data-id]').forEach(p=>{keep[p.dataset.id+p.dataset.k]={top:p.scrollTop,end:p.scrollHeight-p.scrollTop-p.clientHeight<24}});
 const rows=D.filter(t=>sel.has(t.state)&&(!q||(t.id+' '+t.lane+' '+t.model+' '+t.state).toLowerCase().includes(q)))
  .sort((a,b)=>((ORDER[a.state]??9)-(ORDER[b.state]??9))||(a.state=='DONE'?(b.started||'').localeCompare(a.started||''):a.id.localeCompare(b.id)));
 const cap=300,more=rows.length>cap?rows.length-cap:0;
 list.innerHTML=rows.slice(0,cap).map(t=>`<div class=card><div class=row onclick="tog('${t.id}')"><span class=id>${t.id}</span>
<span class="b ${t.state}">${t.state}</span><span class=m>lane ${t.lane}${t.after?' · after '+t.after:''}</span>
<span class=m>${t.model?t.model+' · try '+t.attempt+' · '+t.started:''}</span>
<button class="dbtn${dopen.has(t.id)?' on':''}" onclick="event.stopPropagation();dsc('${t.id}')">Description</button></div>
${dopen.has(t.id)?`<div class="md desc" data-id="${t.id}" data-k=d>${descs[t.id]===undefined?'loading...':md(descs[t.id])}</div>`:''}
${open.has(t.id)||t.state=='RUNNING'?`<pre data-id="${t.id}" data-k=l>${esc(t.report||t.tail||(open.has(t.id)?'loading...':'(no output yet)'))}</pre>`:''}</div>`).join('')+(more?`<div class=m style="padding:8px">${more} more hidden: use the filter</div>`:'');
 document.querySelectorAll('[data-id]').forEach(p=>{const k=keep[p.dataset.id+p.dataset.k];
  if(p.dataset.k=='d'){p.scrollTop=k?k.top:0}else if(!k||k.end){p.scrollTop=p.scrollHeight}else{p.scrollTop=k.top}})}
function save(){try{localStorage.setItem('dqxiSel',JSON.stringify([...sel]))}catch(e){}}
function ddt(e){e.stopPropagation();ddm.classList.toggle('on')}
function ddc(k,on){on?sel.add(k):sel.delete(k);if(!sel.size)sel=new Set(ALL);save();renderKeepMenu()}
function ddp(a){sel=new Set(a);save();ddm.dataset.built='';ddm.classList.add('on');render();ddm.classList.add('on')}
function renderKeepMenu(){const was=ddm.classList.contains('on');ddm.classList.add('on');render();if(!was)ddm.classList.remove('on')}
document.addEventListener('click',()=>ddm.classList.remove('on'));
async function tick(){if(busy)return;busy=true;try{const txt=await (await fetch('/api?open='+encodeURIComponent([...open].join(',')))).text();
 if(txt!==last){last=txt;D=JSON.parse(txt).tasks;render()}}catch(e){sum.textContent='board offline: '+e}busy=false}
function tog(id){open.has(id)?open.delete(id):open.add(id);render();last='';tick()}
async function dsc(id){if(dopen.has(id)){dopen.delete(id);render();return}
 dopen.add(id);render();if(descs[id]===undefined){try{descs[id]=await (await fetch('/task?id='+encodeURIComponent(id))).text()}catch(e){descs[id]='could not load: '+e}render()}}
function inl(s){return esc(s).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>').replace(/(^|[^*\w])\*([^*\n]+)\*/g,'$1<i>$2</i>').replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g,'<a href="$2" target=_blank>$1</a>')}
function md(src){src=src.replace(/\r/g,'');const m=src.match(/^---\n([\s\S]*?)\n---\n?/);let head='';if(m){head='<p class=m>'+esc(m[1]).replace(/\n/g,' &middot; ')+'</p>';src=src.slice(m[0].length)}
const L=src.split('\n'),o=[];let i=0;
while(i<L.length){const l=L[i];let r;
if(/^```/.test(l)){const b=[];i++;while(i<L.length&&!/^```/.test(L[i]))b.push(L[i++]);i++;o.push('<pre><code>'+esc(b.join('\n'))+'</code></pre>');continue}
if(r=l.match(/^(#{1,4})\s+(.*)/)){o.push('<h'+Math.min(r[1].length,3)+'>'+inl(r[2])+'</h'+Math.min(r[1].length,3)+'>');i++;continue}
if(/^\s*(---+|\*\*\*+)\s*$/.test(l)){o.push('<hr>');i++;continue}
if(/^\|.*\|\s*$/.test(l)&&/^\|[\s:|-]+\|\s*$/.test(L[i+1]||'')){const rows=[];while(i<L.length&&/^\|.*\|\s*$/.test(L[i]))rows.push(L[i++]);
const cell=x=>x.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim());let t='<table><tr>'+cell(rows[0]).map(c=>'<th>'+inl(c)+'</th>').join('')+'</tr>';
rows.slice(2).forEach(x=>t+='<tr>'+cell(x).map(c=>'<td>'+inl(c)+'</td>').join('')+'</tr>');o.push(t+'</table>');continue}
if(/^\s*>/.test(l)){const b=[];while(i<L.length&&/^\s*>/.test(L[i]))b.push(L[i++].replace(/^\s*>\s?/,''));o.push('<blockquote>'+inl(b.join(' '))+'</blockquote>');continue}
if(/^\s*([-*]|\d+\.)\s+/.test(l)){const ord=/^\s*\d+\./.test(l),b=[];while(i<L.length&&/^\s*([-*]|\d+\.)\s+/.test(L[i]))b.push('<li>'+inl(L[i++].replace(/^\s*([-*]|\d+\.)\s+/,''))+'</li>');o.push((ord?'<ol>':'<ul>')+b.join('')+(ord?'</ol>':'</ul>'));continue}
if(!l.trim()){i++;continue}
const b=[];while(i<L.length&&L[i].trim()&&!/^(```|#|\s*>|\s*([-*]|\d+\.)\s+|\|)/.test(L[i]))b.push(L[i++]);if(!b.length){b.push(L[i++])}o.push('<p>'+inl(b.join(' '))+'</p>')}
return head+o.join('')}
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
        if self.path.startswith("/task?id="):  # the task description (the .md file, front matter included)
            tid = re.sub(r"[^A-Za-z0-9_.-]", "", unquote(self.path.split("=", 1)[1]))
            f = ORC / "tasks" / f"{tid}.md"
            body = (f.read_text(encoding="utf-8", errors="replace") if f.is_file() else "no such task").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers(); self.wfile.write(body); return
        body = json.dumps(snapshot(set(unquote(self.path.split("open=", 1)[1]).split(",")) if "open=" in self.path else ())).encode() if self.path.startswith("/api") else PAGE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json" if self.path.startswith("/api") else "text/html; charset=utf-8")
        self.end_headers(); self.wfile.write(body)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("Worker board on http://localhost:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), H).serve_forever()
