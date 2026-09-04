"""Поиск связей между несколькими таблицами без автоматического объединения."""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from .data_analysis import classify_column
from .utils import convert_numpy_types, safe_round as _round

logger = logging.getLogger(__name__)

MAX_UNIQUE_SAMPLE = 8000
MIN_INTERSECT = 3
JOIN_SCORE_MIN = 0.48
UNION_COL_JACCARD = 0.8
MEASUREMENT_HINTS = (
    "площад", "area", "sqm", "price", "цен", "плат", "rent", "cost", "amount",
    "сумм", "доход", "выруч", "вес", "weight", "объем", "volume", "score",
    "rating", "оценк", "возраст", "age", "salary", "зарплат", "тариф", "ставк",
)
ID_HINTS = ("id", "код", "номер", "key", "uuid", "guid", "инн", "унп", "idx")
GENERIC_SKIP = {"да", "нет", "yes", "no", "true", "false", "0", "1", "-", "нет данных", "nan", "none"}

CARDINALITY_LABELS = {
    "1:1": "один к одному",
    "1:N": "один ко многим",
    "N:1": "многие к одному",
    "N:M": "многие ко многим",
}


def _normalize_name(name: str) -> str:
    return re.sub(r"[\s_\-\.]+", "", str(name).lower())


def _strip_id_suffix(name: str) -> str:
    for suf in ("identifier", "uuid", "guid", "id", "код", "key", "номер", "no"):
        if name.endswith(suf) and len(name) > len(suf):
            return name[: -len(suf)]
    for pref in ("id", "код"):
        if name.startswith(pref) and len(name) > len(pref):
            return name[len(pref):]
    return name


def _looks_like_id_name(name: str) -> bool:
    lower = str(name).lower()
    return any(token in lower for token in ID_HINTS)


def _looks_like_measurement(name: str) -> bool:
    lower = str(name).lower()
    return any(hint in lower for hint in MEASUREMENT_HINTS)


def _name_score(col_a: str, col_b: str, table_a: str, table_b: str) -> float:
    na, nb = _normalize_name(col_a), _normalize_name(col_b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    sa, sb = _strip_id_suffix(na), _strip_id_suffix(nb)
    if sa and sa == sb:
        return 0.94

    ta = _strip_id_suffix(_normalize_name(table_a))
    tb = _strip_id_suffix(_normalize_name(table_b))

    if sa and tb and (sa == tb or sa in tb or tb in sa):
        return 0.86
    if sb and ta and (sb == ta or sb in ta or ta in sb):
        return 0.86
    if na in (tb, tb + "id", "id" + tb) or nb in (ta, ta + "id", "id" + ta):
        return 0.84

    if sa and sb and (sa in sb or sb in sa) and min(len(sa), len(sb)) >= 3:
        return 0.62
    return 0.0


def _canon_value(value) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (bool, np.bool_)):
        return str(value).lower()
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if float(value).is_integer():
            return str(int(value))
        return str(value)
    text = str(value).strip()
    if not text or text.lower() in GENERIC_SKIP:
        return None
    if re.fullmatch(r"-?\d+\.0+", text):
        text = text.split(".", 1)[0]
    return text


def _unique_values(series: pd.Series) -> tuple[set[str], int]:
    sample = series.dropna()
    if sample.empty:
        return set(), 0
    nunique = int(sample.nunique())
    if len(sample) > MAX_UNIQUE_SAMPLE:
        sample = sample.iloc[:MAX_UNIQUE_SAMPLE]
    values: set[str] = set()
    for item in sample.tolist():
        canon = _canon_value(item)
        if canon is not None:
            values.add(canon)
            if len(values) >= MAX_UNIQUE_SAMPLE:
                break
    return values, nunique


def _is_join_candidate(name: str, kind: str, nunique: int, rows: int) -> bool:
    if nunique <= 1:
        return False
    if kind in ("boolean",):
        return False
    if kind == "datetime" and not _looks_like_id_name(name):
        return False
    if kind == "numeric" and _looks_like_measurement(name) and not _looks_like_id_name(name):
        return False
    if kind == "textual" and rows and nunique > 0.95 * rows and not _looks_like_id_name(name):
        return False
    return True


def _cardinality(left_unique_ratio: float, right_unique_ratio: float) -> str:
    left_pk = left_unique_ratio >= 0.92
    right_pk = right_unique_ratio >= 0.92
    if left_pk and right_pk:
        return "1:1"
    if left_pk and not right_pk:
        return "1:N"
    if right_pk and not left_pk:
        return "N:1"
    return "N:M"


def _column_kinds(df: pd.DataFrame) -> dict[str, str]:
    return {col: classify_column(df, col) for col in df.columns}


