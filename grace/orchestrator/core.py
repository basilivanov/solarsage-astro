
# ############################################################################
# AI_HEADER: MODULE_ORCHESTRATOR_CORE
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-ORCHESTRATOR-ADAPTER
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — grace/orchestrator/core.py
# owns:
#   - grace/orchestrator/core.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-ORCH-CORE
# wave: W-ORCH-1
# purpose: GRACE orchestrator core

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class Wave:
    """GRACE wave definition."""
    id: str
    title: str
    phase: str
    dependencies: List[str]
    status: str  # "pending", "in_progress", "completed", "blocked"


class GraceOrchestrator:
    """GRACE-ready orchestrator runtime adapter."""

    def __init__(self, plan_path: Path):
        self.plan_path = plan_path
        self.waves: List[Wave] = []
        self._load_plan()

    def _load_plan(self) -> None:
        """Load waves from development-plan.xml."""
        try:
            tree = ET.parse(self.plan_path)
            root = tree.getroot()
        except ET.ParseError as e:
            raise ValueError(
                f"Failed to parse development plan XML at {self.plan_path}: {e}\n"
                f"Line {e.position[0]}, Column {e.position[1]}"
            ) from e

        for phase in root.findall('.//phase'):
            phase_id = phase.get('id', 'unknown')

            for wave_elem in phase.findall('wave'):
                wave_id = wave_elem.get('id')
                title_elem = wave_elem.find('title')
                title = title_elem.text if title_elem is not None else ''

                # Parse dependencies
                deps = []
                deps_elem = wave_elem.find('dependencies')
                if deps_elem is not None:
                    for dep in deps_elem.findall('wave'):
                        deps.append(dep.text)

                wave = Wave(
                    id=wave_id,
                    title=title,
                    phase=phase_id,
                    dependencies=deps,
                    status='pending',
                )
                self.waves.append(wave)

    def get_wave(self, wave_id: str) -> Optional[Wave]:
        """Get wave by ID."""
        return next((w for w in self.waves if w.id == wave_id), None)

    def get_ready_waves(self) -> List[Wave]:
        """Get waves ready to execute (dependencies satisfied)."""
        ready = []

        for wave in self.waves:
            if wave.status != 'pending':
                continue

            # Check dependencies
            deps_satisfied = all(
                self.get_wave(dep_id).status == 'completed'
                for dep_id in wave.dependencies
                if self.get_wave(dep_id) is not None
            )

            if deps_satisfied:
                ready.append(wave)

        return ready

    def mark_completed(self, wave_id: str) -> None:
        """Mark wave as completed."""
        wave = self.get_wave(wave_id)
        if wave:
            wave.status = 'completed'

    def get_progress(self) -> dict:
        """Get overall progress."""
        total = len(self.waves)
        completed = sum(1 for w in self.waves if w.status == 'completed')
        in_progress = sum(1 for w in self.waves if w.status == 'in_progress')
        pending = sum(1 for w in self.waves if w.status == 'pending')

        return {
            'total': total,
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'percentage': (completed / total * 100) if total > 0 else 0,
        }
