from flask import Flask, request, jsonify, send_from_directory, render_template
import json, os
from pathlib import Path

# Update these paths if your files are in different locations
IMAGE_FOLDER = r"D:\Epstein\_extracted_large_page_images"
JSONL_PATH = r"D:\Epstein\Azure\Vision Output\Large Images\General Descriptions\azure_image_descriptions.jsonl"

app = Flask(__name__, static_folder='static', template_folder='templates')


def load_index():
    items = []
    p = Path(JSONL_PATH)
    if not p.exists():
        print(f"JSONL not found: {JSONL_PATH}")
        return items
    with p.open(encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            image = None
            # try to find an image-like field
            for k, v in obj.items():
                if isinstance(v, str) and any(s in k.lower() for s in ('image', 'file', 'url', 'path')):
                    image = v
                    break
            # fallback: look for values that look like filenames
            if image is None:
                for v in obj.values():
                    if isinstance(v, str) and (v.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) or ('\\' in v) or ('/' in v)):
                        image = v
                        break
            # find a descriptive text
            desc = None
            for key in ('description', 'caption', 'alt', 'text', 'desc'):
                if key in obj and isinstance(obj[key], str):
                    desc = obj[key]
                    break
            if desc is None:
                # pick longest string value as a fallback
                strs = [v for v in obj.values() if isinstance(v, str)]
                if strs:
                    desc = max(strs, key=len)
            visible_text_source = obj.get('visible_text')
            if isinstance(visible_text_source, list):
                visible_text = ' '.join(str(x) for x in visible_text_source if isinstance(x, str))
            elif isinstance(visible_text_source, str):
                visible_text = visible_text_source
            else:
                visible_text = ''
            if image:
                image_name = os.path.basename(image)
                items.append({
                    'image': image_name,
                    'file_name': image,
                    'description': desc or '',
                    'visible_text': visible_text,
                    'raw': obj,
                })
    return items


INDEX = load_index()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search')
def search():
    q = request.args.get('q', '').strip().lower()
    if not q:
        return jsonify({})
    search_description = request.args.get('search_description', 'false').lower() == 'true'
    search_visible_text = request.args.get('search_visible_text', 'false').lower() == 'true'
    if not (search_description or search_visible_text):
        return jsonify({})
    results = []
    for item in INDEX:
        matches = False
        if search_description and q in item['description'].lower():
            matches = True
        if search_visible_text and q in (item.get('visible_text') or '').lower():
            matches = True
        if matches:
            results.append({
                'image': item['image'],
                'file_name': item.get('file_name', ''),
                'description': item['description'],
                'visible_text': item.get('visible_text', ''),
            })
    
    page = int(request.args.get('page', '1'))
    per_page = 10
    total = len(results)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = results[start:end]
    
    return jsonify({
        'items': paginated,
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': (total + per_page - 1) // per_page,
    })


@app.route('/images/<path:filename>')
def images(filename):
    safe_dir = os.path.normpath(IMAGE_FOLDER)
    return send_from_directory(safe_dir, filename)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
