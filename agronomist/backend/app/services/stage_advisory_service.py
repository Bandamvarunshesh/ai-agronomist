from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.crop import Diagnosis
from app.models.crop_stage import CropStage
from app.models.farm import Farm
from app.repositories.stage_advisory_repository import StageAdvisoryRepository
from app.schemas.stage_advisory import (
    StageAdvisoryRead,
    StageDiagnosisContextRead,
    StageWeatherContextRead,
    StageWindowRead,
)
from app.schemas.weather import FarmWeatherRead
from app.services.exceptions import (
    FarmNotFoundError,
    FarmPersistenceError,
    NotificationPersistenceError,
    StageAdvisoryPersistenceError,
    TimelinePersistenceError,
    WeatherLocationNotFoundError,
    WeatherProviderError,
    WeatherResponseParseError,
)
from app.services.farm_service import FarmService
from app.services.notification_generation_service import NotificationGenerationService
from app.services.timeline_service import TimelineService
from app.services.weather_service import WeatherService


@dataclass(frozen=True)
class StageData:
    name: str
    stage_order: int
    start_day: int
    end_day: int
    important_actions: list[str]
    risk_factors: list[str]
    ai_recommendations: list[str]


GENERIC_STAGE_DATA = [
    StageData(
        name="Germination and establishment",
        stage_order=0,
        start_day=0,
        end_day=14,
        important_actions=[
            "Check emergence and plant stand",
            "Keep soil moist but not waterlogged",
            "Fill gaps where crop establishment is poor",
        ],
        risk_factors=[
            "Poor germination",
            "Seedling damping-off",
            "Soil crusting or early moisture stress",
        ],
        ai_recommendations=[
            "Inspect seedlings every 2 to 3 days",
            "Use light irrigation when the topsoil dries",
            "Contact an extension officer if large patches fail to emerge",
        ],
    ),
    StageData(
        name="Vegetative growth",
        stage_order=1,
        start_day=15,
        end_day=40,
        important_actions=[
            "Scout for weeds and early pest damage",
            "Maintain even soil moisture",
            "Plan nutrition based on soil and crop condition",
        ],
        risk_factors=[
            "Weed competition",
            "Nutrient deficiency symptoms",
            "Early sucking pests or leaf damage",
        ],
        ai_recommendations=[
            "Prioritize field scouting before interventions",
            "Avoid precise fertilizer or pesticide dosages without local soil-test or label guidance",
            "Keep records of irrigation and field observations",
        ],
    ),
    StageData(
        name="Flowering and reproductive initiation",
        stage_order=2,
        start_day=41,
        end_day=65,
        important_actions=[
            "Avoid water stress around flowering",
            "Protect pollination conditions",
            "Scout for disease and pest pressure in the canopy",
        ],
        risk_factors=[
            "Flower drop from heat or moisture stress",
            "High disease pressure in humid weather",
            "Pest damage to reproductive parts",
        ],
        ai_recommendations=[
            "Avoid disruptive operations during peak flowering",
            "Use weather windows for any spray operations",
            "Seek local agronomist advice for severe flowering losses",
        ],
    ),
    StageData(
        name="Fruiting or grain filling",
        stage_order=3,
        start_day=66,
        end_day=95,
        important_actions=[
            "Maintain consistent moisture",
            "Monitor crop load and lodging risk",
            "Scout for late pests, diseases, and nutrient stress",
        ],
        risk_factors=[
            "Yield loss from moisture swings",
            "Fruit or grain quality problems",
            "Late-season disease pressure",
        ],
        ai_recommendations=[
            "Keep irrigation steady rather than erratic",
            "Inspect fields after rain or strong wind",
            "Escalate fast-spreading disease symptoms to an agronomist",
        ],
    ),
    StageData(
        name="Maturity and harvest preparation",
        stage_order=4,
        start_day=96,
        end_day=130,
        important_actions=[
            "Track maturity signs",
            "Prepare harvest labor, tools, and storage",
            "Avoid unnecessary late chemical applications",
        ],
        risk_factors=[
            "Harvest delays from rain",
            "Storage quality losses",
            "Lodging or shattering in wind",
        ],
        ai_recommendations=[
            "Plan harvest around dry weather windows",
            "Dry and grade produce before storage where applicable",
            "Follow label pre-harvest intervals for any regulated input",
        ],
    ),
    StageData(
        name="Post-harvest and field reset",
        stage_order=5,
        start_day=131,
        end_day=365,
        important_actions=[
            "Clean field residues as appropriate",
            "Review yield and input records",
            "Plan rotation, soil improvement, and storage checks",
        ],
        risk_factors=[
            "Stored produce spoilage",
            "Carry-over pests and disease",
            "Missed rotation or soil recovery planning",
        ],
        ai_recommendations=[
            "Separate damaged produce during storage",
            "Document disease or pest hotspots for the next season",
            "Discuss rotation and soil health with a local extension officer",
        ],
    ),
]


