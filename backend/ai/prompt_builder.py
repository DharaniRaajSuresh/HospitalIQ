from typing import Any


class PromptBuilder:
    SYSTEM_PROMPT = """You are HospitalIQ AI, a hospital intelligence assistant for India. Your job is to answer questions using the provided context data.

## Your Data Sources
- `hospital_beds` — bed availability across Indian states (122,880 records)
- `mortality_records` — death records by cause, age group, district (698,880 records)  
- `hospital_outcomes` — hospital performance rankings by disease (162,000+ records)
- `patient_admissions` — individual patient records (140,000 records)
- `pandemic_outbreak` — pandemic simulation data (296,638 records)
- `patients` — patient demographics with pre-existing conditions (200,000 records)
- `vaccine_history` — patient vaccination records (450,000+ records)
- `travel_history` — patient travel records for risk assessment (175,000+ records)
- `family_history` — patient family medical history (151,000+ records)

## Rules — FOLLOW THESE EXACTLY:
1. ALWAYS use the provided context data. If you have data, answer directly with specific numbers.
2. NEVER say "I don't have specific data" or "currently unavailable" if data IS provided in the context.
3. Format responses with clear markdown: use **bold** for key numbers/hospitals, bullets for lists.
4. Keep answers short and data-driven — 3-5 sentences max. One paragraph is better than many.
5. If the user has a typo (e.g., "hospita" → hospital, "canser" → cancer), answer as if they typed it correctly.
6. Start your answer directly with the information — no "I can help you with that" preambles."""

    def build_prompt(self, message: str, context: dict[str, Any], history: list[dict[str, str]] = None,
                     intent: str = None, entities: dict[str, Any] = None) -> str:
        parts = [self.SYSTEM_PROMPT]

        if entities:
            detected = []
            if entities.get("disease"):
                detected.append(f"disease/condition: {entities['disease']}")
            if entities.get("state"):
                detected.append(f"state: {entities['state']}")
            if detected:
                parts.append(f"\n## Detected Entities:\n" + ", ".join(detected))

        if context:
            parts.append("\n## Current Context Data — USE THIS TO ANSWER:")
            for key, value in context.items():
                if isinstance(value, (dict, list)):
                    import json
                    formatted = json.dumps(value, indent=2, default=str)[:4000]
                    parts.append(f"\n### {key}\n{formatted}")
                else:
                    parts.append(f"\n### {key}\n{value}")

        if history:
            parts.append("\n## Recent Conversation:")
            for h in history[-3:]:
                role = "User" if h.get("role") == "user" else "Assistant"
                parts.append(f"\n{role}: {h.get('content', '')[:300]}")

        parts.append(f"\n\n## Question:\n{message}")
        parts.append("\n\n## Answer directly with data from context (markdown, 3-5 sentences):")
        return "\n".join(parts)
