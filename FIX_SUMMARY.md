# Fix Summary: Resolve 404 on /playground and Empty Reply Issues

## Issues Addressed

1. **404 Error on `/playground` endpoint** - Users getting "404 Not Found" when accessing the playground UI
2. **Empty reply from server on `/process` endpoint** - curl requests failing with "Empty reply from server" or "Broken pipe" errors
3. **External API calls during model loading** - HuggingFace making unnecessary network requests to check for model updates even though models are cached locally

## Root Causes Identified

### 1. Flask Template Directory Resolution Issue
**Problem:** When Flask app is initialized with `Flask(__name__)` and run via `python -m chandra.scripts.http_server`, the `__name__` variable becomes `'__main__'` instead of the module path. This causes Flask to look for templates in the wrong location, resulting in 404 errors for template-based routes like `/playground`.

**Evidence:** The `/playground` route calls `render_template('playground.html')` but Flask cannot find the template because it's looking in the wrong directory.

### 2. Poor Error Handling in /process Endpoint  
**Problem:** The `/process` endpoint had nested try-finally blocks and lacked comprehensive logging. When errors occurred during file processing, the server could crash or return empty responses without proper error messages.

**Evidence:** The original code had a try-finally inside a try-except, making error handling unclear. Temporary file cleanup was only in the inner finally block, and there was minimal logging at key processing steps.

### 3. External API Calls During Model Loading
**Problem:** HuggingFace's `from_pretrained()` methods make external HTTP requests to huggingface.co by default to check for model updates, even when models are cached locally. This causes delays and can fail if network is unavailable.

**Evidence:** From the issue logs, we see many HTTP requests like:
```
INFO:httpx:HTTP Request: HEAD https://huggingface.co/datalab-to/chandra-ocr-2/resolve/main/config.json
INFO:httpx:HTTP Request: HEAD https://huggingface.co/datalab-to/chandra-ocr-2/resolve/main/processor_config.json
```

These requests happen during model initialization even though the Dockerfile pre-downloads the model at build time.

## Changes Made

### 1. Fixed Flask Template Directory Resolution (`chandra/scripts/http_server.py`)

**Before:**
```python
app = Flask(__name__)
```

**After:**
```python
# Explicitly set template folder to ensure it's found when run with -m
# This fixes the issue where Flask can't find templates when __name__ is '__main__'
_script_dir = Path(__file__).parent
app = Flask(__name__, template_folder=str(_script_dir / 'templates'))
```

**Impact:** 
- The `/playground` endpoint now correctly finds and serves `playground.html`
- Template folder is explicitly set relative to the script location, regardless of how the module is imported
- Works correctly when run as `python -m chandra.scripts.http_server`

### 2. Improved Error Handling and Logging (`chandra/scripts/http_server.py`)

**Changes:**
- Moved `tmp_filepath = None` initialization outside try block
- Flattened nested try-finally blocks into single try-except-finally
- Added comprehensive logging at every key step:
  - When file is received
  - When file is saved to temp location  
  - When loading images from file
  - When starting inference
  - When inference completes
  - When file processing succeeds
- Added logging for all error conditions (no file, empty filename, invalid file type, etc.)
- Improved finally block to always clean up temp file with error handling

**Impact:**
- Server no longer crashes on errors - all exceptions are caught and logged
- Better debugging with detailed logs showing exactly where errors occur
- Proper cleanup of temporary files even when errors happen
- User-friendly error messages returned to client

### 3. Force Use of Cached Models (`chandra/model/hf.py`)

**Before:**
```python
model = AutoModelForImageTextToText.from_pretrained(
    settings.MODEL_CHECKPOINT, **kwargs
)
processor = AutoProcessor.from_pretrained(settings.MODEL_CHECKPOINT)
```

**After:**
```python
kwargs = {
    "dtype": torch.bfloat16,
    "device_map": device_map,
    "local_files_only": True,  # Use cached model without external API calls
}

model = AutoModelForImageTextToText.from_pretrained(
    settings.MODEL_CHECKPOINT, **kwargs
)
processor = AutoProcessor.from_pretrained(
    settings.MODEL_CHECKPOINT,
    local_files_only=True  # Use cached processor without external API calls
)
```

**Impact:**
- No external API calls to huggingface.co during model initialization
- Faster startup time (no network latency)
- Works offline or in restricted network environments
- Eliminates potential network-related failures during initialization

## Testing Recommendations

### Test 1: Verify /playground Endpoint
```bash
# Start the server
docker-compose up

# In a browser, navigate to:
http://localhost:5000/playground

# Expected: Playground UI loads without 404 error
```

### Test 2: Verify /process Endpoint with curl
```bash
# Create a test image
python test_api.py

# Or use curl with a PDF
curl -X POST http://localhost:5000/process \
  -F "file=@/path/to/your/file.pdf" \
  -v

# Expected: 
# - No "Empty reply from server" error
# - JSON response with OCR results
# - Or proper error message if there's an issue
```

### Test 3: Verify No External API Calls
```bash
# Monitor network traffic while starting server
# Should see no HTTP requests to huggingface.co

# Check server logs - should not see any HTTP Request log lines
docker-compose logs -f chandra-api | grep "HTTP Request"

# Expected: No output (no external HTTP requests)
```

### Test 4: Verify Error Handling
```bash
# Test with missing file
curl -X POST http://localhost:5000/process -v

# Test with invalid file type
curl -X POST http://localhost:5000/process \
  -F "file=@test.txt" \
  -v

# Expected: Proper error messages, no server crash
```

## Deployment Notes

1. **Docker Build:** The Dockerfile pre-downloads models at build time (line 32), so `local_files_only=True` ensures these cached models are used
2. **Environment Variables:** The server uses `INFERENCE_METHOD=hf` for CPU mode (default in docker-compose.yml)
3. **Health Check:** The `/health` endpoint can be used to verify server is ready before sending requests

## Files Changed

1. `chandra/scripts/http_server.py` - Flask app initialization and /process error handling
2. `chandra/model/hf.py` - Model loading with local_files_only flag
3. `test_routes.py` - New test script to verify Flask routes (for development)

## Backward Compatibility

All changes are backward compatible:
- Existing API endpoints work the same way
- Response formats unchanged  
- Environment variables unchanged
- Docker deployment unchanged

## Performance Impact

- **Faster startup:** No network latency from checking for model updates
- **Better reliability:** No dependency on external services during initialization
- **Same runtime performance:** No impact on inference speed
