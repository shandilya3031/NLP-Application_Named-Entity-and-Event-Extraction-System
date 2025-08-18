from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import hashlib
from werkzeug.utils import secure_filename
from extraction_rules import TextProcessor
from config import NEWS_ENTITY_TYPES, MAX_FILE_SIZE, ALLOWED_EXTENSIONS, CACHE_TIMEOUT
import time
import fitz  # PyMuPDF
import docx
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Initialize text processor
text_processor = TextProcessor()

# Simple in-memory cache
cache = {}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_cache_key(text, entity_types):
    """Generate cache key for text processing results"""
    content = text + str(sorted(entity_types) if entity_types else [])
    return hashlib.md5(content.encode()).hexdigest()

# def read_file_content(file_path):
#     """Read content from uploaded file"""
#     try:
#         with open(file_path, 'r', encoding='utf-8') as file:
#             return file.read()
#     except UnicodeDecodeError:
#         # Try with different encoding
#         with open(file_path, 'r', encoding='latin-1') as file:
#             return file.read()

# Replace the old read_file_content function in app.py with this one

def read_file_content(file_path):
    """Read content from uploaded file, handling TXT, PDF, and DOCX."""
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()
    
    try:
        if extension == '.pdf':
            # Use PyMuPDF to extract text from PDF
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text()
            return text
            
        elif extension == '.docx':
            # Use python-docx to extract text from DOCX
            doc = docx.Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return '\n'.join(full_text)
            
        else: # Default to reading as plain text (for .txt and others)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return f"Error: Could not read content from the file. It might be corrupted or in an unsupported format."

@app.route('/')
def index():
    """Main page route"""
    return render_template('index.html', entity_types=NEWS_ENTITY_TYPES)

@app.route('/api/extract', methods=['POST'])
def extract_entities():
    """API endpoint for entity and event extraction"""
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({'error': 'Empty text provided'}), 400
        
        selected_types = data.get('entity_types', [])
        extract_events = data.get('extract_events', True)
        
        # Check cache first
        cache_key = get_cache_key(text, selected_types)
        current_time = time.time()
        
        if cache_key in cache:
            cached_data, timestamp = cache[cache_key]
            if current_time - timestamp < CACHE_TIMEOUT:
                return jsonify(cached_data)
        
        # Process text
        start_time = time.time()
        results = text_processor.process_text(text, selected_types, extract_events)
        processing_time = time.time() - start_time
        
        # Add metadata
        results['metadata'] = {
            'processing_time': round(processing_time, 3),
            'timestamp': datetime.now().isoformat(),
            'text_length': len(text),
            'selected_types': selected_types
        }
        
        # Cache results
        cache[cache_key] = (results, current_time)
        
        # Clean old cache entries (simple cleanup)
        if len(cache) > 100:
            oldest_key = min(cache.keys(), key=lambda k: cache[k][1])
            del cache[oldest_key]
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': f'Processing error: {str(e)}'}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """API endpoint for file upload and processing"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        # Read file content
        content = read_file_content(filepath)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'content': content[:10000],  # Limit to first 10K chars for display
            'full_content': content,
            'size': len(content)
        })
    
    except Exception as e:
        return jsonify({'error': f'Upload error: {str(e)}'}), 500

@app.route('/api/export', methods=['POST'])
def export_results():
    """API endpoint for exporting extraction results"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        export_format = data.get('format', 'json').lower()
        results = data.get('results', {})
        
        if export_format == 'json':
            return jsonify(results)
        
        elif export_format == 'csv':
            # Convert to CSV format
            csv_content = "Type,Text,Start,End,Confidence,Context\n"
            
            for entity in results.get('entities', []):
                csv_content += f"{entity['type']},\"{entity['text']}\",{entity['start']},{entity['end']},{entity.get('confidence', 0)},\"{entity.get('context', '')}\"\n"
            
            for event in results.get('events', []):
                csv_content += f"{event['type']},\"{event['text']}\",{event['start']},{event['end']},{event.get('confidence', 0)},\"{event.get('context', '')}\"\n"
            
            return csv_content, 200, {'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=extraction_results.csv'}
        
        elif export_format == 'txt':
            # Convert to text report
            txt_content = "Named Entity and Event Extraction Report\n"
            txt_content += "=" * 50 + "\n\n"
            
            if 'metadata' in results:
                metadata = results['metadata']
                txt_content += f"Processing Time: {metadata.get('processing_time', 'N/A')} seconds\n"
                txt_content += f"Timestamp: {metadata.get('timestamp', 'N/A')}\n"
                txt_content += f"Text Length: {metadata.get('text_length', 'N/A')} characters\n\n"
            
            # Statistics
            stats = results.get('statistics', {})
            txt_content += f"Total Entities: {stats.get('total_entities', 0)}\n"
            txt_content += f"Total Events: {stats.get('total_events', 0)}\n\n"
            
            # Entity breakdown
            txt_content += "Entity Breakdown:\n"
            for entity_type, count in stats.get('entity_counts', {}).items():
                txt_content += f"  {entity_type}: {count}\n"
            
            txt_content += "\nEvent Breakdown:\n"
            for event_type, count in stats.get('event_counts', {}).items():
                txt_content += f"  {event_type}: {count}\n"
            
            txt_content += "\n" + "=" * 50 + "\n"
            txt_content += "Detailed Entities:\n\n"
            
            for entity in results.get('entities', []):
                txt_content += f"[{entity['type']}] {entity['text']} (Confidence: {entity.get('confidence', 0):.2f})\n"
                txt_content += f"  Position: {entity['start']}-{entity['end']}\n"
                txt_content += f"  Context: {entity.get('context', '')}\n\n"
            
            txt_content += "Detailed Events:\n\n"
            for event in results.get('events', []):
                txt_content += f"[{event['type']}] {event['text']} (Confidence: {event.get('confidence', 0):.2f})\n"
                txt_content += f"  Position: {event['start']}-{event['end']}\n"
                txt_content += f"  Context: {event.get('context', '')}\n"
                if 'attributes' in event:
                    for key, value in event['attributes'].items():
                        if value:
                            txt_content += f"  {key.title()}: {value}\n"
                txt_content += "\n"
            
            return txt_content, 200, {'Content-Type': 'text/plain', 'Content-Disposition': 'attachment; filename=extraction_report.txt'}
        
        else:
            return jsonify({'error': 'Unsupported export format'}), 400
    
    except Exception as e:
        return jsonify({'error': f'Export error: {str(e)}'}), 500

@app.route('/api/sample-text')
def get_sample_text():
    """API endpoint to get sample news text from file"""
    try:
        with open('data/sample_news.txt', 'r', encoding='utf-8') as f:
            sample_text = f.read()
        return jsonify({
            'text': sample_text.strip(),
            'title': 'Sample News Text'
        })
    except FileNotFoundError:
        return jsonify({'error': 'Sample text file not found.'}), 404

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
