"""
SolarSelect — Phase 7: Layout Serializer
Serializes PanelConfigurationResult to standard Python dictionaries and formatted JSON strings.
"""

import json
from typing import Dict, Any
from src.roof_fit.placement_engine import PanelConfigurationResult


class LayoutSerializer:
    """Serializes panel configuration results into standard Phase 7 contract representations."""

    @staticmethod
    def to_dict(result: PanelConfigurationResult) -> Dict[str, Any]:
        """Converts PanelConfigurationResult to standard dict."""
        return result.to_dict()

    @staticmethod
    def to_json(result: PanelConfigurationResult, indent: int = 2) -> str:
        """Serializes PanelConfigurationResult to formatted JSON string."""
        return json.dumps(result.to_dict(), indent=indent)

