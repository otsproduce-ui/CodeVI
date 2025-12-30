"""
CodeVI Backend - Main entry point
Flask application with blueprints and configuration
"""
from flask import Flask
from flask_cors import CORS
from app.routes import routes_bp, init_services
from config import Config
import os

def create_app():
    """Initialize Flask app with blueprints and config."""
    app = Flask(__name__, static_folder='../frontend', static_url_path='')
    app.config.from_object(Config)

    # CORS security – allow only frontend origins
    CORS(app, origins=app.config["ALLOWED_ORIGINS"])

    # Initialize services
    init_services(app)

    # Register blueprints
    app.register_blueprint(routes_bp, url_prefix="/api/v1")
    
    # Serve frontend files (must be after API routes)
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        # Don't serve API routes as static files
        if path.startswith('api/'):
            from flask import abort
            abort(404)
        try:
            return app.send_static_file(path)
        except:
            # If file not found, try to serve index.html (for client-side routing)
            return app.send_static_file('index.html')

    @app.route("/health", methods=["GET"])
    def health_legacy():
        """Legacy health endpoint for backward compatibility"""
        from app.routes import search_service
        from flask import jsonify
        
        is_indexed = False
        file_count = 0
        if search_service:
            is_indexed = bool(search_service.is_indexed())
            file_count = int(search_service.file_count())
        
        return jsonify({
            "ok": True,
            "status": "healthy",
            "indexed": is_indexed,
            "file_count": file_count
        })

    @app.route("/scan", methods=["POST"])
    def scan_legacy():
        """Legacy scan endpoint for backward compatibility"""
        from app.routes import scan
        return scan()

    @app.route("/search", methods=["POST"])
    def search_legacy():
        """Legacy search endpoint for backward compatibility"""
        from app.routes import search
        return search()

    @app.route("/api/graph", methods=["GET"])
    def graph_legacy():
        """Legacy graph endpoint for backward compatibility"""
        from app.routes import graph
        return graph()

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
