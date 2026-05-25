from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.db import DatabaseError

from core.constants import PLAN_BASIC, PLAN_MULTIBRANCH, PLAN_PRO, PLAN_STANDARD

_HOME_FILE_KEY = "\u0627\u0644\u0631\u0626\u064a\u0633\u064a\u0629"
_FEATURES_FILE_KEY = "\u0627\u0644\u062d\u0644\u0648\u0644"
_PRICING_FILE_KEY = "\u0627\u0644\u0628\u0627\u0642\u0627\u062a"


def _safe_item(items: list[str], index: int, fallback: str) -> str:
    """Return a list item safely with a fallback."""
    if index < len(items):
        return items[index]
    return fallback


@lru_cache(maxsize=1)
def _helping_data_payload() -> dict[str, dict[str, list[str]]]:
    """
    Load and cache marketing content from helping-data text files.

    Files are authored by the product team and provide Arabic marketing copy.
    """
    data_dir = Path(__file__).resolve().parents[1] / "helping-data"
    payload: dict[str, dict[str, list[str]]] = {
        "home": {"quotes": [], "actions": []},
        "features": {"quotes": [], "actions": []},
        "pricing": {"quotes": [], "actions": []},
    }
    if not data_dir.exists():
        return payload

    for file_path in data_dir.glob("*.txt"):
        key = None
        if _HOME_FILE_KEY in file_path.name:
            key = "home"
        elif _FEATURES_FILE_KEY in file_path.name:
            key = "features"
        elif _PRICING_FILE_KEY in file_path.name:
            key = "pricing"
        if key is None:
            continue

        content = file_path.read_text(encoding="utf-8-sig")
        quotes = [item.strip() for item in re.findall(r'"([^"]+)"', content) if item.strip()]
        actions = [item.strip() for item in re.findall(r"\[([^\]]+)\]", content) if item.strip()]
        payload[key] = {"quotes": quotes, "actions": actions}
    return payload


