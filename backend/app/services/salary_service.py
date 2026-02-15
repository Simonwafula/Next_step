from dataclasses import dataclass


@dataclass(frozen=True)
class SalaryBand:
    minimum: int
    maximum: int


class SalaryService:
    def __init__(self):
        self._seniority_bands = {
            "entry": SalaryBand(50000, 90000),
            "junior": SalaryBand(60000, 120000),
            "mid": SalaryBand(90000, 180000),
            "intermediate": SalaryBand(90000, 180000),
            "senior": SalaryBand(150000, 300000),
            "lead": SalaryBand(220000, 420000),
            "executive": SalaryBand(300000, 600000),
            "director": SalaryBand(300000, 600000),
        }

        self._title_multipliers = {
            "data scientist": 1.25,
            "data engineer": 1.2,
            "software engineer": 1.2,
            "software developer": 1.2,
            "product manager": 1.2,
            "accountant": 0.9,
            "sales": 0.85,
        }

        self._location_multipliers = {
            "nairobi": 1.15,
            "remote": 1.1,
            "mombasa": 1.0,
            "kisumu": 1.0,
            "kenya": 1.0,
        }

    def estimate_salary_range(
        self,
        title: str | None,
        seniority: str | None,
        location_text: str | None,
        currency: str = "KES",
    ) -> dict[str, int | float | str | bool]:
        level_key = (seniority or "mid").strip().lower()
        base_band = self._seniority_bands.get(
            level_key,
            self._seniority_bands["mid"],
        )

        title_lower = (title or "").lower()
        title_multiplier = self._pick_title_multiplier(title_lower)

        location_lower = (location_text or "").lower()
        location_multiplier = self._pick_location_multiplier(location_lower)

        multiplier = title_multiplier * location_multiplier

        estimated_min = int(round(base_band.minimum * multiplier, -3))
        estimated_max = int(round(base_band.maximum * multiplier, -3))

        confidence = 0.45
        if seniority:
            confidence += 0.2
        if title_multiplier != 1.0:
            confidence += 0.2
        if location_multiplier != 1.0:
            confidence += 0.1

        return {
            "min": max(estimated_min, 30000),
            "max": max(estimated_max, estimated_min),
            "currency": currency,
            "estimated": True,
            "confidence": min(round(confidence, 2), 0.95),
        }

    def format_salary_range(
        self,
        minimum: int,
        maximum: int,
        currency: str = "KES",
    ) -> str:
        return f"{currency} {minimum:,.0f} - {maximum:,.0f}"

    def _pick_title_multiplier(self, title_lower: str) -> float:
        for role_key, multiplier in self._title_multipliers.items():
            if role_key in title_lower:
                return multiplier
        return 1.0

    def _pick_location_multiplier(self, location_lower: str) -> float:
        for location_key, multiplier in self._location_multipliers.items():
            if location_key in location_lower:
                return multiplier
        return 1.0


salary_service = SalaryService()
