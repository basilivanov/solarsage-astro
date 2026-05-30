# AI_HEADER
# module: M-SEMANTIC-SERVICE
# wave: W-4.3
# purpose: Semantic layer service

from app.schemas.semantic import SemanticLayer, SphereTheme


# Theme mappings (simplified for MVP)
DAY_THEMES = {
    "supportive": "День возможностей",
    "steady": "Спокойный день",
    "tense": "День вызовов",
}

SPHERE_THEMES = {
    "career": {
        "high": ("Активный рост", ["продвижение", "успех", "признание"]),
        "medium": ("Стабильность", ["работа", "задачи", "рутина"]),
        "low": ("Затишье", ["отдых", "планирование"]),
    },
    "relationships": {
        "high": ("Гармония", ["близость", "понимание", "любовь"]),
        "medium": ("Ровные отношения", ["общение", "поддержка"]),
        "low": ("Дистанция", ["одиночество", "размышления"]),
    },
    "health": {
        "high": ("Энергия", ["бодрость", "активность", "сила"]),
        "medium": ("Норма", ["здоровье", "баланс"]),
        "low": ("Усталость", ["отдых", "восстановление"]),
    },
    "creativity": {
        "high": ("Вдохновение", ["творчество", "идеи", "самовыражение"]),
        "medium": ("Потенциал", ["хобби", "интересы"]),
        "low": ("Пауза", ["рефлексия", "накопление"]),
    },
}


class SemanticService:
    """Semantic layer service."""

    def build_semantic_layer(
        self,
        day_status: str,
        sphere_scores: dict[str, float],
    ) -> SemanticLayer:
        """
        Build semantic layer from scoring results.

        Args:
            day_status: "supportive" | "steady" | "tense"
            sphere_scores: {"career": 2, "relationships": 1, ...}

        Returns:
            SemanticLayer with themes and keywords
        """
        # Day theme
        day_theme = DAY_THEMES.get(day_status, "Обычный день")

        # Sphere themes
        sphere_themes = []
        all_keywords = []

        for sphere, score in sphere_scores.items():
            if sphere not in SPHERE_THEMES:
                continue

            # Determine level (high/medium/low)
            if score >= 3:
                level = "high"
            elif score >= 1:
                level = "medium"
            else:
                level = "low"

            theme, keywords = SPHERE_THEMES[sphere][level]

            sphere_themes.append(SphereTheme(
                sphere=sphere,
                score=score / 5.0,  # Normalize to 0.0-1.0
                theme=theme,
                keywords=keywords,
            ))

            all_keywords.extend(keywords)

        # Top keywords (unique, max 5)
        top_keywords = list(dict.fromkeys(all_keywords))[:5]

        return SemanticLayer(
            day_status=day_status,
            day_theme=day_theme,
            sphere_themes=sphere_themes,
            top_keywords=top_keywords,
        )
