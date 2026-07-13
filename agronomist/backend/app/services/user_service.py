from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.farm import Farm
from app.models.user import User
from app.schemas.user import (
    DEFAULT_ACCOUNT_SETTINGS,
    AccountSettingsRead,
    AccountSettingsUpdate,
    UserCreate,
    UserProfileUpdate,
)
from app.services.exceptions import (
    DuplicateUserError,
    InvalidCredentialsError,
    UserPersistenceError,
    UserValidationError,
)


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(func.lower(User.email) == email.lower())
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        statement = select(User).where(User.id == user_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_users(self, *, skip: int = 0, limit: int = 100) -> Sequence[User]:
        statement = (
            select(User)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return self.db.execute(statement).scalars().all()

    def create_user(self, user_in: UserCreate) -> User:
        email = user_in.email.lower()
        phone_number = user_in.phone_number

        duplicate_filters = [func.lower(User.email) == email]
        if phone_number:
            duplicate_filters.append(User.phone_number == phone_number)

        duplicate = self.db.execute(
            select(User.id).where(or_(*duplicate_filters))
        ).scalar_one_or_none()
        if duplicate:
            raise DuplicateUserError

        user = User(
            email=email,
            phone_number=phone_number,
            full_name=user_in.full_name,
            preferred_language=user_in.preferred_language,
            hashed_password=get_password_hash(user_in.password),
        )

        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateUserError from exc

        self.db.refresh(user)
        return user

    def update_profile(
        self,
        *,
        user: User,
        profile_in: UserProfileUpdate,
    ) -> User:
        data = profile_in.model_dump(exclude_unset=True)

        if "phone_number" in data:
            phone_number = data["phone_number"]
            if phone_number:
                duplicate = self.db.execute(
                    select(User.id).where(
                        User.phone_number == phone_number,
                        User.id != user.id,
                    )
                ).scalar_one_or_none()
                if duplicate:
                    raise DuplicateUserError
            user.phone_number = phone_number

        if "default_farm_id" in data:
            default_farm_id = data["default_farm_id"]
            if default_farm_id is not None and not self._farm_belongs_to_user(
                user_id=user.id,
                farm_id=default_farm_id,
            ):
                raise UserValidationError("Default farm must belong to the current user")
            user.default_farm_id = default_farm_id

        for field in (
            "full_name",
            "preferred_language",
            "profile_picture_url",
            "default_state",
            "default_district",
        ):
            if field in data:
                setattr(user, field, data[field])

        settings_updates = {
            field: data[field]
            for field in ("timezone", "units", "theme")
            if field in data
        }
        if settings_updates:
            settings_data = self._merged_settings(user)
            settings_data.update(settings_updates)
            user.account_settings = self._normalize_settings_aliases(settings_data)

        return self._commit_and_refresh(user)

    def get_settings(self, *, user: User) -> AccountSettingsRead:
        return self._settings_read(user)

    def update_settings(
        self,
        *,
        user: User,
        settings_in: AccountSettingsUpdate,
    ) -> AccountSettingsRead:
        data = settings_in.model_dump(exclude_unset=True)

        if "default_farm_id" in data:
            default_farm_id = data["default_farm_id"]
            if default_farm_id is not None and not self._farm_belongs_to_user(
                user_id=user.id,
                farm_id=default_farm_id,
            ):
                raise UserValidationError("Default farm must belong to the current user")
            user.default_farm_id = default_farm_id

        for field in ("preferred_language", "default_state", "default_district"):
            if field in data:
                setattr(user, field, data[field])

        settings_data = self._merged_settings(user)
        settings_updates = {
            key: value
            for key, value in data.items()
            if key
            not in {
                "preferred_language",
                "default_state",
                "default_district",
                "default_farm_id",
            }
        }
        settings_data.update(settings_updates)
        for canonical_key, alias_key in (
            ("response_language", "ai_response_language"),
            ("explanation_detail", "ai_explanation_detail"),
        ):
            if alias_key in settings_updates and canonical_key not in settings_updates:
                settings_data[canonical_key] = settings_updates[alias_key]
            if canonical_key in settings_updates and alias_key not in settings_updates:
                settings_data[alias_key] = settings_updates[canonical_key]
        user.account_settings = self._normalize_settings_aliases(settings_data)
        self._commit_and_refresh(user)
        return self._settings_read(user)

    def change_password(
        self,
        *,
        user: User,
        current_password: str,
        new_password: str,
    ) -> None:
        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError
        user.hashed_password = get_password_hash(new_password)
        self._commit_and_refresh(user)

    def _settings_read(self, user: User) -> AccountSettingsRead:
        settings = self._merged_settings(user)
        response_language = settings["response_language"]
        explanation_detail = settings["explanation_detail"]
        return AccountSettingsRead(
            preferred_language=user.preferred_language,
            units=settings["units"],
            timezone=settings["timezone"],
            date_format=settings["date_format"],
            theme=settings["theme"],
            default_state=user.default_state,
            default_district=user.default_district,
            default_farm_id=user.default_farm_id,
            default_location=settings["default_location"],
            default_location_latitude=settings["default_location_latitude"],
            default_location_longitude=settings["default_location_longitude"],
            location_source=settings["location_source"],
            location_permission_status=settings["location_permission_status"],
            weather_alerts=bool(settings.get("weather_alerts", True)),
            irrigation_reminders=bool(settings.get("irrigation_reminders", True)),
            fertilizer_reminders=bool(settings.get("fertilizer_reminders", True)),
            disease_alerts=bool(settings.get("disease_alerts", True)),
            crop_stage_reminders=bool(settings.get("crop_stage_reminders", True)),
            high_risk_alerts=bool(settings.get("high_risk_alerts", True)),
            daily_summary=bool(settings.get("daily_summary", True)),
            weekly_summary=bool(settings.get("weekly_summary", True)),
            push_enabled=bool(settings.get("push_enabled", False)),
            push_token=settings.get("push_token"),
            push_platform=settings.get("push_platform"),
            push_provider=settings.get("push_provider"),
            response_language=response_language,
            ai_response_language=response_language,
            explanation_detail=explanation_detail,
            ai_explanation_detail=explanation_detail,
            organic_treatment_preference=bool(settings["organic_treatment_preference"]),
            chemical_treatment_preference=bool(settings["chemical_treatment_preference"]),
            show_sources_by_default=bool(settings["show_sources_by_default"]),
            allow_farm_context_in_chat=bool(settings["allow_farm_context_in_chat"]),
            location_usage_consent=bool(settings["location_usage_consent"]),
            ai_data_usage_explanation=settings["ai_data_usage_explanation"],
            delete_account_requested=bool(settings["delete_account_requested"]),
            export_account_data_requested=bool(settings["export_account_data_requested"]),
        )

    def _merged_settings(self, user: User) -> dict[str, Any]:
        settings = dict(DEFAULT_ACCOUNT_SETTINGS)
        settings.update(user.account_settings or {})
        settings.setdefault("weather_alerts", True)
        settings.setdefault("irrigation_reminders", True)
        settings.setdefault("fertilizer_reminders", True)
        settings.setdefault("disease_alerts", True)
        settings.setdefault("crop_stage_reminders", True)
        settings.setdefault("high_risk_alerts", True)
        settings.setdefault("daily_summary", True)
        settings.setdefault("weekly_summary", True)
        settings.setdefault("push_enabled", False)
        settings.setdefault("push_token", None)
        settings.setdefault("push_platform", None)
        settings.setdefault("push_provider", None)
        settings = self._normalize_settings_aliases(settings)
        return settings

    def _normalize_settings_aliases(self, settings: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(settings)
        response_language = (
            normalized.get("response_language")
            or normalized.get("ai_response_language")
            or DEFAULT_ACCOUNT_SETTINGS["response_language"]
        )
        explanation_detail = (
            normalized.get("explanation_detail")
            or normalized.get("ai_explanation_detail")
            or DEFAULT_ACCOUNT_SETTINGS["explanation_detail"]
        )
        normalized["response_language"] = response_language
        normalized["ai_response_language"] = response_language
        normalized["explanation_detail"] = explanation_detail
        normalized["ai_explanation_detail"] = explanation_detail
        return normalized

    def _farm_belongs_to_user(self, *, user_id: uuid.UUID, farm_id: uuid.UUID) -> bool:
        statement = select(Farm.id).where(Farm.id == farm_id, Farm.user_id == user_id)
        return self.db.execute(statement).scalar_one_or_none() is not None

    def _commit_and_refresh(self, user: User) -> User:
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateUserError from exc
        except Exception as exc:
            self.db.rollback()
            raise UserPersistenceError from exc

        self.db.refresh(user)
        return user
