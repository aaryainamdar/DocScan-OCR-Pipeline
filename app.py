import os
import uuid
import json
import time
from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from preprocessor import preprocess_image
from ocr_engine import extract_text
from postprocessor import clean_and_format
from pdf_exporter import export_to_pdf

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROCESSED_FOLDER'] = 'processed'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload and process a document image."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Use: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

    # Save uploaded file
    doc_id = str(uuid.uuid4())
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{doc_id}.{ext}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Get processing options from form
    ocr_engine = request.form.get('ocr_engine', 'tesseract')
    lang = request.form.get('language', 'eng')
    enhance = request.form.get('enhance', 'true').lower() == 'true'

    start_time = time.time()

    try:
        # Step 1: Preprocess
        preprocessed_path, preprocessing_stats = preprocess_image(
            filepath,
            app.config['PROCESSED_FOLDER'],
            doc_id,
            enhance=enhance
        )

        # Step 2: OCR
        raw_text, ocr_confidence = extract_text(
            preprocessed_path,
            engine=ocr_engine,
            lang=lang
        )

        # Step 3: Post-process
        structured_output = clean_and_format(raw_text)

        processing_time = round(time.time() - start_time, 2)

        result = {
            'doc_id': doc_id,
            'status': 'success',
            'processing_time_s': processing_time,
            'preprocessing': preprocessing_stats,
            'ocr': {
                'engine': ocr_engine,
                'language': lang,
                'confidence': ocr_confidence,
                'raw_text': raw_text,
            },
            'output': structured_output
        }

        # Cache result
        result_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{doc_id}_result.json")
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': str(e), 'doc_id': doc_id}), 500


@app.route('/api/result/<doc_id>', methods=['GET'])
def get_result(doc_id):
    """Retrieve cached result by document ID."""
    result_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{doc_id}_result.json")
    if not os.path.exists(result_path):
        return jsonify({'error': 'Result not found'}), 404
    with open(result_path) as f:
        return jsonify(json.load(f))


@app.route('/api/export/<doc_id>/json', methods=['GET'])
def export_json(doc_id):
    """Export result as JSON file."""
    result_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{doc_id}_result.json")
    if not os.path.exists(result_path):
        return jsonify({'error': 'Result not found'}), 404
    return send_file(result_path, as_attachment=True, download_name=f"doc_{doc_id[:8]}.json")


@app.route('/api/export/<doc_id>/pdf', methods=['GET'])
def export_pdf(doc_id):
    """Export extracted text as formatted PDF."""
    result_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{doc_id}_result.json")
    if not os.path.exists(result_path):
        return jsonify({'error': 'Result not found'}), 404

    with open(result_path) as f:
        result = json.load(f)

    pdf_path = export_to_pdf(result, app.config['PROCESSED_FOLDER'], doc_id)
    return send_file(pdf_path, as_attachment=True, download_name=f"doc_{doc_id[:8]}.pdf")


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': '1.0.0'})


if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('processed', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)
