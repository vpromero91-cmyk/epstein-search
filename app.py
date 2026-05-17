from flask import Flask, request, jsonify, render_template, Response, abort
import json
import os
from azure.storage.blob import BlobServiceClient

# =========================
# CONFIG
# =========================

AZURE_STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
CONTAINER_NAME = os.environ.get("AZURE_STORAGE_CONTAINER", "epfiles")

# Update these if your blob folders/names are different
IMAGE_PREFIX = os.environ.get("IMAGE_PREFIX", "images/")
JSONL_BLOB_NAME = os.environ.get(
    "JSONL_BLOB_NAME",
    "azure_image_descriptions.jsonl"
)

app = Flask(__name__, static_folder="static", template_folder="templates")

blob_service = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
container = blob_service.get_container_client(CONTAINER_NAME)


# =========================
# AZURE HELPERS
# =========================

def blob_exists(blob_name):
    try:
        container.get_blob_client(blob_name).get_blob_properties()
        return True
    except Exception:
        return False


def read_blob_text(blob_name):
    blob_client = container.get_blob_client(blob_name)
    data = blob_client.download_blob().readall()
    return data.decode("utf-8", errors="replace")


def find_image_blob(filename):
    """
    Finds the image in Azure Blob Storage.

    First tries:
        IMAGE_PREFIX + filename

    Then falls back to searching by basename.
    """
    filename = filename.replace("\\", "/").split("/")[-1]

    direct_blob = f"{IMAGE_PREFIX.rstrip('/')}/{filename}"

    if blob_exists(direct_blob):
        return direct_blob

    for blob in container.list_blobs(name_starts_with=IMAGE_PREFIX):
        if blob.name.replace("\\", "/").split("/")[-1] == filename:
            return blob.name

    return None


# =========================
# LOAD SEARCH INDEX
# =========================

def load_index():
    items = []

    try:
        text = read_blob_text(JSONL_BLOB_NAME)
    except Exception as e:
        print(f"Could not load JSONL blob: {JSONL_BLOB_NAME}")
        print(f"Error: {e}")
        return items

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        try:
            obj = json.loads(line)
        except Exception:
            continue

        image = None

        # Try to find an image-like field
        for k, v in obj.items():
            if isinstance(v, str) and any(s in k.lower() for s in ("image", "file", "url", "path")):
                image = v
                break

        # Fallback: look for values that look like filenames/paths
        if image is None:
            for v in obj.values():
                if isinstance(v, str) and (
                    v.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
                    or "\\" in v
                    or "/" in v
                ):
                    image = v
                    break

        # Find descriptive text
        desc = None
        for key in ("description", "caption", "alt", "text", "desc"):
            if key in obj and isinstance(obj[key], str):
                desc = obj[key]
                break

        if desc is None:
            strs = [v for v in obj.values() if isinstance(v, str)]
            if strs:
                desc = max(strs, key=len)

        visible_text_source = obj.get("visible_text")

        if isinstance(visible_text_source, list):
            visible_text = " ".join(str(x) for x in visible_text_source if isinstance(x, str))
        elif isinstance(visible_text_source, str):
            visible_text = visible_text_source
        else:
            visible_text = ""

        if image:
            image_name = image.replace("\\", "/").split("/")[-1]

            items.append({
                "image": image_name,
                "file_name": image,
                "description": desc or "",
                "visible_text": visible_text,
                "raw": obj,
            })

    print(f"Loaded {len(items)} indexed image records.")
    return items


INDEX = load_index()


# =========================
# ROUTES
# =========================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search():
    q = request.args.get("q", "").strip().lower()

    if not q:
        return jsonify({})

    search_description = request.args.get("search_description", "false").lower() == "true"
    search_visible_text = request.args.get("search_visible_text", "false").lower() == "true"

    if not (search_description or search_visible_text):
        return jsonify({})

    results = []

    for item in INDEX:
        matches = False

        if search_description and q in item.get("description", "").lower():
            matches = True

        if search_visible_text and q in item.get("visible_text", "").lower():
            matches = True

        if matches:
            results.append({
                "image": item["image"],
                "file_name": item.get("file_name", ""),
                "description": item.get("description", ""),
                "visible_text": item.get("visible_text", ""),
            })

    page = int(request.args.get("page", "1"))
    per_page = 10
    total = len(results)

    start = (page - 1) * per_page
    end = start + per_page
    paginated = results[start:end]

    return jsonify({
        "items": paginated,
        "page": page,
        "per_page": per_page,
        "total": total,
        "total_pages": (total + per_page - 1) // per_page,
    })


@app.route("/images/<path:filename>")
def images(filename):
    blob_name = find_image_blob(filename)

    if not blob_name:
        abort(404, description=f"Image not found: {filename}")

    blob_client = container.get_blob_client(blob_name)
    stream = blob_client.download_blob()
    data = stream.readall()

    content_type = "application/octet-stream"

    if filename.lower().endswith(".png"):
        content_type = "image/png"
    elif filename.lower().endswith((".jpg", ".jpeg")):
        content_type = "image/jpeg"
    elif filename.lower().endswith(".gif"):
        content_type = "image/gif"
    elif filename.lower().endswith(".webp"):
        content_type = "image/webp"

    return Response(data, mimetype=content_type)


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "container": CONTAINER_NAME,
        "jsonl_blob": JSONL_BLOB_NAME,
        "image_prefix": IMAGE_PREFIX,
        "index_count": len(INDEX),
    })


@app.route("/reload-index")
def reload_index():
    global INDEX
    INDEX = load_index()
    return jsonify({
        "status": "reloaded",
        "index_count": len(INDEX),
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
