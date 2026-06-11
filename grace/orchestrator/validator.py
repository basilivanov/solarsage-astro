
# ############################################################################
# AI_HEADER: MODULE_ORCHESTRATOR_VALIDATOR
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-ORCHESTRATOR-ADAPTER
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — grace/orchestrator/validator.py
# owns:
#   - grace/orchestrator/validator.py
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
# module: M-ORCH-VALIDATOR
# wave: W-ORCH-1
# purpose: Wave packet validator

from pathlib import Path
from typing import List, Tuple


class PacketValidator:
    """Validate wave packets against GRACE canon."""

    def __init__(self, packets_dir: Path):
        self.packets_dir = packets_dir

    def validate_packet(self, wave_id: str) -> Tuple[bool, List[str]]:
        """
        Validate wave packet.

        Returns:
            (is_valid, errors)
        """
        packet_path = self.packets_dir / f"{wave_id}.md"

        if not packet_path.exists():
            return False, [f"Packet file not found: {packet_path}"]

        content = packet_path.read_text()
        errors = []

        # Check required sections
        required_sections = ['# Decision', '## Acceptance Criteria', '## Evidence']
        for section in required_sections:
            if section not in content:
                errors.append(f"Missing section: {section}")

        # Check for AI_HEADER (optional but recommended)
        if '# AI_HEADER' not in content and 'AI_HEADER' not in content:
            errors.append("Missing AI_HEADER (recommended)")

        return len(errors) == 0, errors

    def validate_all(self) -> dict:
        """Validate all packets."""
        results = {}

        for packet_file in self.packets_dir.glob('W-*.md'):
            wave_id = packet_file.stem
            is_valid, errors = self.validate_packet(wave_id)
            results[wave_id] = {
                'valid': is_valid,
                'errors': errors,
            }

        return results