def detect_unions(tables: list[dict]) -> list[dict]:
    links = []
    for i, left in enumerate(tables):
        left_cols = {str(c).lower() for c in left["columns"]}
        for right in tables[i + 1:]:
            right_cols = {str(c).lower() for c in right["columns"]}
            if not left_cols or not right_cols:
                continue
            inter = left_cols & right_cols
            union = left_cols | right_cols
            jaccard = len(inter) / len(union)
            if jaccard < UNION_COL_JACCARD or len(inter) < 2:
                continue
            links.append({
                "kind": "union",
                "left_table": left["id"],
                "right_table": right["id"],
                "left_column": None,
                "right_column": None,
                "score": _round(jaccard),
                "jaccard": _round(jaccard),
                "coverage_left": 100.0,
                "coverage_right": 100.0,
                "matched_values": len(inter),
                "cardinality": "union",
                "cardinality_label": "одинаковая схема",
                "shared_columns": sorted(inter)[:40],
                "examples": sorted(inter)[:8],
                "name_score": 1.0,
                "reason": (
                    f"Схемы совпадают на {round(jaccard * 100)}%: "
                    f"{len(inter)} общих столбцов из {len(union)}."
                ),
            })
    return links


def detect_join_links(tables: list[dict]) -> list[dict]:
    cache: dict[tuple[str, str], tuple[set[str], int, str, int]] = {}
    kinds_by_table = {t["id"]: _column_kinds(t["df"]) for t in tables}

    def cached(table_id: str, col: str, df: pd.DataFrame):
        key = (table_id, col)
        if key not in cache:
            values, nunique = _unique_values(df[col])
            kind = kinds_by_table[table_id].get(col, "textual")
            non_null = int(df[col].notna().sum())
            cache[key] = (values, nunique, kind, non_null)
        return cache[key]

    links: list[dict] = []
    for i, left in enumerate(tables):
        left_df = left["df"]
        for right in tables[i + 1:]:
            right_df = right["df"]
            pair_best: list[dict] = []
            for col_a in left_df.columns:
                vals_a, nuniq_a, kind_a, nn_a = cached(left["id"], col_a, left_df)
                if not _is_join_candidate(col_a, kind_a, nuniq_a, left["rows"]):
                    continue
                if not vals_a:
                    continue
                for col_b in right_df.columns:
                    name_s = _name_score(col_a, col_b, left["id"], right["id"])
                    vals_b, nuniq_b, kind_b, nn_b = cached(right["id"], col_b, right_df)
                    if not _is_join_candidate(col_b, kind_b, nuniq_b, right["rows"]):
                        continue
                    if not vals_b:
                        continue
                    if kind_a == "datetime" and kind_b == "datetime" and name_s < 0.9:
                        continue

                    inter = vals_a & vals_b
                    if len(inter) < MIN_INTERSECT:
                        continue
                    union = vals_a | vals_b
                    jaccard = len(inter) / max(len(union), 1)
                    cov_a = len(inter) / max(len(vals_a), 1)
                    cov_b = len(inter) / max(len(vals_b), 1)
                    overlap = 0.5 * jaccard + 0.5 * max(cov_a, cov_b)

                    if name_s < 0.4 and overlap < 0.55:
                        continue
                    if name_s < 0.15 and overlap < 0.7:
                        continue
                    if overlap < 0.18 and name_s < 0.85:
                        continue

                    score = 0.42 * name_s + 0.58 * overlap
                    if _looks_like_id_name(col_a) or _looks_like_id_name(col_b):
                        score = min(1.0, score + 0.08)
                    if score < JOIN_SCORE_MIN:
                        continue

                    uniq_a = nuniq_a / max(nn_a, 1)
                    uniq_b = nuniq_b / max(nn_b, 1)
                    card = _cardinality(uniq_a, uniq_b)
                    pair_best.append({
                        "kind": "join",
                        "left_table": left["id"],
                        "right_table": right["id"],
                        "left_column": str(col_a),
                        "right_column": str(col_b),
                        "score": _round(min(score, 1.0)),
                        "jaccard": _round(jaccard),
                        "coverage_left": _round(cov_a * 100, 2),
                        "coverage_right": _round(cov_b * 100, 2),
                        "matched_values": int(len(inter)),
                        "left_unique": int(nuniq_a),
                        "right_unique": int(nuniq_b),
                        "cardinality": card,
                        "cardinality_label": CARDINALITY_LABELS[card],
                        "examples": sorted(inter)[:8],
                        "name_score": _round(name_s),
                        "reason": (
                            f"Ключ «{col_a}» ↔ «{col_b}»: пересечение {len(inter)} значений, "
                            f"покрытие {round(max(cov_a, cov_b) * 100)}%, связь {CARDINALITY_LABELS[card]}."
                        ),
                    })

            pair_best.sort(key=lambda x: x["score"], reverse=True)
            links.extend(pair_best[:2])

    links.sort(key=lambda x: x["score"], reverse=True)
    return links[:40]


