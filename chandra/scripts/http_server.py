"""
HTTP server for Chandra OCR that accepts file uploads via POST requests.
Processes images and PDFs and returns OCR results as JSON.
"""
import io
import os
import tempfile
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

from chandra.input import load_file
from chandra.model import InferenceManager
from chandra.model.schema import BatchInputItem

app = Flask(__name__)

# Configure upload settings
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.tiff', '.bmp'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Global model instance
model: Optional[InferenceManager] = None


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def initialize_model(method: str = None):
    """Initialize the inference model."""
    global model
    if model is None:
        # Get method from environment or default to vllm
        if method is None:
            method = os.environ.get('INFERENCE_METHOD', 'vllm')
        print(f"Initializing model with method: {method}")
        model = InferenceManager(method=method)
        print("Model initialized successfully")
    return model


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })


@app.route('/process', methods=['POST'])
def process_file():
    """
    Process an uploaded file and return OCR results.
    
    Expected request:
        - Multipart form data with 'file' field containing the document
        - Optional form fields:
            - page_range: Page range for PDFs (e.g., '1-5,7,9-12')
            - include_images: Whether to include images in output (default: true)
            - include_headers_footers: Whether to include headers/footers (default: false)
            - max_output_tokens: Max tokens per page
    
    Returns:
        JSON response with OCR results for all pages
    """
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'File type not allowed. Supported types: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    try:
        # Get optional parameters
        page_range = request.form.get('page_range')
        include_images = request.form.get('include_images', 'true').lower() == 'true'
        include_headers_footers = request.form.get('include_headers_footers', 'false').lower() == 'true'
        max_output_tokens = request.form.get('max_output_tokens')
        
        if max_output_tokens:
            max_output_tokens = int(max_output_tokens)
        
        # Save file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
            file.save(tmp_file.name)
            tmp_filepath = tmp_file.name
        
        try:
            # Load images from file
            config = {'page_range': page_range} if page_range else {}
            images = load_file(tmp_filepath, config)
            
            # Create batch input items
            batch = [
                BatchInputItem(image=img, prompt_type="ocr_layout")
                for img in images
            ]
            
            # Build kwargs for generate
            generate_kwargs = {
                'include_images': include_images,
                'include_headers_footers': include_headers_footers,
            }
            
            if max_output_tokens is not None:
                generate_kwargs['max_output_tokens'] = max_output_tokens
            
            # Run inference
            results = model.generate(batch, **generate_kwargs)
            
            # Format response
            pages = []
            for page_num, result in enumerate(results):
                page_data = {
                    'page_num': page_num,
                    'markdown': result.markdown,
                    'html': result.html,
                    'token_count': result.token_count,
                    'page_box': result.page_box,
                    'num_chunks': len(result.chunks),
                    'num_images': len(result.images),
                }
                
                # Add image names if images were extracted
                if result.images:
                    page_data['image_names'] = list(result.images.keys())
                
                pages.append(page_data)
            
            response = {
                'success': True,
                'filename': secure_filename(file.filename),
                'num_pages': len(results),
                'pages': pages
            }
            
            return jsonify(response)
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_filepath):
                os.unlink(tmp_filepath)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information."""
    return jsonify({
        'name': 'Chandra OCR HTTP API',
        'version': '0.2.0',
        'endpoints': {
            '/health': 'GET - Health check',
            '/process': 'POST - Process document (multipart/form-data with file field)',
            '/': 'GET - API information'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_CONTENT_LENGTH / (1024 * 1024)
    })


def main():
    """Main entry point for the HTTP server."""
    # Get configuration from environment
    host = os.environ.get('HTTP_HOST', '0.0.0.0')
    port = int(os.environ.get('HTTP_PORT', '5000'))
    debug = os.environ.get('HTTP_DEBUG', 'false').lower() == 'true'
    method = os.environ.get('INFERENCE_METHOD', 'vllm')
    
    # Initialize model before starting server
    print("Starting Chandra OCR HTTP Server...")
    initialize_model(method)
    
    print(f"Server starting on {host}:{port}")
    print(f"Inference method: {method}")
    print(f"Supported file types: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f"Max file size: {MAX_CONTENT_LENGTH / (1024 * 1024):.1f}MB")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
