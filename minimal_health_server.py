"""
Minimal health server for immediate Azure App Service compatibility.
Starts instantly and responds to health checks while main app initializes.
"""
import os
import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class MinimalHealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that always returns healthy status."""
    
    def do_GET(self):
        """Handle GET requests with immediate healthy response."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        response = {
            "status": "healthy",
            "service": "NewsRagnarok Crawler",
            "timestamp": time.time(),
            "version": "1.0.0",
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "port": os.environ.get("PORT", "8000")
        }
        
        self.wfile.write(json.dumps(response, indent=2).encode())
    
    def do_HEAD(self):
        """Handle HEAD requests from Azure health checks."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests if needed."""
        self.do_GET()
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs to reduce noise."""
        pass

def start_minimal_health_server():
    """Start minimal health server for Azure App Service."""
    port = int(os.environ.get('PORT', 8000))
    
    print(f"🚀 Starting minimal health server on port {port}")
    print(f"⏰ Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Create server with socket reuse
        server = HTTPServer(('0.0.0.0', port), MinimalHealthHandler)
        server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        print(f"✅ Minimal health server ready on http://0.0.0.0:{port}")
        print(f"🌐 Health endpoint: http://localhost:{port}/")
        print(f"💚 Ready for Azure health checks")
        
        # Start serving forever
        server.serve_forever()
        
    except Exception as e:
        print(f"❌ Failed to start minimal health server: {e}")
        exit(1)

if __name__ == "__main__":
    import socket
    start_minimal_health_server()