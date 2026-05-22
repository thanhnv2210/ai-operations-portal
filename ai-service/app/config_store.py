"""File-backed in-memory store for admin configuration.

Persists to data/admin_config.json on every write.
No DB schema changes required for MVP.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent.parent / "data" / "admin_config.json"

_DEFAULTS: dict[str, Any] = {
    "thresholds": {
        "failure_rate_warning":           0.05,
        "failure_rate_critical":          0.10,
        "processing_time_warning_s":      300,
        "processing_time_critical_s":     600,
        "min_transaction_volume_per_day": 10,
    },
    "prompt_templates": [
        {
            "id": "tpl-summary",
            "name": "Operational Summary",
            "description": "Daily health summary sent to ops team",
            "template": (
                "Summarise the operational health for {{period}}. "
                "Highlight any hubs with failure rates above {{failure_rate_threshold}}% "
                "and any error codes appearing more than {{error_threshold}} times."
            ),
            "updated_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "tpl-anomaly",
            "name": "Anomaly Explanation",
            "description": "Explains a detected anomaly to the ops team",
            "template": (
                "Explain the following anomaly in plain English for an operations team: {{anomaly_description}}. "
                "Include likely root causes and suggested next steps. Do not include PII."
            ),
            "updated_at": "2026-01-01T00:00:00Z",
        },
        {
            "id": "tpl-trend",
            "name": "Trend Observation",
            "description": "Identifies trends over a rolling window",
            "template": (
                "Analyse transaction trends for the past {{window_days}} days. "
                "Identify volume growth/decline per hub, shifts in failure rates, "
                "and any emerging error patterns. Return a concise bullet-point report."
            ),
            "updated_at": "2026-01-01T00:00:00Z",
        },
    ],
}

# Module-level in-memory state
_store: dict[str, Any] = {}


def _load() -> None:
    global _store
    if _DATA_FILE.exists():
        try:
            _store = json.loads(_DATA_FILE.read_text())
            log.info("Admin config loaded from %s", _DATA_FILE)
            return
        except Exception as e:
            log.warning("Could not read admin config (%s), using defaults", e)
    _store = json.loads(json.dumps(_DEFAULTS))  # deep copy
    _save()


def _save() -> None:
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DATA_FILE.write_text(json.dumps(_store, indent=2))


def init() -> None:
    _load()


# --- Thresholds ---

def get_thresholds() -> dict[str, Any]:
    return dict(_store["thresholds"])


def update_thresholds(updates: dict[str, Any]) -> dict[str, Any]:
    _store["thresholds"].update(updates)
    _save()
    return get_thresholds()


# --- Prompt templates ---

def list_templates() -> list[dict]:
    return list(_store["prompt_templates"])


def get_template(template_id: str) -> dict | None:
    return next((t for t in _store["prompt_templates"] if t["id"] == template_id), None)


def create_template(name: str, description: str, template: str) -> dict:
    tpl = {
        "id": f"tpl-{uuid.uuid4().hex[:8]}",
        "name": name,
        "description": description,
        "template": template,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _store["prompt_templates"].append(tpl)
    _save()
    return tpl


def update_template(template_id: str, **kwargs: Any) -> dict | None:
    tpl = get_template(template_id)
    if tpl is None:
        return None
    tpl.update({k: v for k, v in kwargs.items() if v is not None})
    tpl["updated_at"] = datetime.now(timezone.utc).isoformat()
    _save()
    return tpl


def delete_template(template_id: str) -> bool:
    before = len(_store["prompt_templates"])
    _store["prompt_templates"] = [
        t for t in _store["prompt_templates"] if t["id"] != template_id
    ]
    if len(_store["prompt_templates"]) < before:
        _save()
        return True
    return False
