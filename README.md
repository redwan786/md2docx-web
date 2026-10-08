# md2docx-web

A small web app. Upload a Markdown (`.md`) file and download a Word (`.docx`) file.

It turns math in ```latex blocks into real Word equations and uses `reference.docx` for the look (tables, headings, fonts).

## Files

| File | What it does |
|------|--------------|
| `app.py` | The web app (Flask + Waitress). |
| `requirements.txt` | Python packages. `pypandoc_binary` brings its own Pandoc, so you do not install Pandoc by hand. |
| `latex-math.lua` | Pandoc filter for ```latex blocks. |
| `reference.docx` | Word style template. |

## Run on your own computer

```
pip install -r requirements.txt
python app.py
```

Open <http://localhost:8080>.

## Deploy on Botkeep (from GitHub)

1. Push this folder to a GitHub repository.
2. In Botkeep, click **Create server** and choose **Import from GitHub**.
3. Pick the repository and the `main` branch.
4. Choose **Python** and set the start command to: `python app.py`
5. Give the server about **512 MB RAM** and **600 MB storage** (Pandoc alone is about 155 MB).
6. Start the server and watch the **Console**. You should see `md2docx listening on 0.0.0.0:...`.
7. Open **Domains** and add an HTTPS route to your server, then open the link.

The app reads the port from `SERVER_PORT` (or `PORT`). No secrets are needed.

## Notes

- Max upload size is 2 MB. Change `MAX_MB` in `app.py` if you need more.
- Uploaded files are not saved. They live in a temporary folder only while converting.
- If the first start is slow, it is installing packages. Wait for the console to finish.

## License

MIT.
