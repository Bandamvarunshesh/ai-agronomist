from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.crop import Diagnosis
from app.models.farm import Farm
from app.models.notification import Notification
from app.models.recommendation import FarmRecommendation
from app.schemas.stage_advisory import StageAdvisoryRead
from app.schemas.weather import FarmWeatherRead
from app.services.exceptions import NotificationPersistenceError
from app.services.notification_service import NotificationService


logger = logging.getLogger(__name__)

HIGH_RISK_SEVERITIES = {"high", "severe", "critical"}


class NotificationGenerationService:
    def __init__(self, db: Session):
        self.notification_service = NotificationService(db)

    def add_for_recommendation(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        recommendation: FarmRecommendation,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        risk_level = recommendation.risk_level.lower()
        health_score = self._decimal_to_float(recommendation.farm_health_score)
        deep_link = f"/farms/{farm.id}/recommendations"

        self._append_notification(
            notifications,
            user_id=user_id,
            farm_id=farm.id,
            notification_type="recommendation_generated",
            title=f"New recommendations for {farm.farm_name}",
            body=(
                f"{len(recommendation.prioritized_recommendations)} prioritized actions "
                f"are ready for {farm.crop}."
            ),
            priority="normal",
            source="recommendation",
            payload={
                "recommendation_id": str(recommendation.id),
                "farm_health_score": health_score,
                "risk_level": recommendation.risk_level,
            },
            dedupe_key=f"recommendation_generated:{recommendation.id}",
            deep_link=deep_link,
        )
        self._append_notification(
            notifications,
            user_id=user_id,
            farm_id=farm.id,
            notification_type="daily_ai_summary",
            title=f"Daily AI summary for {farm.farm_name}",
            body=self._daily_summary_body(recommendation),
            priority="normal",
            source="recommendation",
            payload={
                "recommendation_id": str(recommendation.id),
                "daily_action_plan": recommendation.daily_action_plan,
            },
            dedupe_key=f"daily_ai_summary:{recommendation.id}",
            deep_link=deep_link,
        )
        self._append_notification(
            notifications,
            user_id=user_id,
            farm_id=farm.id,
            notification_type="weekly_ai_summary",
            title=f"Weekly AI summary for {farm.farm_name}",
            body=recommendation.weekly_summary,
            priority="normal",
            source="recommendation",
            payload={
                "recommendation_id": str(recommendation.id),
                "weekly_summary": recommendation.weekly_summary,
            },
            dedupe_key=f"weekly_ai_summary:{recommendation.id}",
            deep_link=deep_link,
        )

        if risk_level in {"high", "critical"} or health_score <= 60:
            priority = (
                "urgent"
                if risk_level == "critical" or health_score <= 40
                else "high"
            )
            self._append_notification(
                notifications,
                user_id=user_id,
                farm_id=farm.id,
                notification_type="farm_health_alert",
                title=f"Farm health alert: {farm.farm_name}",
                body=(
                    f"Health score is {health_score:.0f}/100 with "
                    f"{recommendation.risk_level} risk."
                ),
                priority=priority,
                source="recommendation",
                payload={
                    "recommendation_id": str(recommendation.id),
                    "farm_health_score": health_score,
                    "risk_level": recommendation.risk_level,
                },
                dedupe_key=f"farm_health_alert:{recommendation.id}",
                deep_link=deep_link,
            )

        if risk_level == "critical":
            self._append_notification(
                notifications,
                user_id=user_id,
                farm_id=farm.id,
                notification_type="high_risk_alert",
                title=f"Critical risk for {farm.farm_name}",
                body="Review the latest recommendations and contact a local expert if needed.",
                priority="urgent",
                source="recommendation",
                payload={
                    "recommendation_id": str(recommendation.id),
                    "risk_level": recommendation.risk_level,
                },
                dedupe_key=f"high_risk_recommendation:{recommendation.id}",
                deep_link=deep_link,
            )

        return notifications

    def add_for_weather(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        weather: FarmWeatherRead,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        today = date.today().isoformat()
        next_two_day_rain = sum(
            day.precipitation_sum_mm or 0 for day in weather.forecast[:2]
        )
        seven_day_rain = sum(day.precipitation_sum_mm or 0 for day in weather.forecast)
        max_temp = self._max_float(day.temperature_max_c for day in weather.forecast)
        max_gust = self._max_float(day.wind_gusts_max_kmh for day in weather.forecast)
        max_humidity = self._max_float(
            day.relative_humidity_mean_percent for day in weather.forecast
        )
        deep_link = f"/farms/{farm.id}/weather"

        weather_risks = []
        if seven_day_rain >= 50:
            weather_risks.append("heavy rainfall")
        if max_temp is not None and max_temp >= 38:
            weather_risks.append("severe heat")
        if max_gust is not None and max_gust >= 45:
            weather_risks.append("strong wind")
        if max_humidity is not None and max_humidity >= 90:
            weather_risks.append("very high humidity")

        if weather_risks:
            self._append_notification(
                notifications,
                user_id=user_id,
                farm_id=farm.id,
                notification_type="weather_alert",
                title=f"Weather alert for {farm.farm_name}",
                body=f"Watch for {', '.join(weather_risks)} in the 7-day forecast.",
                priority="high",
                source="weather",
                payload={
                    "weather_risks": weather_risks,
                    "fetched_at": weather.fetched_at.isoformat(),
                    "source": weather.source,
                },
                dedupe_key=f"weather_alert:{farm.id}:{today}:{'-'.join(weather_risks)}",
                deep_link=deep_link,
            )

        if next_two_day_rain < 3 and max_temp is not None and max_temp >= 34:
            self._append_notification(
                notifications,
                user_id=user_id,
                farm_id=farm.id,
                notification_type="irrigation_reminder",
                title=f"Irrigation reminder for {farm.farm_name}",
                body="Rain looks limited and heat is elevated; check soil moisture before irrigation.",
                priority="normal",
                source="weather",
                payload={
                    "next_two_day_rain_mm": next_two_day_rain,
                    "max_temperature_c": max_temp,
                    "weather_advice": weather.advice.irrigation,
                },
                dedupe_key=f"irrigation_reminder:{farm.id}:{today}",
                deep_link=deep_link,
            )

        return notifications

    def add_for_stage_advisory(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        advisory: StageAdvisoryRead,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        today = date.today().isoformat()
        deep_link = f"/farms/{farm.id}/stage-advisory"

        self._append_notification(
            notifications,
            user_id=user_id,
            farm_id=farm.id,
            notification_type="crop_stage_reminder",
            title=f"{farm.crop} stage: {advisory.current_stage.name}",
            body=self._first_text(
                advisory.ai_recommendations,
                default="Review the current stage advisory for next actions.",
            ),
            priority="normal",
            source="stage_advisory",
            payload={
                "current_stage": advisory.current_stage.model_dump(mode="json"),
                "next_stage": (
                    advisory.next_stage.model_dump(mode="json")
                    if advisory.next_stage is not None
                    else None
                ),
                "days_since_sowing": advisory.days_since_sowing,
            },
            dedupe_key=(
                f"crop_stage_reminder:{farm.id}:{today}:"
                f"{advisory.current_stage.name}"
            ),
            deep_link=deep_link,
        )

        fertilizer_action = self._find_keyword_action(
            advisory.important_actions + advisory.ai_recommendations,
            {"fertilizer", "nutrition", "nutrient", "soil test", "soil-test"},
        )
        if fertilizer_action is not None:
            self._append_notification(
                notifications,
                user_id=user_id,
                farm_id=farm.id,
                notification_type="fertilizer_reminder",
                title=f"Nutrition reminder for {farm.farm_name}",
                body=fertilizer_action,
                priority="normal",
                source="stage_advisory",
                payload={"stage": advisory.current_stage.model_dump(mode="json")},
                dedupe_key=f"fertilizer_reminder:{farm.id}:{today}",
                deep_link=deep_link,
            )

        task_action = self._first_text(advisory.important_actions, default="")
        if task_action:
            self._append_notification(
                notifications,
                user_id=user_id,
                farm_id=farm.id,
                notification_type="farming_task_reminder",
                title=f"Task reminder for {farm.farm_name}",
                body=task_action,
                priority="normal",
                source="stage_advisory",
                payload={"stage": advisory.current_stage.model_dump(mode="json")},
                dedupe_key=f"farming_task_reminder:{farm.id}:{today}:{task_action[:40]}",
                deep_link=deep_link,
            )

        return notifications

    def add_for_high_risk_diagnosis(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        diagnosis: Diagnosis,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        severity = diagnosis.severity.lower()
        if not diagnosis.escalate_to_human and severity not in HIGH_RISK_SEVERITIES:
            return notifications

        deep_link = f"/farms/{farm.id}/diagnoses/{diagnosis.id}"
        self._append_notification(
            notifications,
            user_id=user_id,
            farm_id=farm.id,
            diagnosis_id=diagnosis.id,
            notification_type="disease_alert",
            title=f"Disease alert: {diagnosis.disease_name}",
            body=(
                f"{diagnosis.severity} severity detected on {farm.farm_name}. "
                "Scout nearby plants and consider local expert review."
            ),
            priority="high",
            source="diagnosis",
            payload={
                "diagnosis_id": str(diagnosis.id),
                "disease_name": diagnosis.disease_name,
                "severity": diagnosis.severity,
                "confidence_score": str(diagnosis.confidence_score),
                "escalate_to_human": diagnosis.escalate_to_human,
            },
            dedupe_key=f"disease_alert:{diagnosis.id}",
            deep_link=deep_link,
        )
        self._append_notification(
            notifications,
            user_id=user_id,
            farm_id=farm.id,
            diagnosis_id=diagnosis.id,
            notification_type="high_risk_alert",
            title=f"High-risk diagnosis for {farm.farm_name}",
            body=(
                "Contact a local agronomist or extension officer before "
                "high-risk treatment decisions."
            ),
            priority="urgent",
            source="diagnosis",
            payload={
                "diagnosis_id": str(diagnosis.id),
                "disease_name": diagnosis.disease_name,
                "severity": diagnosis.severity,
            },
            dedupe_key=f"high_risk_diagnosis:{diagnosis.id}",
            deep_link=deep_link,
        )
        return notifications

    def _append_notification(
        self,
        notifications: list[Notification],
        **kwargs,
    ) -> None:
        try:
            notification = self.notification_service.add_notification(**kwargs)
        except NotificationPersistenceError:
            logger.exception("Unable to generate notification")
            raise

        if notification is not None:
            notifications.append(notification)

    def _daily_summary_body(self, recommendation: FarmRecommendation) -> str:
        if not recommendation.daily_action_plan:
            return "Review today's AI action plan for the farm."

        first_day = recommendation.daily_action_plan[0]
        actions = first_day.get("actions") if isinstance(first_day, dict) else None
        if isinstance(actions, list) and actions:
            return "Today's top action: " + str(actions[0])
        return "Review today's AI action plan for the farm."

    def _decimal_to_float(self, value: Decimal | None) -> float:
        if value is None:
            return 0.0
        return float(value)

    def _max_float(self, values: Iterable[float | int | None]) -> float | None:
        numeric_values = [float(value) for value in values if value is not None]
        if not numeric_values:
            return None
        return max(numeric_values)

    def _first_text(self, values: list[str], *, default: str) -> str:
        for value in values:
            cleaned = " ".join(value.split())
            if cleaned:
                return cleaned
        return default

    def _find_keyword_action(
        self,
        values: list[str],
        keywords: set[str],
    ) -> str | None:
        for value in values:
            normalized = " ".join(value.split())
            lower_value = normalized.lower()
            if any(keyword in lower_value for keyword in keywords):
                return normalized
        return None
