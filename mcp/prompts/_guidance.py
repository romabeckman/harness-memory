import json


def input_data(value: str | None) -> str:
    encoded = json.dumps(value, ensure_ascii=False)
    return f"<input-data>{encoded.replace('<', r'\\u003c').replace('>', r'\\u003e')}</input-data>"


def message(text: str) -> list[str]:
    return [text]
