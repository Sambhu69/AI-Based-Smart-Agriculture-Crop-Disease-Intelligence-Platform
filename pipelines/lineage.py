"""
Pipeline Lineage Tracking Utility
=================================
Records and saves execution metadata, inputs, outputs, checksums, and parameters
for reproducible and auditable data engineering steps.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def compute_file_hash(path: Path) -> str:
    """Calculates SHA-256 hash of a file."""
    if not path.is_file():
        return ""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class LineageRecord:
    """Encapsulates execution lineage for a pipeline stage."""

    def __init__(
        self,
        pipeline_name: str,
        stage_name: str,
        parameters: Optional[Dict[str, Any]] = None,
    ):
        self.pipeline_name = pipeline_name
        self.stage_name = stage_name
        self.parameters = parameters or {}
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.inputs: List[Dict[str, Any]] = []
        self.outputs: List[Dict[str, Any]] = []
        self.status: str = "running"
        self.metadata: Dict[str, Any] = {}

    def add_input(self, path: Path, description: str = "") -> None:
        """Records an input artifact."""
        self.inputs.append({
            "path": str(path),
            "exists": path.exists(),
            "sha256": compute_file_hash(path) if path.is_file() else None,
            "description": description,
        })

    def add_output(self, path: Path, description: str = "") -> None:
        """Records an output artifact."""
        self.outputs.append({
            "path": str(path),
            "exists": path.exists(),
            "sha256": compute_file_hash(path) if path.is_file() else None,
            "description": description,
        })

    def finish(self, status: str = "success", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Finalizes lineage record and returns dict representation."""
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.status = status
        if metadata:
            self.metadata.update(metadata)
        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pipeline_name": self.pipeline_name,
            "stage_name": self.stage_name,
            "parameters": self.parameters,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "metadata": self.metadata,
        }

    def save(self, destination: Path) -> Path:
        """Persists lineage record as JSON."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return destination
