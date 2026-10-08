"""md2docx web app: upload a .md file, get a .docx file."""
import os
import re
import tempfile

import pypandoc
from flask import Flask, Response, request
from waitress import serve

BASE = os.path.dirname(os.path.abspath(__file__))
LUA_FILTER = os.path.join(BASE, "latex-math.lua")
REFERENCE_DOC = os.path.join(BASE, "reference.docx")
MAX_MB = 2  # biggest upload allowed

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>md2docx</title>
<style>
 body{font-family:system-ui,sans-serif;background:#0d0f14;color:#e8eaf0;display:flex;
      justify-content:center;padding:40px 16px}
 .box{max-width:520px;width:100%%;background:#171a22;border-radius:14px;padding:28px}
 h1{margin-top:0} p,li{color:#aab0c0;line-height:1.5}
 input[type=file]{width:100%%;margin:16px 0;color:#e8eaf0}
 button{background:#3b6cff;color:#fff;border:0;border-radius:8px;padding:12px 20px;
        font-size:16px;cursor:pointer;width:100%%}
 .err{background:#3a1d22;color:#ffb4b4;padding:10px;border-radius:8px}
 small{color:#7d8498}
</style></head><body><div class="box">
<h1>md2docx</h1>
<p>Upload a Markdown (<code>.md</code>) file. You get a Word (<code>.docx</code>) file back.
Math in <code>```latex</code> blocks becomes real Word equations.</p>
%s
<form method="post" action="/convert" enctype="multipart/form-data">
 <input type="file" name="file" accept=".md,.markdown,.txt" required>
 <button type="submit">Convert to .docx</button>
</form>
<p><small>Max file size: %d MB. Files are not saved on the server.</small></p>
</div></body></html>"""


def page(error=""):
    msg = '<p class="err">%s</p>' % error if error else ""
    return Response(PAGE % (msg, MAX_MB), mimetype="text/html")


@app.get("/")
def home():
    return page()


@app.get("/health")
def health():
    return "ok"


@app.post("/convert")
def convert():
    f = request.files.get("file")
    if not f or not f.filename:
        return page("Please choose a file."), 400
    try:
        text = f.read().decode("utf-8")
    except UnicodeDecodeError:
        return page("The file must be UTF-8 text."), 400

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
            return page("Could not convert this file. Check your Markdown."), 500
        with open(out, "rb") as fh:
            data = fh.read()

    return Response(
        data,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": 'attachment; filename="%s_converted.docx"' % base},
    )


@app.errorhandler(413)
def too_big(_):
    return page("File is too big (max %d MB)." % MAX_MB), 413


if __name__ == "__main__":
    port = int(os.environ.get("SERVER_PORT") or os.environ.get("PORT") or 8080)
    print("md2docx listening on 0.0.0.0:%d" % port, flush=True)
    serve(app, host="0.0.0.0", port=port, threads=2)
