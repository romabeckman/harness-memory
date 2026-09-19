from datetime import datetime, timezone


def valid_payload(**overrides):
    payload = {
        "schema_version": "1.0",
        "project": {"key": "payments", "name": "Payments", "metadata": {}},
        "revision": 1,
        "generated_at": datetime(2026, 9, 17, 12, tzinfo=timezone.utc),
        "entities": [
            {"key": "payments-api", "type": "api", "name": "Payments API", "metadata": {}}
        ],
        "relations": [],
        "evidence": [],
    }
    payload.update(overrides)
    return payload
