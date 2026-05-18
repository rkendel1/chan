"""
HTTP server for Chandra OCR that accepts file uploads via POST requests.
Processes images and PDFs and returns OCR results as JSON.
"""
import io
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename

from chandra.input import load_file
from chandra.model import InferenceManager
from chandra.model.schema import BatchInputItem

# Explicitly set template folder to ensure it's found when run with -m
# This fixes the issue where Flask can't find templates when __name__ is '__main__'
_script_dir = Path(__file__).parent
app = Flask(__name__, template_folder=str(_script_dir / 'templates'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# Ensure logs are flushed immediately
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(line_buffering=True)

# Configure upload settings
ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp', '.tiff', '.bmp'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Global model instance with thread lock for initialization
model: Optional[InferenceManager] = None
model_lock = threading.Lock()
model_initializing = False  # Track if model is currently initializing


# Timeout exception for inference
class InferenceTimeoutError(Exception):
    """Raised when inference takes too long."""
    pass


def run_inference_with_timeout(model, batch, timeout_seconds=600, **kwargs):
    """
    Run model inference with a timeout.
    
    Args:
        model: The InferenceManager instance
        batch: Batch of items to process
        timeout_seconds: Maximum time to wait (default 10 minutes)
        **kwargs: Additional arguments for generate()
    
    Returns:
        Results from model.generate()
    
    Raises:
        InferenceTimeoutError: If inference takes longer than timeout_seconds
    """
    result_container = {'results': None, 'error': None}
    
    def target():
        try:
            logger.info("Inference thread started")
            result_container['results'] = model.generate(batch, **kwargs)
            logger.info(f"Inference thread completed with {len(result_container['results'])} results")
        except Exception as e:
            logger.error(f"Inference thread encountered error: {str(e)}", exc_info=True)
            result_container['error'] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        logger.error(f"Inference timed out after {timeout_seconds} seconds")
        raise InferenceTimeoutError(f"Inference took longer than {timeout_seconds} seconds")
    
    if result_container['error'] is not None:
        raise result_container['error']
    
    return result_container['results']


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def initialize_model(method: str = None):
    """Initialize the inference model with thread safety."""
    global model, model_initializing
    
    # Use lock to ensure thread-safe initialization
    with model_lock:
        if model is None and not model_initializing:
            # Set flag immediately to prevent race condition
            model_initializing = True
    
    # If we set the flag, do the initialization outside the lock
    if model_initializing and model is None:
        try:
            # Get method from environment or default to vllm
            if method is None:
                method = os.environ.get('INFERENCE_METHOD', 'vllm')
            logger.info(f"Initializing model with method: {method}")
            temp_model = InferenceManager(method=method)
            
            # Set model and clear flag atomically
            with model_lock:
                model = temp_model
                model_initializing = False
            logger.info("Model initialized successfully")
        except Exception as e:
            # Clear flag on error
            with model_lock:
                model_initializing = False
            logger.error(f"Model initialization failed: {e}")
            raise
    
    return model


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'model_initializing': model_initializing
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
    tmp_filepath = None
    try:
        logger.info("Received request to /process endpoint")
        
        # Check if model is initialized or initializing
        if model is None:
            if model_initializing:
                logger.warning("Model is still initializing")
                return jsonify({
                    'error': 'Model is still initializing. Please wait and try again in a few moments.',
                    'status': 'initializing'
                }), 503
            else:
                logger.error("Model not initialized")
                return jsonify({
                    'error': 'Model not initialized. Server may have failed to start properly.'
                }), 503
        
        # Check if file is present
        if 'file' not in request.files:
            logger.warning("No file provided in request")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            logger.warning("Empty filename provided")
            return jsonify({'error': 'Empty filename'}), 400
        
        if not allowed_file(file.filename):
            logger.warning(f"File type not allowed: {file.filename}")
            return jsonify({
                'error': f'File type not allowed. Supported types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        logger.info(f"Processing file: {file.filename}")
        
        # Get optional parameters
        page_range = request.form.get('page_range')
        include_images = request.form.get('include_images', 'true').lower() == 'true'
        include_headers_footers = request.form.get('include_headers_footers', 'false').lower() == 'true'
        max_output_tokens = request.form.get('max_output_tokens')
        
        if max_output_tokens:
            max_output_tokens = int(max_output_tokens)
        
        # Sanitize filename to prevent path traversal
        safe_name = secure_filename(file.filename)
        file_extension = Path(safe_name).suffix.lower()
        
        # Verify the extension is in allowed list (additional security check)
        if file_extension not in ALLOWED_EXTENSIONS:
            logger.warning(f"File extension not allowed: {file_extension}")
            return jsonify({
                'error': f'File type not allowed. Supported types: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Save file to temporary location with sanitized extension
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            file.save(tmp_file.name)
            tmp_filepath = tmp_file.name
        
        logger.info(f"Saved uploaded file to: {tmp_filepath}")
        
        # Load images from file
        config = {'page_range': page_range} if page_range else {}
        logger.info(f"Loading images from file with config: {config}")
        images = load_file(tmp_filepath, config)
        logger.info(f"Loaded {len(images)} image(s) from file")
        
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
        logger.info(f"Starting inference on {len(batch)} page(s)")
        try:
            # Use timeout wrapper to prevent hanging
            try:
                inference_timeout = int(os.environ.get('INFERENCE_TIMEOUT', 600))  # Default 10 minutes
            except (ValueError, TypeError):
                logger.warning("Invalid INFERENCE_TIMEOUT value, using default of 600 seconds")
                inference_timeout = 600
            
            logger.info(f"Using inference timeout of {inference_timeout} seconds")
            results = run_inference_with_timeout(model, batch, timeout_seconds=inference_timeout, **generate_kwargs)
            logger.info(f"Inference completed successfully, got {len(results)} result(s)")
        except InferenceTimeoutError as e:
            logger.error(f"Inference timed out: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Processing timed out after {inference_timeout} seconds. The document may be too complex or large.'
            }), 504
        except Exception as e:
            logger.error(f"Inference failed: {str(e)}", exc_info=True)
            raise  # Re-raise to be caught by outer exception handler
        
        # Format response
        logger.info("Formatting response...")
        pages = []
        for page_num, result in enumerate(results):
            logger.debug(f"Formatting page {page_num}")
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
        
        logger.info(f"Formatted {len(pages)} page(s)")
        response = {
            'success': True,
            'filename': secure_filename(file.filename),
            'num_pages': len(results),
            'pages': pages
        }
        
        logger.info(f"Successfully processed {file.filename}, returning response")
        return jsonify(response)
    
    except Exception as e:
        # Log the error internally with full traceback
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        # Return a user-friendly error message
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing the file. Please check the file format and try again.'
        }), 500
    
    finally:
        # Always clean up temporary file
        if tmp_filepath and os.path.exists(tmp_filepath):
            try:
                os.unlink(tmp_filepath)
                logger.info(f"Cleaned up temporary file: {tmp_filepath}")
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary file: {cleanup_error}")


@app.route('/', methods=['GET'])
def index():
    """Root endpoint with API information."""
    return jsonify({
        'name': 'Chandra OCR HTTP API',
        'version': '0.2.0',
        'endpoints': {
            '/health': 'GET - Health check',
            '/process': 'POST - Process document (multipart/form-data with file field)',
            '/playground': 'GET - Interactive playground UI',
            '/': 'GET - API information'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'max_file_size_mb': MAX_CONTENT_LENGTH / (1024 * 1024)
    })


@app.route('/playground', methods=['GET'])
def playground():
    """Serve the interactive playground UI."""
    return render_template('playground.html')


def main():
    """Main entry point for the HTTP server."""
    # Get configuration from environment
    host = os.environ.get('HTTP_HOST', '0.0.0.0')
    port = int(os.environ.get('HTTP_PORT', '5000'))
    debug = os.environ.get('HTTP_DEBUG', 'false').lower() == 'true'
    method = os.environ.get('INFERENCE_METHOD', 'vllm')
    
    # Initialize model before starting server
    logger.info("Starting Chandra OCR HTTP Server...")
    initialize_model(method)
    
    logger.info(f"Server starting on {host}:{port}")
    logger.info(f"Inference method: {method}")
    logger.info(f"Supported file types: {', '.join(ALLOWED_EXTENSIONS)}")
    logger.info(f"Max file size: {MAX_CONTENT_LENGTH / (1024 * 1024):.1f}MB")
    
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    main()
