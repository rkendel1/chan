#!/usr/bin/env python3
"""
Test script to verify the timeout mechanism logic works correctly.
This is a standalone test that doesn't require Flask or other dependencies.
"""
import time
import threading
from unittest.mock import Mock


class InferenceTimeoutError(Exception):
    """Raised when inference takes too long."""
    pass


# Note: This function is duplicated from http_server.py to make the test
# standalone and not require Flask or other HTTP server dependencies.
# Keep this in sync with the main implementation when making changes.
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
            print("Inference thread started")
            result_container['results'] = model.generate(batch, **kwargs)
            print(f"Inference thread completed with {len(result_container['results'])} results")
        except Exception as e:
            print(f"Inference thread encountered error: {str(e)}")
            result_container['error'] = e
    
    thread = threading.Thread(target=target)
    # Use daemon=True so the thread doesn't prevent process shutdown if it hangs.
    # This is acceptable because the HTTP request will timeout and return an error,
    # and any incomplete inference work can be safely discarded.
    thread.daemon = True
    thread.start()
    thread.join(timeout=timeout_seconds)
    
    if thread.is_alive():
        print(f"Inference timed out after {timeout_seconds} seconds")
        raise InferenceTimeoutError(f"Inference took longer than {timeout_seconds} seconds")
    
    if result_container['error'] is not None:
        raise result_container['error']
    
    return result_container['results']


def test_timeout_mechanism():
    """Test that the timeout mechanism correctly times out long-running inference."""
    print("Testing timeout mechanism...")
    
    # Create a mock model that hangs
    mock_model = Mock()
    
    def slow_generate(batch, **kwargs):
        """Simulate a slow/hanging generate call."""
        print("Mock generate called, sleeping for 20 seconds...")
        time.sleep(20)
        return [Mock(markdown="test", html="test", token_count=10, page_box=[0,0,100,100], chunks=[], images={})]
    
    mock_model.generate = slow_generate
    
    # Create a mock batch
    mock_batch = [Mock()]
    
    # Test 1: Should timeout after 2 seconds
    print("\nTest 1: Testing timeout (should timeout after 2 seconds)...")
    start = time.time()
    try:
        results = run_inference_with_timeout(mock_model, mock_batch, timeout_seconds=2)
        print("✗ FAILED: Should have raised InferenceTimeoutError")
        return False
    except InferenceTimeoutError as e:
        elapsed = time.time() - start
        print(f"✓ PASSED: Correctly timed out after {elapsed:.1f} seconds")
        print(f"  Error message: {str(e)}")
        # Allow wide tolerance (1.5-4.0s) for thread scheduling delays on CI systems
        # and under heavy load. The key is that it times out, not the exact timing.
        if elapsed < 1.5 or elapsed > 4.0:
            print(f"✗ FAILED: Timeout took {elapsed:.1f}s, expected ~2s (allowed 1.5-4.0s)")
            return False
    
    # Test 2: Fast generate should complete successfully
    print("\nTest 2: Testing fast inference (should complete successfully)...")
    
    def fast_generate(batch, **kwargs):
        """Simulate a fast generate call."""
        print("Fast generate called, returning immediately...")
        return [Mock(markdown="test", html="test", token_count=10, page_box=[0,0,100,100], chunks=[], images={})]
    
    mock_model.generate = fast_generate
    
    try:
        results = run_inference_with_timeout(mock_model, mock_batch, timeout_seconds=5)
        print(f"✓ PASSED: Fast inference completed successfully, got {len(results)} results")
    except Exception as e:
        print(f"✗ FAILED: Fast inference should not timeout: {str(e)}")
        return False
    
    # Test 3: Exception in inference should be propagated
    print("\nTest 3: Testing exception propagation (ValueError)...")
    
    def error_generate(batch, **kwargs):
        """Simulate a generate call that raises an exception."""
        print("Error generate called, raising ValueError...")
        raise ValueError("Test error from generate")
    
    mock_model.generate = error_generate
    
    try:
        results = run_inference_with_timeout(mock_model, mock_batch, timeout_seconds=5)
        print("✗ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✓ PASSED: ValueError correctly propagated: {str(e)}")
    except Exception as e:
        print(f"✗ FAILED: Wrong exception type: {type(e).__name__}: {str(e)}")
        return False
    
    # Test 4: Different exception types should be propagated
    print("\nTest 4: Testing exception propagation (RuntimeError)...")
    
    def runtime_error_generate(batch, **kwargs):
        """Simulate a generate call that raises a RuntimeError."""
        print("Error generate called, raising RuntimeError...")
        raise RuntimeError("Test runtime error from generate")
    
    mock_model.generate = runtime_error_generate
    
    try:
        results = run_inference_with_timeout(mock_model, mock_batch, timeout_seconds=5)
        print("✗ FAILED: Should have raised RuntimeError")
        return False
    except RuntimeError as e:
        print(f"✓ PASSED: RuntimeError correctly propagated: {str(e)}")
    except Exception as e:
        print(f"✗ FAILED: Wrong exception type: {type(e).__name__}: {str(e)}")
        return False
    
    return True


if __name__ == '__main__':
    import sys
    
    print("="*60)
    print("Testing Inference Timeout Mechanism")
    print("="*60)
    
    success = test_timeout_mechanism()
    
    print("\n" + "="*60)
    if success:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed")
        sys.exit(1)
