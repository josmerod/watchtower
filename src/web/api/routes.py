"""REST API Routes for Watchtower."""

import json
from functools import wraps
from pathlib import Path
from flask import Blueprint, jsonify, request, abort

from src.config.settings import get_settings

api_bp = Blueprint("api", __name__, url_prefix="/api")

def require_api_key(f):
    """Decorator to require API key."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        settings = get_settings()
        if not settings.API_ENABLED:
            abort(503, description="API is disabled")
            
        api_key = request.headers.get("X-API-Key")
        if api_key != settings.API_MASTER_KEY:
            abort(401, description="Invalid or missing API Key")
            
        return f(*args, **kwargs)
    return decorated_function

@api_bp.route("/status", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok", 
        "version": "1.0.0",
        "service": "Watchtower Intelligence Platform"
    })

@api_bp.route("/sources", methods=["GET"])
@require_api_key
def list_sources():
    """List available data sources (intelligence modules)."""
    # Scan data directory for subdirectories with output files
    data_dir = Path("data")
    sources = []
    
    if data_dir.exists():
        for item in data_dir.iterdir():
            if item.is_dir():
                # Check if it has an output folder or JSON files
                output_dir = item / "output"
                if output_dir.exists() or list(item.glob("*.json")):
                    sources.append(item.name)
    
    return jsonify({
        "count": len(sources),
        "sources": sorted(sources)
    })

@api_bp.route("/data/<source_name>", methods=["GET"])
@require_api_key
def get_source_data(source_name: str):
    """Get latest data for a specific source."""
    data_dir = Path("data") / source_name
    if not data_dir.exists():
        abort(404, description=f"Source '{source_name}' not found")
        
    # Attempt to find the "latest" or most relevant JSON file
    # Priority: output/latest.json -> output/*.json (newest) -> *.json (newest)
    
    candidate_files = []
    output_dir = data_dir / "output"
    
    if output_dir.exists():
        if (output_dir / "latest.json").exists():
            candidate_files.append(output_dir / "latest.json")
        candidate_files.extend(output_dir.glob("*.json"))
        
    candidate_files.extend(data_dir.glob("*.json"))
    
    if not candidate_files:
        abort(404, description=f"No data found for source '{source_name}'")
        
    # Sort by modification time, newest first
    # Filter out empty lists/dicts if possible? No, raw data is fine.
    # Exclude checkpoints if possible
    valid_files = [f for f in candidate_files if "checkpoint" not in f.name]
    
    if not valid_files:
        abort(404, description="No valid data files found")
        
    latest_file = sorted(valid_files, key=lambda f: f.stat().st_mtime, reverse=True)[0]
    
    try:
        content = json.loads(latest_file.read_text(encoding="utf-8"))
        return jsonify({
            "source": source_name,
            "timestamp": latest_file.stat().st_mtime,
            "file": latest_file.name,
            "data": content
        })
    except Exception as e:
        abort(500, description=f"Error reading data: {str(e)}")
