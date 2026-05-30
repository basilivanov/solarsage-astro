# AI_HEADER
# module: M-SCORING-SERVICE
# wave: W-4.2
# purpose: Scoring layer (AstroSignal[] → scored signals + day_status)

from app.schemas.normalization import AstroSignal


POSITIVE_ASPECTS = ["trine", "sextile"]
NEGATIVE_ASPECTS = ["square", "opposition"]
NEUTRAL_ASPECTS = ["conjunction"]


class ScoringService:
    """Scoring layer for astrological signals."""

    def score(self, signals: list[AstroSignal]) -> dict:
        """
        Score signals and calculate day_status.

        Args:
            signals: List of AstroSignal from normalization

        Returns:
            {
                "day_status": "supportive" | "steady" | "tense",
                "sphere_scores": {...},
                "top_signals": [...],
            }
        """
        # Calculate sphere scores (W-4.2: simplified, W-4.3: real from canon)
        sphere_scores = self._calculate_sphere_scores(signals)

        # Calculate day_status
        day_status = self._calculate_day_status(signals)

        # Get top signals (strongest 5)
        top_signals = self._get_top_signals(signals, limit=5)

        return {
            "day_status": day_status,
            "sphere_scores": sphere_scores,
            "top_signals": top_signals,
        }

    def _calculate_sphere_scores(self, signals: list[AstroSignal]) -> dict:
        """
        Calculate sphere scores.

        W-4.2: Simplified (count signals per sphere).
        W-4.3: Real scoring from canon rules.
        """
        # Simplified: just count aspects
        aspect_signals = [s for s in signals if s.type == "aspect"]

        return {
            "career": len([s for s in aspect_signals if s.planet in ["Sun", "Saturn"]]),
            "relationships": len([s for s in aspect_signals if s.planet in ["Venus", "Moon"]]),
            "health": len([s for s in aspect_signals if s.planet in ["Mars", "Moon"]]),
            "creativity": len([s for s in aspect_signals if s.planet in ["Sun", "Venus"]]),
        }

    def _calculate_day_status(self, signals: list[AstroSignal]) -> str:
        """
        Calculate day_status from signals.

        Logic:
        - supportive: strong positive aspects (trine, sextile with strength > 0.7)
        - tense: strong negative aspects (square, opposition with strength > 0.7)
        - steady: otherwise
        """
        aspect_signals = [s for s in signals if s.type == "aspect"]

        # Count strong positive aspects
        strong_positive = sum(
            1 for s in aspect_signals
            if s.aspect_type in POSITIVE_ASPECTS and s.strength > 0.7
        )

        # Count strong negative aspects
        strong_negative = sum(
            1 for s in aspect_signals
            if s.aspect_type in NEGATIVE_ASPECTS and s.strength > 0.7
        )

        # Determine status
        if strong_positive > strong_negative and strong_positive >= 2:
            return "supportive"
        elif strong_negative > strong_positive and strong_negative >= 2:
            return "tense"
        else:
            return "steady"

    def _get_top_signals(self, signals: list[AstroSignal], limit: int = 5) -> list[AstroSignal]:
        """Get top N signals by strength."""
        # Sort by strength descending
        sorted_signals = sorted(signals, key=lambda s: s.strength, reverse=True)
        return sorted_signals[:limit]
