#!/usr/bin/env python3
"""
Test script to verify Flask routes are properly registered.
"""
import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

def test_routes():
    """Test that all routes are properly registered."""
    print("Testing Flask routes registration...")
    
    # Import the Flask app
    from chandra.scripts import http_server
    
    # Get the Flask app
    app = http_server.app
    
    print(f"\nFlask app: {app}")
    print(f"Flask root path: {app.root_path}")
    print(f"Flask template folder: {app.template_folder}")
    
    # Check if template folder exists
    template_path = Path(app.root_path) / app.template_folder
    print(f"\nTemplate folder path: {template_path}")
    print(f"Template folder exists: {template_path.exists()}")
    
    if template_path.exists():
        print(f"Template folder contents: {list(template_path.iterdir())}")
        
        # Check if playground.html exists
        playground_html = template_path / 'playground.html'
        print(f"\nplayground.html exists: {playground_html.exists()}")
        if playground_html.exists():
            print(f"playground.html size: {playground_html.stat().st_size} bytes")
    
    # List all registered routes
    print("\n" + "="*60)
    print("Registered routes:")
    print("="*60)
    
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
            'path': str(rule)
        })
    
    # Sort by path
    routes.sort(key=lambda x: x['path'])
    
    for route in routes:
        print(f"{route['methods']:10s} {route['path']:20s} -> {route['endpoint']}")
    
    # Check for specific routes
    print("\n" + "="*60)
    print("Route verification:")
    print("="*60)
    
    expected_routes = [
        ('/', 'index'),
        ('/health', 'health'),
        ('/playground', 'playground'),
        ('/process', 'process_file'),
    ]
    
    all_good = True
    for path, endpoint in expected_routes:
        # Check if route exists
        found = any(route['path'] == path and route['endpoint'] == endpoint for route in routes)
        status = "✓" if found else "✗"
        print(f"{status} {path:20s} -> {endpoint}")
        if not found:
            all_good = False
    
    print("\n" + "="*60)
    if all_good:
        print("✓ All routes are properly registered!")
        return 0
    else:
        print("✗ Some routes are missing!")
        return 1


if __name__ == '__main__':
    try:
        sys.exit(test_routes())
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
