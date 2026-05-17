Local Image Search Web App

This small Flask app loads a JSONL file of image descriptions and serves a web UI to search and view matching images.

Setup

1. (Optional) Create a virtual environment and activate it:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Edit `app.py` if your `JSONL_PATH` or `IMAGE_FOLDER` are different from the defaults.

Run

```powershell
python app.py
```

Open http://localhost:5000 in your browser. Type a word like "baby" and press Search.

Notes

- The server expects the JSONL to contain at least one field with image filenames or paths (keys containing `image`, `file`, `url`, or values ending with image extensions). If your JSONL uses different keys, update the heuristics in `load_index()` in `app.py`.
- Images are served directly from the `IMAGE_FOLDER` path; make sure the filenames in the JSONL match the filenames in that folder (basename matching).
