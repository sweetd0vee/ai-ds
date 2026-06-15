"""Парсинг и форматирование гипотез о данных из ответа LLM."""

from __future__ import annotations

import json
import re

_PRIORITY_ALIASES = {
    "high": "high",
    "высокий": "high",
    "высокая": "high",
    "высокое": "high",
    "medium": "medium",
    "средний": "medium",
    "средняя": "medium",
    "среднее": "medium",
    "low": "low",
    "низкий": "low",
    "низкая": "low",
    "низкое": "low",
}

_PRIORITY_LABELS = {
    "high": "высокий",
    "medium": "средний",
    "low": "низкий",
}


def _normalize_priority(value) -> str:
    key = str(value or "medium").strip().lower()
    return _PRIORITY_ALIASES.get(key, "medium")


def _normalize_hypothesis(item: dict, index: int) -> dict | None:
    if not isinstance(item, dict):
        return None

    title = str(item.get("title") or item.get("name") or "").strip()
    statement = str(item.get("statement") or item.get("formulation") or "").strip()
    rationale = str(item.get("rationale") or item.get("basis") or item.get("evidence") or "").strip()
    verification = str(
        item.get("verification") or item.get("how_to_test") or item.get("test") or ""
    ).strip()

    if not any((title, statement, rationale)):
        return None

    columns = item.get("columns") or item.get("fields") or []
    if isinstance(columns, str):
        columns = [c.strip() for c in re.split(r"[,;]", columns) if c.strip()]
    elif not isinstance(columns, list):
        columns = []

    priority = _normalize_priority(item.get("priority"))

    return {
        "id": int(item.get("id") or index + 1),
        "title": title or f"Гипотеза {index + 1}",
        "statement": statement,
        "rationale": rationale,
        "columns": [str(c).strip() for c in columns if str(c).strip()],
        "verification": verification,
        "priority": priority,
        "priority_label": _PRIORITY_LABELS[priority],
    }


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\s*```\s*$", "", stripped)
    return stripped


def _slice_between_markers(text: str) -> str:
    cleaned = _strip_code_fences(text)
    lower = cleaned.lower()

    start = 0
    for marker in ("---json---", "---hypotheses_start---"):
        idx = lower.find(marker)
        if idx != -1:
            start = max(start, idx + len(marker))

    fragment = cleaned[start:]
    end_match = re.search(r"---HYPOTHESES_END---", fragment, re.IGNORECASE)
    if end_match:
        fragment = fragment[: end_match.start()]
    return fragment.strip()


def _scan_json_string(text: str, i: int) -> int:
    """Пропускает JSON-строку, начиная с кавычки в позиции i. Возвращает индекс после закрывающей кавычки."""
    if i >= len(text) or text[i] != '"':
        return i
    i += 1
    escape = False
    while i < len(text):
        ch = text[i]
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == '"':
            return i + 1
        i += 1
    return len(text)


def _find_balanced_span(text: str, start: int, open_ch: str, close_ch: str) -> int | None:
    """Возвращает индекс символа сразу после закрывающей скобки или None, если фрагмент обрезан."""
    if start >= len(text) or text[start] != open_ch:
        return None

    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch == '"':
            i = _scan_json_string(text, i)
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _try_load_json_array(fragment: str) -> list | None:
    arr_start = fragment.find("[")
    if arr_start == -1:
        return None

    arr_end = _find_balanced_span(fragment, arr_start, "[", "]")
    if arr_end is None:
        return None

    try:
        data = json.loads(fragment[arr_start:arr_end])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def _extract_complete_objects(fragment: str) -> list[dict]:
    """Извлекает полностью закрытые JSON-объекты из обрезанного массива."""
    objects: list[dict] = []
    i = 0
    while i < len(fragment):
        if fragment[i] != "{":
            i += 1
            continue
        end = _find_balanced_span(fragment, i, "{", "}")
        if end is None:
            break
        try:
            obj = json.loads(fragment[i:end])
            if isinstance(obj, dict):
                objects.append(obj)
        except json.JSONDecodeError:
            pass
        i = end
    return objects


def _extract_json_array(text: str) -> list | None:
    fragment = _slice_between_markers(text)

    data = _try_load_json_array(fragment)
    if isinstance(data, list) and data:
        return data

    # Обрезанный или битый массив — берём только завершённые объекты
    objects = _extract_complete_objects(fragment)
    if objects:
        return objects

    # Запасной путь: любой фрагмент с '[' в исходном тексте
    for source in (fragment, text):
        arr_start = source.find("[")
        if arr_start == -1:
            continue
        objects = _extract_complete_objects(source[arr_start:])
        if objects:
            return objects

    return None


def parse_hypotheses(raw: str) -> list[dict]:
    if not raw or not str(raw).strip():
        return []

    data = _extract_json_array(str(raw).strip())
    if not isinstance(data, list):
        return []

    result: list[dict] = []
    for index, item in enumerate(data):
        normalized = _normalize_hypothesis(item, index)
        if normalized:
            result.append(normalized)
    return result


def format_hypotheses_text(hypotheses: list[dict]) -> str:
    if not hypotheses:
        return "Гипотезы не сформулированы."

    lines = ["ГИПОТЕЗЫ О ДАННЫХ", "=" * 40, ""]
    for item in hypotheses:
        cols = ", ".join(item.get("columns") or []) or "—"
        lines.extend([
            f"{item.get('id', '?')}. {item.get('title', 'Гипотеза')}",
            f"Формулировка: {item.get('statement', '—')}",
            f"Основание: {item.get('rationale', '—')}",
            f"Столбцы: {cols}",
            f"Как проверить: {item.get('verification', '—')}",
            f"Приоритет: {item.get('priority_label', item.get('priority', 'medium'))}",
            "",
        ])
    return "\n".join(lines).strip()