def detect_relations(tables: list[dict]) -> dict:
    if len(tables) < 2:
        return {
            "table_count": len(tables),
            "links": [],
            "join_links": [],
            "union_links": [],
            "summary": "Загружена одна таблица — межтабличные связи не ищутся.",
        }

    join_links = detect_join_links(tables)
    union_links = detect_unions(tables)
    links = join_links + union_links
    links.sort(key=lambda x: x["score"], reverse=True)

    if join_links:
        summary = (
            f"Найдено возможных ключей: {len(join_links)} "
            f"(лучший: {join_links[0]['left_table']}.{join_links[0]['left_column']} ↔ "
            f"{join_links[0]['right_table']}.{join_links[0]['right_column']}, "
            f"уверенность {round((join_links[0]['score'] or 0) * 100)}%). "
            "Таблицы не объединялись — связь может отсутствовать."
        )
    elif union_links:
        summary = (
            f"Ключей для join нет, но {len(union_links)} пар таблиц имеют почти одинаковую схему. "
            "Таблицы не склеивались автоматически."
        )
    else:
        summary = (
            "Общих ключей и совместимых схем не найдено. "
            "Таблицы анализируются отдельно."
        )

    return convert_numpy_types({
        "table_count": len(tables),
        "links": links,
        "join_links": join_links,
        "union_links": union_links,
        "summary": summary,
    })


def format_relations_report(relations: dict) -> str:
    lines = ["СВЯЗИ МЕЖДУ ТАБЛИЦАМИ", "=" * 36]
    if relations.get("summary"):
        lines.append(relations["summary"])
        lines.append("")

    links = relations.get("links") or []
    if not links:
        lines.append("Связи не найдены.")
    for i, link in enumerate(links, 1):
        if link.get("kind") == "union":
            lines.append(
                f"{i}. Схема: {link['left_table']} ≈ {link['right_table']} "
                f"(Jaccard {link.get('jaccard')}, общих столбцов {len(link.get('shared_columns') or [])})"
            )
        else:
            lines.append(
                f"{i}. {link['left_table']}.{link['left_column']} ↔ "
                f"{link['right_table']}.{link['right_column']} "
                f"[{link.get('cardinality')}] score={link.get('score')} "
                f"покрытие {link.get('coverage_left')}% / {link.get('coverage_right')}% "
                f"пересечение {link.get('matched_values')}"
            )
            if link.get("examples"):
                lines.append("   примеры: " + ", ".join(str(x) for x in link["examples"][:6]))
        if link.get("reason"):
            lines.append(f"   {link['reason']}")
        lines.append("")

    lines.append("Таблицы не объединялись автоматически.")
    return "\n".join(lines).strip()


def relations_hypotheses(relations: dict) -> list[dict]:
    hyps = []
    for link in (relations.get("join_links") or [])[:6]:
        cov = max(link.get("coverage_left") or 0, link.get("coverage_right") or 0)
        unmatched_hint = 100 - min(link.get("coverage_left") or 0, link.get("coverage_right") or 0)
        hyps.append({
            "id": len(hyps) + 1,
            "kind": "table_relation",
            "kind_label": "Связь таблиц",
            "title": (
                f"Ключ {link['left_table']}.{link['left_column']} ↔ "
                f"{link['right_table']}.{link['right_column']}"
            ),
            "statement": (
                f"Если таблицы «{link['left_table']}» и «{link['right_table']}» описывают одну предметную область, "
                f"то их можно связать по «{link['left_column']}» / «{link['right_column']}» "
                f"({link.get('cardinality_label')}, пересечение {link.get('matched_values')} значений, "
                f"покрытие до {cov}%)."
            ),
            "rationale": link.get("reason") or "",
            "columns": [link["left_column"], link["right_column"]],
            "verification": (
                f"Проверить join left/inner; доля несопоставленных ключей ≈ {round(unmatched_hint, 1)}%. "
                "Сравнить агрегаты до и после объединения."
            ),
            "priority": "high" if (link.get("score") or 0) >= 0.7 else "medium",
            "priority_label": "высокий" if (link.get("score") or 0) >= 0.7 else "средний",
            "source": "python",
        })

    for link in (relations.get("union_links") or [])[:2]:
        hyps.append({
            "id": len(hyps) + 1,
            "kind": "table_relation",
            "kind_label": "Связь таблиц",
            "title": f"Одинаковая схема: {link['left_table']} и {link['right_table']}",
            "statement": (
                f"Если «{link['left_table']}» и «{link['right_table']}» — части одной выборки, "
                f"их можно склеить по строкам (совпадение схемы {round((link.get('jaccard') or 0) * 100)}%)."
            ),
            "rationale": link.get("reason") or "",
            "columns": (link.get("shared_columns") or [])[:8],
            "verification": "Проверить concat, дубликаты и столбец-источник _source_table.",
            "priority": "medium",
            "priority_label": "средний",
            "source": "python",
        })

    return hyps[:8]
