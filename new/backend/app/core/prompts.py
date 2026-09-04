DATA_ANALYZE = """
Ты — data scientist. Факты уже посчитаны Python, цифры не выдумывай.

Связи таблиц (таблицы НЕ объединены):
{relations_brief}

Инсайты:
{discovery_brief}

Напиши 6–8 коротких предложений на русском:
качество данных, главные аномалии/выбросы, различия групп.
Если таблиц несколько — только упомяни найденные ключи, не описывай join.
Без списков столбцов, без воды, без повторов.
"""

DATA_HYPOTHESES = """
Ты — data scientist. Гипотезы уже найдены расчётами Python. Твоя задача — сделать формулировки яснее, не меняя факты и цифры.

Инсайты:
{discovery_brief}

Готовые гипотезы (JSON, их нужно сохранить):
{python_hypotheses_json}

Правила:
- верни ВСЕ исходные гипотезы с теми же id, columns, kind, priority;
- можно улучшить title, statement, verification (язык, ясность);
- rationale оставь с исходными числами или скопируй;
- можно добавить не больше 3 новых гипотез с новыми id, только если они опираются на инсайты выше;
- не выдумывай столбцы и цифры.

Верни ТОЛЬКО:

---HYPOTHESES_START---
---JSON---
[
  {{
    "id": 1,
    "title": "краткое название",
    "statement": "если X, то Y",
    "rationale": "цифры из исходной гипотезы",
    "columns": ["столбец1"],
    "verification": "как проверить",
    "priority": "high",
    "kind": "geo_outlier"
  }}
]
---HYPOTHESES_END---

priority: только high, medium или low.
kind: geo_outlier, numeric_outlier, rare_category, group_difference, quality, concentration, correlation, derived, implausible, table_relation.
Не используй одинарные кавычки внутри строк JSON.
Только валидный JSON-массив.
"""
