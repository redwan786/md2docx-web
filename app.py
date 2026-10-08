"""md2docx web app: upload a .md file, get a .docx file."""
import os
import re
import tempfile

import pypandoc
from flask import Flask, Response, jsonify, request
from waitress import serve

BASE = os.path.dirname(os.path.abspath(__file__))
LUA_FILTER = os.path.join(BASE, "latex-math.lua")
REFERENCE_DOC = os.path.join(BASE, "reference.docx")
MAX_MB = 50  # biggest upload allowed

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

# Logo (also used as the browser tab icon)
LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#4f7cff"/><stop offset="1" stop-color="#8b5cf6"/>
</linearGradient></defs>
<rect width="64" height="64" rx="16" fill="url(#g)"/>
<path d="M21 13h15l11 11v27a2 2 0 0 1-2 2H21a2 2 0 0 1-2-2V15a2 2 0 0 1 2-2z" fill="#fff"/>
<path d="M36 13v9a2 2 0 0 0 2 2h9z" fill="#c7d2fe"/>
<path d="M32 29v12m0 0-5.5-5.5M32 41l5.5-5.5" stroke="#4f7cff" stroke-width="3.6"
 fill="none" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M25 47h14" stroke="#8b5cf6" stroke-width="3.6" stroke-linecap="round"/>