class StageAdvisoryService:
    def __init__(self, db: Session):
        self.db = db
        self.farm_service = FarmService(db)
        self.repository = StageAdvisoryRepository(db)
        self.notification_generation_service = NotificationGenerationService(db)
        self.weather_service = WeatherService(db)
        self.timeline_service = TimelineService(db)

    def get_stage_advisory(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
        log_timeline: bool = True,
    ) -> StageAdvisoryRead:
        farm = self._get_farm(user_id=user_id, farm_id=farm_id)
        stages = self._get_stages_for_crop(farm.crop)
        latest_diagnosis = self._get_latest_diagnosis(
            user_id=user_id,
            farm_id=farm_id,
        )
        weather, weather_context = self._get_weather_context(
            user_id=user_id,
            farm_id=farm_id,
        )

        days_since_sowing = self._days_since_sowing(farm.sowing_date)
        current_stage, next_stage = self._select_stage(stages, days_since_sowing)

        important_actions = self._dedupe(
            [
                *current_stage.important_actions,
                *self._farm_profile_actions(farm, days_since_sowing),
                *self._weather_actions(weather),
                *self._diagnosis_actions(latest_diagnosis),
            ]
        )
        risks = self._dedupe(
            [
                *current_stage.risk_factors,
                *self._farm_profile_risks(farm, days_since_sowing),
                *self._weather_risks(weather, weather_context),
                *self._diagnosis_risks(latest_diagnosis),
            ]
        )
        ai_recommendations = self._dedupe(
            [
                *current_stage.ai_recommendations,
                *self._stage_transition_recommendations(current_stage, next_stage),
                *self._weather_recommendations(weather),
                *self._diagnosis_recommendations(latest_diagnosis),
            ]
        )

        advisory = StageAdvisoryRead(
            farm_id=farm.id,
            farm_name=farm.farm_name,
            crop=farm.crop,
            days_since_sowing=days_since_sowing,
            current_stage=self._stage_window(current_stage),
            next_stage=self._stage_window(next_stage) if next_stage else None,
            important_actions=important_actions,
            risks=risks,
            ai_recommendations=ai_recommendations,
            latest_diagnosis=self._diagnosis_context(latest_diagnosis),
            weather_context=weather_context,
            generated_at=datetime.now(timezone.utc),
        )
        if log_timeline:
            self._log_stage_advisory(
                user_id=user_id,
                farm=farm,
                advisory=advisory,
            )
        return advisory

    def _get_farm(self, *, user_id: uuid.UUID, farm_id: uuid.UUID) -> Farm:
        try:
            return self.farm_service.get_farm(user_id, farm_id)
        except FarmNotFoundError:
            raise
        except FarmPersistenceError:
            raise
        except SQLAlchemyError as exc:
            raise FarmPersistenceError from exc

    def _get_stages_for_crop(self, crop_name: str) -> list[StageData]:
        normalized_name = self._normalize_crop_name(crop_name)
        try:
            crop = self.repository.get_crop_by_normalized_name(normalized_name)
            if crop is None:
                crop = self.repository.get_generic_crop()
            if crop is None:
                return GENERIC_STAGE_DATA

            stages = self.repository.list_crop_stages(crop.id)
        except SQLAlchemyError as exc:
            raise StageAdvisoryPersistenceError from exc

        stage_data = [self._stage_data_from_model(stage) for stage in stages]
        return stage_data or GENERIC_STAGE_DATA

    def _get_latest_diagnosis(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> Diagnosis | None:
        try:
            return self.repository.get_latest_diagnosis_for_farm_user(
                user_id=user_id,
                farm_id=farm_id,
            )
        except SQLAlchemyError as exc:
            raise StageAdvisoryPersistenceError from exc

    def _get_weather_context(
        self,
        *,
        user_id: uuid.UUID,
        farm_id: uuid.UUID,
    ) -> tuple[FarmWeatherRead | None, StageWeatherContextRead]:
        try:
            weather = self.weather_service.get_farm_weather(
                user_id=user_id,
                farm_id=farm_id,
                log_timeline=False,
            )
        except (
            WeatherLocationNotFoundError,
            WeatherProviderError,
            WeatherResponseParseError,
        ) as exc:
            return (
                None,
                StageWeatherContextRead(
                    source="Open-Meteo",
                    summary="Weather context unavailable",
                    unavailable_reason=str(exc),
                ),
            )

        return (
            weather,
            StageWeatherContextRead(
                source=weather.source,
                summary=self._weather_summary(weather),
            ),
        )

    def _log_stage_advisory(
        self,
        *,
        user_id: uuid.UUID,
        farm: Farm,
        advisory: StageAdvisoryRead,
    ) -> None:
        try:
            self.timeline_service.add_event(
                farm_id=farm.id,
                user_id=user_id,
                event_type="stage_advisory",
                title=f"Stage advisory: {advisory.current_stage.name}",
                description=(
                    f"{farm.crop} is at {advisory.current_stage.name}"
                    if advisory.days_since_sowing is not None
                    else f"Stage advisory generated for {farm.crop}"
                ),
                source="stage_advisory",
                payload={
                    "crop": farm.crop,
                    "days_since_sowing": advisory.days_since_sowing,
                    "current_stage": advisory.current_stage.model_dump(),
                    "next_stage": (
                        advisory.next_stage.model_dump()
                        if advisory.next_stage is not None
                        else None
                    ),
                    "latest_diagnosis_id": (
                        str(advisory.latest_diagnosis.id)
                        if advisory.latest_diagnosis is not None
                        else None
                    ),
                    "weather_summary": advisory.weather_context.summary,
                },
            )
            self.notification_generation_service.add_for_stage_advisory(
                user_id=user_id,
                farm=farm,
                advisory=advisory,
            )
            self.db.commit()
        except (
            SQLAlchemyError,
            TimelinePersistenceError,
            NotificationPersistenceError,
        ) as exc:
            self.db.rollback()
            raise StageAdvisoryPersistenceError from exc

    def _normalize_crop_name(self, crop_name: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", " ", crop_name.lower()).strip()
        return " ".join(normalized.split()) or "generic"

    def _stage_data_from_model(self, stage: CropStage) -> StageData:
        return StageData(
            name=stage.stage_name,
            stage_order=stage.stage_order,
            start_day=stage.start_day,
            end_day=stage.end_day,
            important_actions=list(stage.important_actions),
            risk_factors=list(stage.risk_factors),
            ai_recommendations=list(stage.ai_recommendations),
        )

    def _days_since_sowing(self, sowing_date: date | None) -> int | None:
        if sowing_date is None:
            return None
        return (date.today() - sowing_date).days

    def _select_stage(
        self,
        stages: Sequence[StageData],
        days_since_sowing: int | None,
    ) -> tuple[StageData, StageData | None]:
        if days_since_sowing is None:
            return (
                StageData(
                    name="Unknown stage",
                    stage_order=-1,
                    start_day=0,
                    end_day=0,
                    important_actions=["Add sowing date to the farm profile"],
                    risk_factors=["Crop stage cannot be estimated without sowing date"],
                    ai_recommendations=[
                        "Update the farm profile with sowing date for stage-specific advisory",
                    ],
                ),
                stages[0] if stages else None,
            )

        if days_since_sowing < 0:
            return (
                StageData(
                    name="Pre-sowing or planned",
                    stage_order=-1,
                    start_day=days_since_sowing,
                    end_day=-1,
                    important_actions=["Prepare field, seed, irrigation, and labor plan"],
                    risk_factors=["Sowing date is still in the future"],
                    ai_recommendations=[
                        "Use the forecast to choose a safe sowing window and avoid waterlogged soil",
                    ],
                ),
                stages[0] if stages else None,
            )

        for index, stage in enumerate(stages):
            if stage.start_day <= days_since_sowing <= stage.end_day:
                next_stage = stages[index + 1] if index + 1 < len(stages) else None
                return stage, next_stage

        if stages and days_since_sowing > stages[-1].end_day:
            return stages[-1], None

        first_stage = stages[0] if stages else GENERIC_STAGE_DATA[0]
        return first_stage, stages[1] if len(stages) > 1 else None

    def _farm_profile_actions(
        self,
        farm: Farm,
        days_since_sowing: int | None,
    ) -> list[str]:
        actions = [
            f"Tailor field checks to {farm.crop} in {farm.village}, {farm.district}",
        ]
        if farm.soil_type:
            actions.append(f"Use {farm.soil_type} soil behavior when planning irrigation")
        if farm.irrigation_type:
            actions.append(f"Check {farm.irrigation_type} system before peak water demand")
        if days_since_sowing is None:
            actions.append("Record sowing date to improve stage accuracy")
        return actions

    def _farm_profile_risks(
        self,
        farm: Farm,
        days_since_sowing: int | None,
    ) -> list[str]:
        risks: list[str] = []
        soil_type = (farm.soil_type or "").lower()
        if "sandy" in soil_type:
            risks.append("Sandy soil can lose moisture quickly")
        if "clay" in soil_type:
            risks.append("Clay soil can stay wet and increase waterlogging risk")
        if days_since_sowing is None:
            risks.append("Missing sowing date reduces stage precision")
        return risks

    def _weather_actions(self, weather: FarmWeatherRead | None) -> list[str]:
        if weather is None:
            return ["Check local forecast manually before irrigation or spraying"]

        actions: list[str] = []
        next_two_day_rain = self._sum_rain(weather, days=2)
        if next_two_day_rain >= 10:
            actions.append("Clear drainage paths and delay irrigation before expected rain")
        if self._max_temp(weather) >= 35:
            actions.append("Schedule field work and irrigation during cooler hours")
        if self._max_wind_gust(weather) >= 30:
            actions.append("Choose calmer hours for spraying and equipment work")
        if self._max_humidity(weather) >= 85:
            actions.append("Scout dense canopy areas for disease symptoms")
        return actions

    def _weather_risks(
        self,
        weather: FarmWeatherRead | None,
        weather_context: StageWeatherContextRead,
    ) -> list[str]:
        if weather is None:
            return [f"Weather risk unknown: {weather_context.unavailable_reason}"]

        risks: list[str] = []
        if self._sum_rain(weather, days=7) >= 50:
            risks.append("Heavy cumulative rainfall may cause waterlogging or delays")
        if self._max_temp(weather) >= 40:
            risks.append("Severe heat stress risk in the next 7 days")
        elif self._max_temp(weather) >= 35:
            risks.append("Elevated heat stress risk in the next 7 days")
        if self._max_wind_gust(weather) >= 45:
            risks.append("Strong wind gusts may damage plants or field structures")
        elif self._max_wind_gust(weather) >= 30:
            risks.append("Wind may increase spray drift and lodging risk")
        if self._max_humidity(weather) >= 85:
            risks.append("High humidity may increase fungal and bacterial disease pressure")
        return risks

    def _weather_recommendations(self, weather: FarmWeatherRead | None) -> list[str]:
        if weather is None:
            return [
                "Use local weather observations before making irrigation, spray, or harvest decisions",
            ]

        recommendations: list[str] = []
        if self._sum_rain(weather, days=2) >= 5:
            recommendations.append(
                "Delay sprays if possible until leaves are dry and rain risk is lower",
            )
        if self._sum_rain(weather, days=7) < 5:
            recommendations.append(
                "Rainfall looks limited; conserve soil moisture and monitor irrigation need",
            )
        if self._max_temp(weather) >= 35:
            recommendations.append(
                "Watch for wilting, flower drop, or seedling stress during hot afternoons",
            )
        if self._max_wind_gust(weather) >= 30:
            recommendations.append(
                "Avoid pesticide or foliar nutrient applications during windy windows",
            )
        return recommendations

    def _diagnosis_actions(self, diagnosis: Diagnosis | None) -> list[str]:
        if diagnosis is None:
            return []
        return [
            f"Recheck plots affected by latest diagnosis: {diagnosis.disease_name}",
        ]

    def _diagnosis_risks(self, diagnosis: Diagnosis | None) -> list[str]:
        if diagnosis is None:
            return []

        risks = [
            f"Latest diagnosis indicates {diagnosis.disease_name} with {diagnosis.severity} severity",
        ]
        if diagnosis.escalate_to_human or diagnosis.severity.lower() in {
            "high",
            "severe",
            "critical",
        }:
            risks.append("Diagnosis may require local expert review")
        return risks

    def _diagnosis_recommendations(self, diagnosis: Diagnosis | None) -> list[str]:
        if diagnosis is None:
            return ["Continue routine scouting and record new symptoms with photos"]

        recommendations = [
            "Compare current symptoms with the latest diagnosis before changing treatment",
        ]
        if diagnosis.prevention_steps:
            recommendations.extend(diagnosis.prevention_steps[:3])
        if diagnosis.escalate_to_human or diagnosis.severity.lower() in {
            "high",
            "severe",
            "critical",
        }:
            recommendations.append(
                "Consult a local agronomist or extension officer before high-risk treatment decisions",
            )
        return recommendations

    def _stage_transition_recommendations(
        self,
        current_stage: StageData,
        next_stage: StageData | None,
    ) -> list[str]:
        if next_stage is None:
            return ["Review field records and plan the next crop cycle"]

        return [
            f"Prepare for next stage: {next_stage.name}",
            f"Current stage window is day {current_stage.start_day} to {current_stage.end_day}",
        ]

    def _stage_window(self, stage: StageData) -> StageWindowRead:
        return StageWindowRead(
            name=stage.name,
            stage_order=stage.stage_order if stage.stage_order >= 0 else None,
            start_day=stage.start_day if stage.start_day >= 0 else None,
            end_day=stage.end_day if stage.end_day >= 0 else None,
        )

    def _diagnosis_context(
        self,
        diagnosis: Diagnosis | None,
    ) -> StageDiagnosisContextRead | None:
        if diagnosis is None:
            return None
        return StageDiagnosisContextRead(
            id=diagnosis.id,
            disease_name=diagnosis.disease_name,
            severity=diagnosis.severity,
            confidence_score=self._decimal_to_float(diagnosis.confidence_score),
            escalate_to_human=diagnosis.escalate_to_human,
            created_at=diagnosis.created_at,
        )

    def _weather_summary(self, weather: FarmWeatherRead) -> str:
        current = weather.current
        temp = current.temperature_c
        next_two_day_rain = self._sum_rain(weather, days=2)
        max_temp = self._max_temp(weather)
        max_gust = self._max_wind_gust(weather)
        return (
            f"{current.condition}; current temperature {temp} C; "
            f"{next_two_day_rain:.1f} mm rain forecast in 2 days; "
            f"7-day max temperature {max_temp:.1f} C; "
            f"max wind gust {max_gust:.1f} km/h"
        )

    def _sum_rain(self, weather: FarmWeatherRead, *, days: int) -> float:
        return sum(
            day.precipitation_sum_mm or 0
            for day in weather.forecast[:days]
        )

    def _max_temp(self, weather: FarmWeatherRead) -> float:
        return self._max_number(
            day.temperature_max_c for day in weather.forecast
        )

    def _max_wind_gust(self, weather: FarmWeatherRead) -> float:
        return self._max_number(
            day.wind_gusts_max_kmh for day in weather.forecast
        )

    def _max_humidity(self, weather: FarmWeatherRead) -> float:
        return self._max_number(
            day.relative_humidity_mean_percent for day in weather.forecast
        )

    def _max_number(self, values: Iterable[float | int | None]) -> float:
        numeric_values = [float(value) for value in values if value is not None]
        if not numeric_values:
            return 0.0
        return max(numeric_values)

    def _decimal_to_float(self, value: Decimal) -> float:
        return float(value)

    def _dedupe(self, values: Iterable[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for value in values:
            normalized = " ".join(value.split())
            if not normalized or normalized.lower() in seen:
                continue
            seen.add(normalized.lower())
            deduped.append(normalized)
        return deduped
