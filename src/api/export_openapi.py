"""Script to export the FastAPI OpenAPI schema to a JSON file."""

import json

# Import the FastAPI app instance
from src.api.main import app


def export_openapi(output_path: str = "openapi.json"):
    """Export the OpenAPI schema to a file."""
    openapi_schema = app.openapi()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI schema successfully exported to {output_path}")


if __name__ == "__main__":
    export_openapi()
