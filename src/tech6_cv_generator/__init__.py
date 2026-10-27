"""tech6-cv-generator: generate TECH-6 CV documents from structured JSON."""

from .form_builder import FormBuilder
from .schema_mappers import map_flat_to_tech6, map_kosovo_to_tech6, map_to_canonical

__version__ = "2.0.0"

__all__ = [
    "FormBuilder",
    "map_flat_to_tech6",
    "map_kosovo_to_tech6",
    "map_to_canonical",
    "__version__",
]
