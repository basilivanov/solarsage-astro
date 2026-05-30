# AI_HEADER
# module: M-SIDECAR-SCHEMA-HEALTH
# wave: W-3.1
# purpose: Health response schema

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response."""
    ok: bool
    version: str
    ephemeris_path: str
    calculation_version: str