</svg>"""

PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>md2docx · Markdown to Word</title>
<meta name="description" content="Convert Markdown notes to Word (.docx) with real equations and clean tables.">
<meta name="theme-color" content="#0b0d13">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="shortcut icon" href="/favicon.svg">
<style>
:root{
  --bg:#0b0d13; --card:#141824; --line:#252b3d; --text:#eceff7; --muted:#8c94ab;
  --brand:#4f7cff; --brand2:#8b5cf6; --ok:#34d399; --err:#fb7185;
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  min-height:100vh; color:var(--text);
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Nirmala UI",sans-serif;
  background:
    radial-gradient(900px 500px at 15% -10%, rgba(79,124,255,.22), transparent 60%),
    radial-gradient(800px 500px at 100% 0%, rgba(139,92,246,.20), transparent 55%),
    var(--bg);
  display:flex; flex-direction:column; align-items:center; padding:28px 16px 20px;
}
.brand{display:flex; align-items:center; gap:12px; margin:8px 0 26px}
.brand img{width:44px; height:44px; border-radius:12px; box-shadow:0 8px 24px rgba(79,124,255,.35)}
.brand span{font-size:22px; font-weight:700; letter-spacing:.2px}
.brand small{display:block; font-size:12px; font-weight:500; color:var(--muted); margin-top:1px}
main{width:100%; max-width:600px}
.card{
  background:linear-gradient(180deg, rgba(255,255,255,.03), rgba(255,255,255,0)), var(--card);
  border:1px solid var(--line); border-radius:20px; padding:28px;
  box-shadow:0 20px 60px rgba(0,0,0,.45);
}
h1{margin:0 0 8px; font-size:28px; line-height:1.2}
h1 em{font-style:normal; background:linear-gradient(90deg,var(--brand),var(--brand2));
  -webkit-background-clip:text; background-clip:text; color:transparent}
.lead{margin:0 0 22px; color:var(--muted); line-height:1.55; font-size:15px}
code{background:#1d2234; padding:2px 6px; border-radius:6px; font-size:.9em; color:#c9d4ff}

.drop{
  display:block; cursor:pointer; text-align:center; padding:34px 18px;
  border:2px dashed #34405f; border-radius:16px; background:rgba(79,124,255,.04);
  transition:.18s ease; outline:none;
}
.drop:hover,.drop:focus-visible,.drop.drag{border-color:var(--brand); background:rgba(79,124,255,.10); transform:translateY(-1px)}
.drop.has-file{border-style:solid; border-color:var(--ok); background:rgba(52,211,153,.07)}
.drop .ico{width:46px; height:46px; margin:0 auto 10px; color:var(--brand)}
.drop.has-file .ico{color:var(--ok)}
.drop b{display:block; font-size:16px; margin-bottom:4px; word-break:break-all}
.drop span{color:var(--muted); font-size:13.5px}
input[type=file]{display:none}

button{
  margin-top:16px; width:100%; border:0; cursor:pointer; color:#fff; font-size:16px; font-weight:600;
  padding:14px 18px; border-radius:12px; display:flex; align-items:center; justify-content:center; gap:10px;
  background:linear-gradient(90deg,var(--brand),var(--brand2)); transition:.18s ease;
  box-shadow:0 10px 28px rgba(79,124,255,.35);
}
button:hover:not(:disabled){transform:translateY(-1px); filter:brightness(1.07)}
button:disabled{opacity:.45; cursor:not-allowed; box-shadow:none}
.spin{width:18px; height:18px; border:3px solid rgba(255,255,255,.35); border-top-color:#fff;
  border-radius:50%; animation:sp .7s linear infinite; display:none}
.loading .spin{display:inline-block}
@keyframes sp{to{transform:rotate(360deg)}}

.msg{margin-top:14px; padding:12px 14px; border-radius:12px; font-size:14px; line-height:1.45; display:none}
.msg.err{display:block; background:rgba(251,113,133,.10); color:#fecdd3; border:1px solid rgba(251,113,133,.35)}
.msg.ok{display:block; background:rgba(52,211,153,.10); color:#bbf7d0; border:1px solid rgba(52,211,153,.35)}
.msg a{color:#fff; font-weight:600}

.feats{display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:18px}
.feat{background:rgba(255,255,255,.025); border:1px solid var(--line); border-radius:14px; padding:14px}
.feat i{font-style:normal; font-size:20px}
.feat b{display:block; margin:6px 0 2px; font-size:14px}
.feat p{margin:0; color:var(--muted); font-size:12.5px; line-height:1.4}
.note{margin:16px 2px 0; color:var(--muted); font-size:12.5px; text-align:center}
footer{margin-top:auto; padding-top:26px; color:#6a7390; font-size:12.5px; text-align:center}
footer a{color:#9fb2ff; text-decoration:none}
footer a:hover{text-decoration:underline}
@media (max-width:560px){
  .card{padding:20px} h1{font-size:23px} .feats{grid-template-columns:1fr}
}
</style></head>
<body>
  <div class="brand">
    <img src="/favicon.svg" alt="md2docx logo">
    <span>md2docx<small>Markdown → Word</small></span>
  </div>

  <main>
    <div class="card">
      <h1>Turn notes into a <em>Word file</em></h1>
      <p class="lead">Upload a Markdown (<code>.md</code>) file and get a clean <code>.docx</code> back.
        Math in <code>```latex</code> blocks becomes real Word equations.</p>

      <label class="drop" id="drop" tabindex="0" for="file">
        <svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>
          <path d="M14 3v5h5"/><path d="M12 17v-6m0 0-2.5 2.5M12 11l2.5 2.5"/>
        </svg>
        <b id="fname">Drop your .md file here</b>
        <span id="fhint">or click to choose · max __MAX_MB__ MB</span>
      </label>
      <input type="file" id="file" accept=".md,.markdown,.txt">

      <button id="go" disabled>
        <span class="spin"></span><span id="golabel">Convert to .docx</span>
      </button>
      <div id="msg" class="msg" role="status"></div>

      <div class="feats">
        <div class="feat"><i>▦</i><b>Clean tables</b><p>Borders and header row, ready for class notes.</p></div>
        <div class="feat"><i>∑</i><b>Real equations</b><p>Editable in Word, not pictures or code.</p></div>
        <div class="feat"><i>অ</i><b>Bangla ready</b><p>Bengali text stays correct and readable.</p></div>
      </div>
      <p class="note">Your file is not saved on the server. It is deleted right after converting.</p>
    </div>
  </main>

  <footer>Made by Redwan · <a href="https://github.com/redwan786/md2docx-web" target="_blank" rel="noopener">Source on GitHub</a></footer>

<script>
(function(){
  var MAX = __MAX_MB__ * 1024 * 1024;
  var $ = function(id){ return document.getElementById(id); };
  var drop=$("drop"), input=$("file"), btn=$("go"), msg=$("msg"),
      fname=$("fname"), fhint=$("fhint"), golabel=$("golabel");
  var file=null;

  function show(kind, html){ msg.className = "msg " + kind; msg.innerHTML = html; }
  function clearMsg(){ msg.className = "msg"; msg.innerHTML = ""; }
  function size(n){ return n < 1024*1024 ? (n/1024).toFixed(1)+" KB" : (n/1048576).toFixed(2)+" MB"; }

  function setFile(f){
    if(!f) return;
    if(!/\.(md|markdown|txt)$/i.test(f.name)){ show("err","Please choose a <b>.md</b> file."); return; }
    if(f.size > MAX){ show("err","This file is too big. Max size is __MAX_MB__ MB."); return; }
    file = f; clearMsg();
    drop.classList.add("has-file");
    fname.textContent = f.name;
    fhint.textContent = size(f.size) + " · click to change";
    btn.disabled = false;
  }

  input.addEventListener("change", function(){ setFile(input.files[0]); });
  ["dragenter","dragover"].forEach(function(t){
    drop.addEventListener(t, function(e){ e.preventDefault(); drop.classList.add("drag"); });
  });
  ["dragleave","drop"].forEach(function(t){
    drop.addEventListener(t, function(e){ e.preventDefault(); drop.classList.remove("drag"); });
  });
  drop.addEventListener("drop", function(e){ setFile(e.dataTransfer.files[0]); });
  drop.addEventListener("keydown", function(e){
    if(e.key==="Enter" || e.key===" "){ e.preventDefault(); input.click(); }
  });

  btn.addEventListener("click", async function(){
    if(!file) return;
    btn.disabled = true; btn.classList.add("loading"); golabel.textContent = "Converting…"; clearMsg();
    try{
      var fd = new FormData(); fd.append("file", file);
      var res = await fetch("/convert", {method:"POST", body:fd});
      if(!res.ok){
        var m = "Something went wrong. Please try again.";
        try{ var j = await res.json(); if(j && j.error) m = j.error; }catch(_){}
        throw new Error(m);
      }
      var blob = await res.blob();
      var cd = res.headers.get("Content-Disposition") || "";
      var mt = /filename="?([^";]+)"?/.exec(cd);
      var name = mt ? mt[1] : "converted.docx";
      var url = URL.createObjectURL(blob);
      var a = document.createElement("a");
      a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
      show("ok", "Done! <b>" + name.replace(/</g,"&lt;") + '</b> is downloading. <a href="' + url + '" download="' + name.replace(/"/g,"") + '">Download again</a>');
    }catch(err){
      show("err", String(err.message || err).replace(/</g,"&lt;"));
    }finally{
      btn.classList.remove("loading"); golabel.textContent = "Convert to .docx"; btn.disabled = false;
    }
  });
})();
</script>
</body></html>"""


