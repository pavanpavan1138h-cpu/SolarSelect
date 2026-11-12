"""Explicit mapping from Phase 9 field names to authoritative Phase 7 inputs."""
from src.roof_fit.engine import RoofFitEngine
from src.energy_economics.catalogue import ReadOnlyPanelCatalogue
from app.backend.services import SolarSelectPlatformService

class RoofService:
    def __init__(self, root):
        path = root / "configs/panels_catalogue.csv"
        self.catalogue = ReadOnlyPanelCatalogue(path)
        self.engine = RoofFitEngine(catalogue_path=path)

    def roof_fit(self, request):
        self.catalogue.get_panel(request.panel_id)
        spec = request.model_dump(exclude={"panel_id", "orientation_override", "inter_panel_clearance", "inter_row_clearance"})
        spec.update(clamping_gap=request.inter_panel_clearance,
                    walkway_gap=request.inter_row_clearance,
                    allowed_orientations=request.orientation_override or "both")
        return self.engine.run_dict(spec, panel_id=request.panel_id,
                                    allowed_orientations=request.orientation_override)

    @staticmethod
    def limitations():
        # Method is data-only; avoids constructing the old cwd-dependent service.
        return SolarSelectPlatformService.get_documented_limitations(None) + [
            {"id": "Spatial Non-Transferability", "title": "Known Melbourne campus sites only",
             "desc": "Temporal evaluation on observed UNISOLAR Campus 1 sites; no validation for India, new regions or residential roofs."},
            {"id": "Geometry", "title": "Geometric feasibility only",
             "desc": "No structural, regulatory or electrical installation approval."},
        ]
