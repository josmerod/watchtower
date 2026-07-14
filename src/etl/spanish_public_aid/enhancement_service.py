"""Enhancement service for Spanish public aid data."""

from typing import Any

from src.models.spanish_public_aid import SpanishPublicAidModel


class EnhancementService:
    """Service for enhancing aid data with tags, keywords, and quality scores."""

    def __init__(self, debug: bool = False):
        """Initialize enhancement service.

        Args:
            debug: Enable debug logging
        """
        self.debug = debug

    def enhance_aid_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Enhance aid data with additional metadata.

        Args:
            raw_data: Raw aid data

        Returns:
            Enhanced aid data
        """
        enhanced = raw_data.copy()

        # Add tags
        enhanced["tags"] = self._generate_tags(raw_data)

        # Add keywords
        enhanced["keywords"] = self._generate_keywords(raw_data)

        # Calculate quality score
        enhanced["quality_score"] = self._calculate_quality_score(raw_data)

        return enhanced

    def _generate_tags(self, raw_data: dict[str, Any]) -> list[str]:
        """Generate tags for the aid.

        Args:
            raw_data: Raw aid data

        Returns:
            List of tags
        """
        tags = []

        title = raw_data.get("title", "").lower()
        description = raw_data.get("description", "").lower()
        text = f"{title} {description}"

        # Tag based on keywords
        if any(word in text for word in ["2025", "nuevo", "reciente"]):
            tags.append("2025")

        if any(word in text for word in ["joven", "menor", "juvenil"]):
            tags.append("jóvenes")

        if any(word in text for word in ["mujer", "mujeres", "igualdad"]):
            tags.append("mujeres")

        if any(word in text for word in ["discapacidad", "diversidad funcional"]):
            tags.append("discapacidad")

        if any(word in text for word in ["digital", "tecnología", "tecnológico"]):
            tags.append("digital")

        if any(word in text for word in ["sostenible", "medio ambiente", "verde"]):
            tags.append("sostenible")

        return tags

    def _generate_keywords(self, raw_data: dict[str, Any]) -> list[str]:
        """Generate keywords from aid data.

        Args:
            raw_data: Raw aid data

        Returns:
            List of keywords
        """
        keywords = []

        title = raw_data.get("title", "")
        description = raw_data.get("description", "")
        text = f"{title} {description}"

        # Common Spanish aid keywords
        aid_keywords = [
            "subvención",
            "ayuda",
            "beca",
            "fomento",
            "apoyo",
            "convocatoria",
            "plazo",
            "solicitud",
            "inscripción",
            "requisitos",
            "documentación",
            "bases",
        ]

        for keyword in aid_keywords:
            if keyword.lower() in text.lower():
                keywords.append(keyword)

        # Extract year if present
        import re

        years = re.findall(r"\b20\d{2}\b", text)
        keywords.extend(years)

        return list(set(keywords))

    def _calculate_quality_score(self, raw_data: dict[str, Any]) -> float:
        """Calculate quality score for aid data.

        Args:
            raw_data: Raw aid data

        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 0.0

        # Has title
        if raw_data.get("title") and len(raw_data["title"]) > 20:
            score += 0.2

        # Has description
        if raw_data.get("description") and len(raw_data["description"]) > 50:
            score += 0.2

        # Has URL
        if raw_data.get("url"):
            score += 0.2

        # Has dates
        if raw_data.get("dates"):
            score += 0.1

        # Has proper source
        if raw_data.get("source") in ["bdns", "gva", "valencia", "labora"]:
            score += 0.2

        # Has good title length
        title_len = len(raw_data.get("title", ""))
        if 20 < title_len < 200:
            score += 0.1

        return min(score, 1.0)

    def generate_statistics(self, data: list[SpanishPublicAidModel]) -> dict[str, Any]:
        """Generate statistics from processed aid data.

        Args:
            data: List of aid models

        Returns:
            Statistics dictionary
        """
        if not data:
            return {
                "total_aids": 0,
                "by_scope": {},
                "by_type": {},
                "by_category": {},
                "by_status": {},
                "average_quality_score": 0.0,
            }

        stats = {
            "total_aids": len(data),
            "by_scope": {},
            "by_type": {},
            "by_category": {},
            "by_status": {},
            "average_quality_score": 0.0,
        }

        # Count by scope
        for aid in data:
            scope = aid.scope.value if aid.scope else "unknown"
            stats["by_scope"][scope] = stats["by_scope"].get(scope, 0) + 1

            # Count by type
            aid_type = aid.aid_type.value if aid.aid_type else "unknown"
            stats["by_type"][aid_type] = stats["by_type"].get(aid_type, 0) + 1

            # Count by category
            category = aid.category.value if aid.category else "unknown"
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1

            # Count by status
            status = aid.status.value if aid.status else "unknown"
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Quality scores
            if hasattr(aid, "quality_score") and aid.quality_score:
                stats["average_quality_score"] += aid.quality_score

        # Calculate average quality
        if data:
            stats["average_quality_score"] /= len(data)

        return stats