@app.get("/")
def home():
    html = PAGE.replace("__MAX_MB__", str(MAX_MB))
    return Response(html, mimetype="text/html")


@app.get("/favicon.svg")
@app.get("/favicon.ico")
def favicon():
    return Response(LOGO_SVG, mimetype="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=86400"})


@app.get("/health")
def health():
    return "ok"


@app.post("/convert")
def convert():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(error="Please choose a file."), 400
    try:
        text = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return jsonify(error="The file must be UTF-8 text."), 400

    base = re.sub(r"[^\w\-]+", "_", os.path.splitext(f.filename)[0]).strip("_") or "note"
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.md")
        out = os.path.join(tmp, "out.docx")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            pypandoc.convert_file(
                src, "docx", format="markdown", outputfile=out,
                extra_args=[
                    "--sandbox",
                    "--lua-filter=" + LUA_FILTER,
                    "--reference-doc=" + REFERENCE_DOC,
                ],
            )
        except Exception as exc:  # pandoc failed
            app.logger.error("pandoc error: %s", exc)
            return jsonify(error="Could not convert this file. Please check your Markdown."), 500
        with open(out, "rb") as fh:
            data = fh.read()

    return Response(
        data,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="%s_converted.docx"' % base},
    )


@app.errorhandler(413)
def too_big(_):
    return jsonify(error="File is too big (max %d MB)." % MAX_MB), 413


if __name__ == "__main__":
    port = int(os.environ.get("SERVER_PORT") or os.environ.get("PORT") or 8080)
    print("md2docx listening on 0.0.0.0:%d" % port, flush=True)
    serve(app, host="0.0.0.0", port=port, threads=2)
