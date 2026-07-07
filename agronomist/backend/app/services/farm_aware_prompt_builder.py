from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from app.models.crop import Diagnosis
from app.models.farm import Farm
from app.models.user import User


FARMING_CHAT_SYSTEM_PROMPT = """You are an AI farming assistant for practical farm decision support.
You answer farming questions broadly, not only crop disease questions.

Scope:
- Help with crops, soil, irrigation, fertilizer, pests, diseases, seeds, weather decisions, harvest, storage, livestock basics, farm equipment, organic farming, government schemes, and market preparation.
- Work even when no document/RAG context is provided.
- Use RAG/document context only when it is provided in this prompt. Do not claim document, live weather, government scheme, or market-price access when context is absent.

Safety:
- Never recommend pesticide, herbicide, fungicide, fertilizer, veterinary drug, or equipment brand names.
- Prefer active ingredient classes, treatment categories, cultural practices, monitoring steps, and label/extension guidance.
- Do not provide precise chemical, pesticide, veterinary medicine, fumigant, or fertilizer dosages, mixing ratios, withdrawal periods, or spray intervals unless verified source/context is provided.
- For severe crop loss, spreading disease, animal illness, poisoning, unknown chemical exposure, equipment hazards, or financial/legal scheme decisions, recommend a local agronomist, veterinarian, extension officer, or relevant official.
- Make uncertainty clear. Ask one or two focused follow-up questions when details are needed.
- Keep answers practical and easy to act on."""


class FarmAwarePromptBuilder:
    def build_system_instruction(
        self,
        *,
        user: User,
        farm: Farm | None,
        recent_diagnoses: Sequence[Diagnosis],
        rag_context: str | None = None,
    ) -> str:
        sections = [
            FARMING_CHAT_SYSTEM_PROMPT,
            f"Current date: {date.today().isoformat()}",
            f"User preferred language: {user.preferred_language}",
        ]

        if farm is not None:
            sections.append(self._format_farm_context(farm))
        else:
            sections.append("Farm profile context: not provided for this chat session.")

        if recent_diagnoses:
            sections.append(self._format_diagnosis_context(recent_diagnoses))
        else:
            sections.append("Recent diagnosis context: none available.")

        if rag_context and rag_context.strip():
            sections.append(f"RAG/document context:\n{rag_context.strip()}")
        else:
            sections.append("RAG/document context: none provided.")

        return "\n\n".join(sections)

    def _format_farm_context(self, farm: Farm) -> str:
        values = [
            ("Farm name", farm.farm_name),
            ("Crop", farm.crop),
            ("Location", farm.location),
            ("Village", farm.village),
            ("District", farm.district),
            ("State", farm.state),
            ("Soil type", farm.soil_type),
            ("Land size acres", self._format_decimal(farm.land_size_acres)),
            ("Irrigation type", farm.irrigation_type),
            (
                "Sowing date",
                farm.sowing_date.isoformat() if farm.sowing_date else None,
            ),
        ]
        lines = ["Farm profile context:"]
        lines.extend(f"- {label}: {value}" for label, value in values if value)
        return "\n".join(lines)

    def _format_diagnosis_context(self, diagnoses: Sequence[Diagnosis]) -> str:
        lines = [
            "Recent diagnosis context:",
            "Treat this as historical context, not as a verified dosage or label source.",
        ]
        for index, diagnosis in enumerate(diagnoses, start=1):
            confidence = self._format_decimal(diagnosis.confidence_score)
            lines.append(
                f"{index}. {diagnosis.created_at.date().isoformat()} - "
                f"{diagnosis.disease_name}; severity {diagnosis.severity}; "
                f"confidence {confidence}; escalate_to_human {diagnosis.escalate_to_human}."
            )
            self._append_list(lines, "Possible causes", diagnosis.possible_causes)
            self._append_list(lines, "Organic treatment", diagnosis.organic_treatment)
            self._append_list(lines, "Chemical treatment", diagnosis.chemical_treatment)
            self._append_list(lines, "Prevention", diagnosis.prevention_steps)
        return "\n".join(lines)

    def _append_list(self, lines: list[str], label: str, values: Sequence[str]) -> None:
        if values:
            lines.append(f"   {label}: {', '.join(values[:5])}")

    def _format_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format(value.normalize(), "f")