def _arabic_content() -> dict[str, Any]:
    data = _helping_data_payload()
    home_q = data["home"]["quotes"]
    home_a = data["home"]["actions"]
    features_q = data["features"]["quotes"]
    features_a = data["features"]["actions"]
    pricing_q = data["pricing"]["quotes"]

    return {
        "home": {
            "kicker": "\u0645\u0646\u0635\u0629 \u062a\u0634\u063a\u064a\u0644 \u0627\u0644\u0645\u0637\u0627\u0639\u0645",
            "title": _safe_item(
                home_q,
                0,
                "\u0642\u064f\u062f \u0645\u0637\u0639\u0645\u0643 \u0628\u0630\u0643\u0627\u0621.. \u0648\u0627\u062a\u0631\u0643 \u0644\u0646\u0627 \u062a\u0639\u0642\u064a\u062f\u0627\u062a \u0627\u0644\u0625\u062f\u0627\u0631\u0629.",
            ),
            "subtitle": _safe_item(
                home_q,
                1,
                "\u0645\u0646 \u0627\u0644\u0643\u0627\u0634\u064a\u0631 \u0625\u0644\u0649 \u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631\u060c \u0643\u0644 \u0639\u0645\u0644\u064a\u0627\u062a \u0645\u0637\u0639\u0645\u0643 \u0641\u064a \u0645\u0646\u0635\u0629 \u0648\u0627\u062d\u062f\u0629.",
            ),
            "primary_cta": _safe_item(home_a, 0, "\u0627\u0628\u062f\u0623 \u062a\u062c\u0631\u0628\u062a\u0643 \u0627\u0644\u0645\u062c\u0627\u0646\u064a\u0629"),
            "secondary_cta": _safe_item(home_a, 1, "\u0627\u062d\u062c\u0632 \u0639\u0631\u0636\u064b\u0627 \u062a\u0648\u0636\u064a\u062d\u064a\u064b\u0627"),
            "problem_title": _safe_item(home_q, 2, "\u0647\u0644 \u064a\u0633\u062a\u0647\u0644\u0643 \u0645\u0637\u0639\u0645\u0643 \u0648\u0642\u062a\u0643 \u0628\u062f\u0644\u0627\u064b \u0645\u0646 \u0623\u0646 \u064a\u0645\u0646\u062d\u0643 \u0627\u0644\u0623\u0631\u0628\u0627\u062d\u061f"),
            "problem_text": _safe_item(
                home_q,
                3,
                "\u0646\u062a\u064a\u062d \u0644\u0643 \u0631\u0624\u064a\u0629 \u0643\u0627\u0645\u0644\u0629 \u0644\u0644\u0645\u062e\u0632\u0648\u0646 \u0648\u0627\u0644\u0645\u0628\u064a\u0639\u0627\u062a \u0648\u0627\u0644\u062a\u062f\u0641\u0642 \u0627\u0644\u0645\u0627\u0644\u064a \u0641\u064a \u0648\u0642\u062a \u0641\u0639\u0644\u064a.",
            ),
            "solution_text": _safe_item(
                home_q,
                4,
                "\u0646\u0638\u0627\u0645 \u0648\u0627\u062d\u062f \u064a\u062f\u064a\u0631 \u0646\u0642\u0627\u0637 \u0627\u0644\u0628\u064a\u0639\u060c \u0627\u0644\u0645\u062e\u0632\u0648\u0646\u060c \u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631\u060c \u0648\u0627\u0644\u0637\u0628\u0627\u0639\u0629 \u0628\u062f\u0648\u0646 \u062a\u0639\u0642\u064a\u062f.",
            ),
            "highlights": [
                _safe_item(home_q, 5, "\u0643\u0627\u0634\u064a\u0631 \u064a\u0639\u0645\u0644 \u062d\u062a\u0649 \u0639\u0646\u062f \u0627\u0646\u0642\u0637\u0627\u0639 \u0627\u0644\u0627\u062a\u0635\u0627\u0644."),
                _safe_item(home_q, 6, "\u062e\u0635\u0645 \u0627\u0644\u0645\u0643\u0648\u0646\u0627\u062a \u062a\u0644\u0642\u0627\u0626\u064a\u064b\u0627 \u0645\u0639 \u0643\u0644 \u0637\u0644\u0628."),
                _safe_item(home_q, 7, "\u062a\u062d\u0644\u064a\u0644\u0627\u062a \u0641\u0648\u0631\u064a\u0629 \u0644\u0644\u0641\u0631\u0648\u0639 \u0648\u0627\u0644\u0645\u0646\u062a\u062c\u0627\u062a."),
                _safe_item(home_q, 9, "\u0634\u0627\u0634\u0627\u062a \u0645\u0637\u0628\u062e \u0631\u0642\u0645\u064a\u0629 \u062a\u0642\u0644\u0644 \u0627\u0644\u062a\u0623\u062e\u064a\u0631."),
            ],
            "metrics": [
                _safe_item(home_q, 10, "\u062a\u062d\u0633\u064a\u0646 \u0647\u062f\u0631 \u0627\u0644\u0645\u062e\u0632\u0648\u0646 \u0628\u0646\u0633\u0628\u0629 \u0643\u0628\u064a\u0631\u0629."),
                _safe_item(home_q, 11, "\u0631\u0641\u0639 \u0633\u0631\u0639\u0629 \u0627\u0644\u062e\u062f\u0645\u0629 \u0641\u064a \u0623\u0648\u0642\u0627\u062a \u0627\u0644\u0630\u0631\u0648\u0629."),
                _safe_item(home_q, 12, "\u064a\u0639\u062a\u0645\u062f \u0639\u0644\u064a\u0646\u0627 \u0639\u062f\u062f \u0643\u0628\u064a\u0631 \u0645\u0646 \u0627\u0644\u0639\u0644\u0627\u0645\u0627\u062a."),
            ],
            "final_title": _safe_item(
                home_q,
                17,
                "\u0647\u0644 \u0623\u0646\u062a \u0645\u0633\u062a\u0639\u062f \u0644\u062a\u0646\u0638\u064a\u0645 \u0645\u0637\u0639\u0645\u0643 \u0648\u0632\u064a\u0627\u062f\u0629 \u0623\u0631\u0628\u0627\u062d\u0643\u061f",
            ),
            "final_text": _safe_item(
                home_q,
                18,
                "\u0627\u0628\u062f\u0623 \u0627\u0644\u064a\u0648\u0645 \u0648\u062d\u0648\u0644 \u0625\u062f\u0627\u0631\u0629 \u0645\u0637\u0639\u0645\u0643 \u0625\u0644\u0649 \u0646\u0638\u0627\u0645 \u0645\u0646\u0638\u0645 \u0648\u0642\u0627\u0628\u0644 \u0644\u0644\u062a\u0648\u0633\u0639.",
            ),
            "final_cta": _safe_item(home_a, 2, "\u0627\u0628\u062f\u0623 \u0631\u062d\u0644\u0629 \u0627\u0644\u0646\u062c\u0627\u062d \u0627\u0644\u0622\u0646"),
            "trust_points": [
                "\u062a\u0634\u063a\u064a\u0644 \u0645\u062a\u0635\u0644 \u0648\u0623\u0648\u0641\u0644\u0627\u064a\u0646 \u0645\u0639 \u0645\u0632\u0627\u0645\u0646\u0629 \u0630\u0643\u064a\u0629.",
                "\u062d\u0645\u0627\u064a\u0629 \u0648\u0646\u0633\u062e \u0627\u062d\u062a\u064a\u0627\u0637\u064a \u064a\u0648\u0645\u064a.",
                "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0645\u062a\u0639\u062f\u062f\u0629 \u0644\u0644\u0641\u0631\u0648\u0639 \u0648\u0625\u062f\u0627\u0631\u0629 \u0645\u0631\u0643\u0632\u064a\u0629.",
                "\u062f\u0639\u0645 \u0633\u0631\u064a\u0639 \u0648\u062a\u0648\u0627\u0635\u0644 \u0645\u0628\u0627\u0634\u0631 \u0645\u0639 \u0627\u0644\u0641\u0631\u064a\u0642.",
            ],
            "screens": [
                {
                    "title": "\u0634\u0627\u0634\u0629 \u0627\u0644\u0643\u0627\u0634\u064a\u0631",
                    "text": "\u0648\u0627\u062c\u0647\u0629 \u0644\u0645\u0633 \u0633\u0631\u064a\u0639\u0629 \u0648\u0645\u0631\u0646\u0629 \u0645\u0635\u0645\u0645\u0629 \u0644\u0644\u0623\u064a\u0628\u0627\u062f.",
                    "image": "undraw_posting_photo.svg",
                },
                {
                    "title": "\u0634\u0627\u0634\u0629 \u0627\u0644\u0645\u0637\u0628\u062e",
                    "text": "\u062a\u0631\u062a\u064a\u0628 \u0627\u0644\u0637\u0644\u0628\u0627\u062a \u0628\u0645\u0631\u0627\u062d\u0644 \u062a\u062d\u0636\u064a\u0631 \u0648\u0645\u0624\u0642\u062a\u0627\u062a \u0648\u0627\u0636\u062d\u0629.",
                    "image": "undraw_profile_1.svg",
                },
                {
                    "title": "\u0644\u0648\u062d\u0629 \u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631",
                    "text": "\u062a\u062d\u0644\u064a\u0644 \u0627\u0644\u0623\u062f\u0627\u0621 \u0648\u0627\u0644\u0641\u0631\u0648\u0639 \u0641\u064a \u0644\u062d\u0638\u0627\u062a.",
                    "image": "undraw_rocket.svg",
                },
            ],
            "testimonials": [
                {
                    "name": "\u0645\u062d\u0645\u062f \u064a\u0627\u0633\u0631",
                    "role": "\u0645\u0627\u0644\u0643 \u0645\u0637\u0639\u0645",
                    "text": "\u0623\u0635\u0628\u062d\u0646\u0627 \u0646\u0631\u0649 \u0643\u0644 \u0634\u064a\u0621 \u0628\u0633\u0647\u0648\u0644\u0629 \u0628\u062f\u0648\u0646 \u062a\u0639\u0642\u064a\u062f.",
                },
                {
                    "name": "\u0631\u064a\u0645 \u0641\u0648\u0627\u0632",
                    "role": "\u0645\u062f\u064a\u0631\u0629 \u0641\u0631\u0639",
                    "text": "\u0627\u0644\u0643\u0627\u0634\u064a\u0631 \u0648\u0627\u0644\u0645\u0637\u0628\u062e \u0623\u0635\u0628\u062d\u0627 \u0645\u0631\u062a\u0628\u064a\u0646 \u0648\u0627\u0644\u0637\u0644\u0628\u0627\u062a \u062a\u0633\u0644\u064a\u0645 \u0623\u0633\u0631\u0639.",
                },
                {
                    "name": "\u0647\u0627\u0646\u064a \u0633\u0639\u062f",
                    "role": "\u0645\u062d\u0627\u0633\u0628",
                    "text": "\u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631 \u0623\u0635\u0628\u062d\u062a \u062a\u0648\u0641\u0631 \u0648\u0642\u062a\u064a \u0648\u062a\u062c\u0645\u0639 \u0643\u0644 \u0627\u0644\u0623\u0631\u0642\u0627\u0645.",
                },
            ],
        },
        "features": {
            "title": _safe_item(
                features_q,
                0,
                "\u062d\u0644\u0648\u0644 \u0630\u0643\u064a\u0629 \u0648\u0634\u0627\u0645\u0644\u0629 \u0645\u0635\u0645\u0645\u0629 \u0644\u0646\u0645\u0648 \u0623\u0639\u0645\u0627\u0644\u0643.",
            ),
            "subtitle": _safe_item(
                features_q,
                1,
                "\u0628\u064a\u0626\u0629 \u0639\u0645\u0644 \u0645\u062a\u0643\u0627\u0645\u0644\u0629 \u062a\u0631\u0628\u0637 \u0627\u0644\u0628\u064a\u0639 \u0648\u0627\u0644\u0645\u062e\u0632\u0648\u0646 \u0648\u0627\u0644\u0641\u0631\u064a\u0642 \u0648\u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631.",
            ),
            "cards": [
                {
                    "title": "\u0646\u0642\u0637\u0629 \u0628\u064a\u0639 \u0633\u062d\u0627\u0628\u064a\u0629",
                    "text": _safe_item(features_q, 2, "\u0623\u062f\u0627\u0621 \u0633\u0631\u064a\u0639 \u0648\u0648\u0627\u062c\u0647\u0629 \u0645\u0631\u0646\u0629 \u0644\u0644\u0643\u0627\u0634\u064a\u0631."),
                },
                {
                    "title": "\u0625\u062f\u0627\u0631\u0629 \u0645\u062e\u0632\u0648\u0646 \u0645\u062a\u0642\u062f\u0645\u0629",
                    "text": _safe_item(features_q, 4, "\u0627\u0644\u0633\u064a\u0637\u0631\u0629 \u0639\u0644\u0649 \u0627\u0644\u0645\u062e\u0632\u0648\u0646 \u0648\u062a\u0642\u0644\u064a\u0644 \u0627\u0644\u0647\u062f\u0631."),
                },
                {
                    "title": "\u0627\u0644\u062a\u062d\u0644\u064a\u0644 \u0648\u0627\u062a\u062e\u0627\u0630 \u0627\u0644\u0642\u0631\u0627\u0631",
                    "text": _safe_item(features_q, 7, "\u062a\u0642\u0627\u0631\u064a\u0631 \u062a\u0648\u0636\u062d \u0646\u0642\u0627\u0637 \u0627\u0644\u0642\u0648\u0629 \u0648\u0627\u0644\u0636\u0639\u0641 \u0641\u064a \u0627\u0644\u0623\u062f\u0627\u0621."),
                },
                {
                    "title": "\u0627\u0644\u0645\u0637\u0628\u062e \u0648\u0641\u0631\u064a\u0642 \u0627\u0644\u0639\u0645\u0644",
                    "text": _safe_item(features_q, 11, "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0641\u0631\u0642 \u0648\u0627\u0644\u0645\u0647\u0627\u0645 \u0628\u0634\u0643\u0644 \u0623\u0643\u062b\u0631 \u0641\u0627\u0639\u0644\u064a\u0629."),
                },
            ],
            "closing_title": _safe_item(features_q, 12, "\u0627\u0644\u062d\u0644 \u0627\u0644\u0645\u062a\u0643\u0627\u0645\u0644 \u0628\u0627\u0646\u062a\u0638\u0627\u0631\u0643."),
            "closing_text": _safe_item(features_q, 13, "\u0627\u0628\u062f\u0623 \u0627\u0644\u064a\u0648\u0645 \u0648\u0637\u0648\u0631 \u0639\u0645\u0644\u064a\u0627\u062a \u0645\u0637\u0639\u0645\u0643."),
            "closing_cta": _safe_item(features_a, 0, "\u0627\u0637\u0644\u0628 \u0627\u0633\u062a\u0634\u0627\u0631\u0629 \u0645\u062c\u0627\u0646\u064a\u0629"),
            "workflow_steps": [
                "\u0627\u0633\u062a\u064a\u0631\u0627\u062f \u0642\u0627\u0626\u0645\u0629 \u0627\u0644\u0623\u0635\u0646\u0627\u0641 \u0648\u0625\u0639\u062f\u0627\u062f \u0627\u0644\u0641\u0631\u0648\u0639.",
                "\u062a\u062f\u0631\u064a\u0628 \u0627\u0644\u0643\u0627\u0634\u064a\u0631 \u0648\u0627\u0644\u0641\u0631\u064a\u0642 \u0639\u0644\u0649 \u0648\u0627\u062c\u0647\u0629 \u0648\u0627\u062d\u062f\u0629.",
                "\u0628\u062f\u0621 \u0627\u0644\u062a\u0634\u063a\u064a\u0644 \u0648\u0645\u062a\u0627\u0628\u0639\u0629 \u0627\u0644\u0623\u062f\u0627\u0621 \u0645\u0646 \u0644\u0648\u062d\u0629 \u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631.",
            ],
            "module_points": [
                "\u0646\u0642\u0637\u0629 \u0628\u064a\u0639 \u0645\u062a\u0643\u0627\u0645\u0644\u0629 \u0645\u0639 \u0627\u0644\u0645\u0637\u0628\u062e.",
                "\u0623\u062f\u0627\u0629 \u0645\u062e\u0632\u0648\u0646 \u0648\u0645\u0648\u0631\u062f\u064a\u0646 \u0648\u062a\u0642\u0627\u0631\u064a\u0631 \u062a\u0643\u0627\u0644\u064a\u0641.",
                "\u0644\u0648\u062d\u0629 \u062a\u0642\u0627\u0631\u064a\u0631 \u0648\u0645\u0642\u0627\u0631\u0646\u0627\u062a \u0641\u0631\u0648\u0639.",
            ],
        },
        "pricing": {
            "title": _safe_item(
                pricing_q,
                0,
                "\u0627\u062e\u062a\u0631 \u0627\u0644\u0628\u0627\u0642\u0629 \u0627\u0644\u062a\u064a \u062a\u0645\u0646\u062d \u0645\u0637\u0639\u0645\u0643 \u0622\u0641\u0627\u0642\u064b\u0627 \u062c\u062f\u064a\u062f\u0629.",
            ),
            "subtitle": _safe_item(
                pricing_q,
                1,
                "\u062e\u0637\u0637 \u0633\u0639\u0631\u064a\u0629 \u0634\u0641\u0627\u0641\u0629 \u0645\u0635\u0645\u0645\u0629 \u062d\u0633\u0628 \u062d\u062c\u0645 \u0645\u0634\u0631\u0648\u0639\u0643.",
            ),
            "plan_badges": {
                PLAN_BASIC: _safe_item(pricing_q, 2, "\u0627\u0646\u0637\u0644\u0627\u0642"),
                PLAN_STANDARD: _safe_item(pricing_q, 4, "\u0646\u0645\u0648"),
                PLAN_MULTIBRANCH: _safe_item(pricing_q, 7, "\u0627\u0644\u0627\u062d\u062a\u0631\u0627\u0641"),
                PLAN_PRO: _safe_item(pricing_q, 7, "\u0627\u0644\u0627\u062d\u062a\u0631\u0627\u0641"),
            },
            "plan_descriptions": {
                PLAN_BASIC: _safe_item(pricing_q, 3, "\u0643\u0644 \u0645\u0627 \u062a\u062d\u062a\u0627\u062c\u0647 \u0644\u0644\u0627\u0646\u0637\u0644\u0627\u0642."),
                PLAN_STANDARD: _safe_item(pricing_q, 5, "\u062a\u062d\u0643\u0645 \u062f\u0642\u064a\u0642 \u0641\u064a \u0627\u0644\u0645\u062e\u0632\u0648\u0646 \u0648\u0627\u0644\u062a\u0643\u0627\u0644\u064a\u0641."),
                PLAN_MULTIBRANCH: _safe_item(pricing_q, 8, "\u062a\u0648\u0633\u0639 \u0645\u0631\u0646 \u0648\u0625\u062f\u0627\u0631\u0629 \u0645\u0631\u0643\u0632\u064a\u0629 \u0644\u0644\u0641\u0631\u0648\u0639."),
                PLAN_PRO: _safe_item(pricing_q, 8, "\u062a\u0648\u0633\u0639 \u0645\u0631\u0646 \u0648\u0625\u062f\u0627\u0631\u0629 \u0645\u0631\u0643\u0632\u064a\u0629 \u0644\u0644\u0641\u0631\u0648\u0639."),
            },
            "faqs": [
                _safe_item(pricing_q, 10, "\u0644\u0627 \u062a\u0648\u062c\u062f \u0631\u0633\u0648\u0645 \u0645\u062e\u0641\u064a\u0629."),
                _safe_item(pricing_q, 11, "\u064a\u0645\u0643\u0646\u0643 \u0627\u0644\u062a\u0631\u0642\u064a\u0629 \u0628\u064a\u0646 \u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0641\u064a \u0623\u064a \u0648\u0642\u062a."),
                _safe_item(pricing_q, 12, "\u064a\u062a\u0648\u0641\u0631 \u062e\u0635\u0645 \u0644\u0644\u0627\u0634\u062a\u0631\u0627\u0643 \u0627\u0644\u0633\u0646\u0648\u064a."),
            ],
            "money_back": _safe_item(pricing_q, 13, "\u0636\u0645\u0627\u0646 \u0627\u0633\u062a\u0631\u062f\u0627\u062f \u062e\u0644\u0627\u0644 15 \u064a\u0648\u0645\u064b\u0627."),
            "closing_cta": _safe_item(pricing_q, 14, "\u0627\u0633\u062a\u062b\u0645\u0631 \u0641\u064a \u0645\u0633\u062a\u0642\u0628\u0644 \u0645\u0637\u0639\u0645\u0643 \u0627\u0644\u064a\u0648\u0645."),
            "comparison_rows": [
                {"label": "\u0627\u0644\u0643\u0627\u0634\u064a\u0631 \u0648\u0627\u0644\u0645\u0637\u0628\u062e", "values": {PLAN_BASIC: True, PLAN_STANDARD: True, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
                {"label": "\u0625\u062f\u0627\u0631\u0629 \u0627\u0644\u0645\u062e\u0632\u0648\u0646 \u0627\u0644\u0645\u062a\u0642\u062f\u0645\u0629", "values": {PLAN_BASIC: False, PLAN_STANDARD: True, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
                {"label": "\u062a\u062d\u0644\u064a\u0644 \u0627\u0644\u0641\u0631\u0648\u0639 \u0648\u0627\u0644\u0645\u0642\u0627\u0631\u0646\u0629", "values": {PLAN_BASIC: False, PLAN_STANDARD: False, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
                {"label": "\u0645\u0648\u0627\u0631\u062f \u0628\u0634\u0631\u064a\u0629 \u0648\u0625\u062f\u0627\u0631\u0629 \u0645\u0648\u0638\u0641\u064a\u0646", "values": {PLAN_BASIC: False, PLAN_STANDARD: False, PLAN_MULTIBRANCH: False, PLAN_PRO: True}},
                {"label": "\u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631 \u0627\u0644\u0645\u062a\u0642\u062f\u0645\u0629", "values": {PLAN_BASIC: False, PLAN_STANDARD: True, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
            ],
        },
    }


def _english_content() -> dict[str, Any]:
    return {
        "home": {
            "kicker": "Restaurant Operations Platform",
            "title": "Run your restaurant with confidence, not chaos.",
            "subtitle": (
                "From POS checkout to inventory, analytics, printing, subscriptions, and branch operations, "
                "Restoraq centralizes your workflow in one system."
            ),
            "primary_cta": "Start Free Trial",
            "secondary_cta": "Book a Live Demo",
            "problem_title": "Is your restaurant consuming your time instead of growing your profit?",
            "problem_text": (
                "Stock surprises, manual paperwork, and missing visibility hurt daily operations and margin."
            ),
            "solution_text": (
                "Restoraq connects POS, stock, payments, reports, and branch management in one control center."
            ),
            "highlights": [
                "POS continues when the internet is down, with automatic sync later.",
                "Recipe-based consumption and low-stock alerts protect margins.",
                "Live dashboards track branch performance, staff output, and best sellers.",
                "Kitchen Display workflows replace paper ticket chaos.",
            ],
            "metrics": [
                "Reduce inventory waste with tighter stock discipline.",
                "Increase service speed and turnover during peak hours.",
                "Built to support single branches and multi-branch operators.",
            ],
            "final_title": "Ready to scale your restaurant operations?",
            "final_text": "Launch quickly, train your team fast, and keep full control as you grow.",
            "final_cta": "Launch With Restoraq",
            "trust_points": [
                "Offline-ready POS with automatic sync.",
                "Daily backups and secure cloud storage.",
                "Multi-branch control from one dashboard.",
                "Responsive support for busy operators.",
            ],
            "screens": [
                {
                    "title": "Cashier Terminal",
                    "text": "Tablet-first checkout with fast product search.",
                    "image": "undraw_posting_photo.svg",
                },
                {
                    "title": "Kitchen Display",
                    "text": "Live ticket flow with prep status tracking.",
                    "image": "undraw_profile_1.svg",
                },
                {
                    "title": "Analytics Dashboard",
                    "text": "Actionable metrics for sales, stock, and staff.",
                    "image": "undraw_rocket.svg",
                },
            ],
            "testimonials": [
                {
                    "name": "Omar Adel",
                    "role": "Restaurant Owner",
                    "text": "We finally see sales, stock, and team performance in one place.",
                },
                {
                    "name": "Lamia Saeed",
                    "role": "Branch Manager",
                    "text": "Kitchen status and cashier flow are smooth, even on busy nights.",
                },
                {
                    "name": "Karim Nabil",
                    "role": "Finance Lead",
                    "text": "Reports are clear and save us hours every week.",
                },
            ],
        },
        "features": {
            "title": "Smart, connected solutions for every restaurant department.",
            "subtitle": (
                "We do not provide isolated tools. We provide an operating layer that keeps cashiers, kitchen, "
                "inventory, and management in sync."
            ),
            "cards": [
                {
                    "title": "Cloud POS & Checkout",
                    "text": "Fast cashier workflows, tablet-ready UX, and resilient offline operations.",
                },
                {
                    "title": "Inventory Intelligence",
                    "text": "Track ingredients, automate deductions from recipes, and catch low stock early.",
                },
                {
                    "title": "Reporting & Performance",
                    "text": "See branch KPIs, sales patterns, and product performance in clear dashboards.",
                },
                {
                    "title": "Kitchen & Team Operations",
                    "text": "KDS-ready workflows, role-based access, and operational accountability.",
                },
            ],
            "closing_title": "One complete operating system.",
            "closing_text": "Start with what you need today and unlock advanced modules as you grow.",
            "closing_cta": "Request Free Consultation",
            "workflow_steps": [
                "Import your menu, setup branches, and connect printers.",
                "Train cashiers and kitchen staff on one unified interface.",
                "Monitor performance from live dashboards and reports.",
            ],
            "module_points": [
                "Unified POS, kitchen display, and order flow.",
                "Inventory, suppliers, and recipes in one control panel.",
                "Executive reporting across branches and teams.",
            ],
        },
        "pricing": {
            "title": "Choose a plan that matches your growth stage.",
            "subtitle": "Clear pricing, no hidden fees, and upgrades whenever you need.",
            "plan_badges": {
                PLAN_BASIC: "Start",
                PLAN_STANDARD: "Grow",
                PLAN_MULTIBRANCH: "Scale",
                PLAN_PRO: "Enterprise",
            },
            "plan_descriptions": {
                PLAN_BASIC: "Everything needed for a streamlined launch.",
                PLAN_STANDARD: "Advanced inventory and reporting for tighter control.",
                PLAN_MULTIBRANCH: "Centralized management for multi-branch operations.",
                PLAN_PRO: "Full modules, deeper analytics, and enterprise-level control.",
            },
            "faqs": [
                "No hidden charges. You only pay the listed subscription amount.",
                "You can upgrade your plan at any time without losing data.",
                "Annual subscriptions can include discounted terms.",
            ],
            "money_back": "Money-back guarantee within the first 15 days.",
            "closing_cta": "Invest in operational clarity and sustainable growth.",
            "comparison_rows": [
                {"label": "POS & Kitchen Display", "values": {PLAN_BASIC: True, PLAN_STANDARD: True, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
                {"label": "Advanced Inventory", "values": {PLAN_BASIC: False, PLAN_STANDARD: True, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
                {"label": "Branch Comparison", "values": {PLAN_BASIC: False, PLAN_STANDARD: False, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
                {"label": "HR & Payroll", "values": {PLAN_BASIC: False, PLAN_STANDARD: False, PLAN_MULTIBRANCH: False, PLAN_PRO: True}},
                {"label": "Advanced Reports", "values": {PLAN_BASIC: False, PLAN_STANDARD: True, PLAN_MULTIBRANCH: True, PLAN_PRO: True}},
            ],
        },
    }


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _strip_html(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value or "").strip()


def _shorten_text(value: str, max_len: int = 120) -> str:
    cleaned = _strip_html(value)
    if len(cleaned) <= max_len:
        return cleaned
    sentence_breaks = [".", "!", "?", "؟", "،", ";", "؛", "\n"]
    for marker in sentence_breaks:
        idx = cleaned.find(marker)
        if 0 < idx <= max_len:
            return cleaned[: idx + 1].strip()
    trimmed = cleaned[:max_len].rstrip()
    if " " in trimmed:
        trimmed = trimmed.rsplit(" ", 1)[0]
    return trimmed.strip()


def _parse_keyed_lines(value: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in _split_lines(value):
        if "|" not in line:
            continue
        key, content = line.split("|", 1)
        key = key.strip().lower()
        content = content.strip()
        if key and content:
            mapping[key] = content
    return mapping


def _parse_feature_cards(value: str) -> list[dict[str, str]]:
    cards: list[dict[str, str]] = []
    for line in _split_lines(value):
        if "|" in line:
            title, text = line.split("|", 1)
            cards.append({"title": title.strip(), "text": text.strip()})
        else:
            cards.append({"title": line.strip(), "text": ""})
    return cards


def _apply_home_page_override(content: dict[str, Any], language_code: str) -> dict[str, Any]:
    from core.models import HomePageContent

    try:
        override = HomePageContent.objects.filter(language=language_code).first()
    except DatabaseError:
        return content
    if not override:
        return content

    updated = dict(content)
    mapping = {
        "kicker": override.kicker,
        "title": override.title,
        "subtitle": override.subtitle,
        "primary_cta": override.primary_cta,
        "secondary_cta": override.secondary_cta,
        "problem_title": override.problem_title,
        "problem_text": override.problem_text,
        "solution_text": override.solution_text,
        "final_title": override.final_title,
        "final_text": override.final_text,
        "final_cta": override.final_cta,
    }
    for key, value in mapping.items():
        if value:
            updated[key] = value

    if override.highlights:
        updated["highlights"] = _split_lines(override.highlights)
    if override.metrics:
        updated["metrics"] = _split_lines(override.metrics)

    return updated


def _apply_features_page_override(content: dict[str, Any], language_code: str) -> dict[str, Any]:
    from core.models import FeaturesPageContent

    try:
        override = FeaturesPageContent.objects.filter(language=language_code).first()
    except DatabaseError:
        return content
    if not override:
        return content

    updated = dict(content)
    mapping = {
        "title": override.title,
        "subtitle": override.subtitle,
        "closing_title": override.closing_title,
        "closing_text": override.closing_text,
        "closing_cta": override.closing_cta,
    }
    for key, value in mapping.items():
        if value:
            updated[key] = value
    if override.cards:
        updated["cards"] = _parse_feature_cards(override.cards)
    return updated


def _apply_pricing_page_override(content: dict[str, Any], language_code: str) -> dict[str, Any]:
    from core.models import PricingPageContent

    try:
        override = PricingPageContent.objects.filter(language=language_code).first()
    except DatabaseError:
        return content
    if not override:
        return content

    updated = dict(content)
    mapping = {
        "title": override.title,
        "subtitle": override.subtitle,
        "money_back": override.money_back,
        "closing_cta": override.closing_cta,
    }
    for key, value in mapping.items():
        if value:
            updated[key] = value

    if override.faq_items:
        updated["faqs"] = _split_lines(override.faq_items)
    if override.plan_badges:
        badges = _parse_keyed_lines(override.plan_badges)
        if badges:
            merged_badges = dict(updated.get("plan_badges", {}))
            merged_badges.update(badges)
            updated["plan_badges"] = merged_badges
    if override.plan_descriptions:
        descriptions = _parse_keyed_lines(override.plan_descriptions)
        if descriptions:
            merged_desc = dict(updated.get("plan_descriptions", {}))
            merged_desc.update(descriptions)
            updated["plan_descriptions"] = merged_desc

    return updated


def _resolve_slide_image(value: str) -> str:
    if not value:
        return ""
    value = value.strip()
    if value.startswith("http://") or value.startswith("https://") or value.startswith("/"):
        return value
    return f"/static/{value}"


def get_marketing_slides(language: str, fallback: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    from core.models import MarketingSlide

    language_code = "ar" if str(language).startswith("ar") else "en"
    try:
        slides_qs = MarketingSlide.objects.filter(language=language_code, is_active=True).order_by("order", "id")
    except DatabaseError:
        slides_qs = MarketingSlide.objects.none()

    slides = [
        {
            "title": _shorten_text(slide.title, 80),
            "subtitle": _shorten_text(slide.subtitle, 120),
            "cta_text": slide.cta_text,
            "cta_url": slide.cta_url,
            "image": _resolve_slide_image(slide.image_path),
        }
        for slide in slides_qs
    ]

    if slides:
        return slides

    home = fallback or {}
    return [
        {
            "title": home.get("title_short") or home.get("title", ""),
            "subtitle": home.get("subtitle_short") or "",
            "cta_text": home.get("primary_cta", ""),
            "cta_url": "/accounts/login/",
            "image": "/static/img/undraw_posting_photo.svg",
        },
        {
            "title": home.get("problem_title_short") or home.get("problem_title", ""),
            "subtitle": home.get("problem_text_short") or "",
            "cta_text": home.get("secondary_cta", ""),
            "cta_url": "/features/",
            "image": "/static/img/undraw_profile_1.svg",
        },
        {
            "title": home.get("final_title_short") or home.get("final_title", ""),
            "subtitle": home.get("final_text_short") or "",
            "cta_text": home.get("final_cta", ""),
            "cta_url": "/accounts/login/",
            "image": "/static/img/undraw_rocket.svg",
        },
    ]


def get_marketing_content(language: str) -> dict[str, Any]:
    """Return localized content for public marketing pages."""
    language_code = "ar" if str(language).startswith("ar") else "en"
    content = _arabic_content() if language_code == "ar" else _english_content()

    content["home"] = _apply_home_page_override(content["home"], language_code)
    content["features"] = _apply_features_page_override(content["features"], language_code)
    content["pricing"] = _apply_pricing_page_override(content["pricing"], language_code)
    home = content["home"]
    home["title_short"] = _shorten_text(home.get("title", ""), 72)
    home["subtitle_short"] = _shorten_text(home.get("subtitle", ""), 120)
    home["problem_title_short"] = _shorten_text(home.get("problem_title", ""), 80)
    home["problem_text_short"] = _shorten_text(home.get("problem_text", ""), 120)
    home["solution_text_short"] = _shorten_text(home.get("solution_text", ""), 120)
    home["final_title_short"] = _shorten_text(home.get("final_title", ""), 80)
    home["final_text_short"] = _shorten_text(home.get("final_text", ""), 120)
    return content
