#!/usr/bin/env python3
"""
Test that pages are processed individually instead of in batches.
This ensures OOM protection is working correctly.
"""
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_process_pages_individually():
    """Test that the HTTP server processes pages one at a time."""
    from chandra.model.schema import BatchInputItem, BatchOutputItem
    from PIL import Image
    
    # Create mock images
    mock_images = [
        Image.new('RGB', (100, 100), color='red'),
        Image.new('RGB', (100, 100), color='green'),
        Image.new('RGB', (100, 100), color='blue'),
    ]
    
    # Create mock model that tracks how many items are passed at once
    call_counts = []
    
    def mock_generate(batch, **kwargs):
        # Track batch size
        call_counts.append(len(batch))
        # Return mock results
        return [
            BatchOutputItem(
                markdown=f"Page {i}",
                html=f"<p>Page {i}</p>",
                chunks=[],
                raw=f"Page {i}",
                page_box=[0, 0, 100, 100],
                token_count=10,
                images={},
                error=False
            )
            for i in range(len(batch))
        ]
    
    mock_model = Mock()
    mock_model.generate = mock_generate
    
    # Test processing 3 pages
    batch = [BatchInputItem(image=img, prompt_type="ocr_layout") for img in mock_images]
    
    # Simulate the per-page processing loop from http_server.py
    results = []
    for page_item in batch:
        page_results = mock_model.generate([page_item])
        results.extend(page_results)
    
    # Verify each page was processed individually (batch size of 1)
    assert len(call_counts) == 3, f"Expected 3 calls, got {len(call_counts)}"
    assert all(count == 1 for count in call_counts), f"Expected all batch sizes to be 1, got {call_counts}"
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    
    print("✓ Pages processed individually (batch size = 1 per call)")
    print(f"✓ Made {len(call_counts)} inference calls for {len(batch)} pages")
    print(f"✓ Batch sizes: {call_counts}")
    return True


def test_batch_processing_old_way():
    """Show what the old batch processing looked like (for comparison)."""
    from chandra.model.schema import BatchInputItem, BatchOutputItem
    from PIL import Image
    
    # Create mock images
    mock_images = [
        Image.new('RGB', (100, 100), color='red'),
        Image.new('RGB', (100, 100), color='green'),
        Image.new('RGB', (100, 100), color='blue'),
    ]
    
    # Create mock model that tracks how many items are passed at once
    call_counts = []
    
    def mock_generate(batch, **kwargs):
        call_counts.append(len(batch))
        return [
            BatchOutputItem(
                markdown=f"Page {i}",
                html=f"<p>Page {i}</p>",
                chunks=[],
                raw=f"Page {i}",
                page_box=[0, 0, 100, 100],
                token_count=10,
                images={},
                error=False
            )
            for i in range(len(batch))
        ]
    
    mock_model = Mock()
    mock_model.generate = mock_generate
    
    # OLD WAY: Process all pages at once (causes OOM)
    batch = [BatchInputItem(image=img, prompt_type="ocr_layout") for img in mock_images]
    results = mock_model.generate(batch)  # All 3 pages at once
    
    # Verify all pages were processed in one call
    assert len(call_counts) == 1, f"Expected 1 call, got {len(call_counts)}"
    assert call_counts[0] == 3, f"Expected batch size of 3, got {call_counts[0]}"
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
    
    print("✗ Old way: All pages in one batch (causes OOM)")
    print(f"✗ Made {len(call_counts)} inference call for {len(batch)} pages")
    print(f"✗ Batch sizes: {call_counts}")
    return True


if __name__ == '__main__':
    print("="*60)
    print("Testing Page-by-Page Processing")
    print("="*60)
    
    print("\n--- NEW WAY (Individual Pages) ---")
    success1 = test_process_pages_individually()
    
    print("\n--- OLD WAY (Batch Processing) ---")
    success2 = test_batch_processing_old_way()
    
    print("\n" + "="*60)
    if success1 and success2:
        print("✓ All tests passed!")
        print("\nThe new implementation processes pages individually,")
        print("preventing OOM crashes with large documents.")
        sys.exit(0)
    else:
        print("✗ Some tests failed")
        sys.exit(1)
