"""Python-first поиск инсайтов: выбросы, ядро рынка, редкие категории, гипотезы."""

from __future__ import annotations

import re
from collections import defaultdict

import numpy as np
import pandas as pd

from .data_analysis import classify_column
from .utils import convert_numpy_types

CORE_COVERAGE = 0.80
CORE_MIN_SHARE = 0.05
RARE_SHARE = 0.02
RARE_COUNT_CAP = 8
MAX_EXAMPLES = 8
MAX_HYPOTHESES = 14

GEO_HINTS = (
    "город", "city", "town", "населен", "регион", "region", "област",
    "district", "country", "страна", "адрес", "address", "localit",
    "location", "поселок", "посёлок", "деревн", "район", "округ", "state",
    "province", "municip", "zip", "индекс",
)
MONEY_HINTS = (
    "цена", "плат", "price", "rent", "cost", "amount", "сумм", "доход",
    "выруч", "revenue", "profit", "тариф", "ставк", "fee", "оплат", "зарплат",
    "salary",
)
CURRENCY_HINTS = ("валют", "currency", "ccy", "curr")
AREA_HINTS = (
    "площад", "area", "sqm", "кв.м", "кв м", "м.кв", "м кв", "метраж",
    "кв. м", "м2", "m2",
)

KIND_LABELS = {
    "geo_outlier": "Вне основной области",
    "numeric_outlier": "Выбросы",
    "rare_category": "Редкие категории",
    "group_difference": "Различия групп",
    "quality": "Качество данных",
    "concentration": "Концентрация",
    "correlation": "Связь признаков",
    "derived": "Производная метрика",
    "implausible": "Подозрительные значения",
}

SCRIPT_LABELS = {
    "cyrillic": "кириллицей",
    "latin": "латиницей",
    "mixed": "смешанной письменностью",
    "other": "одной письменностью",
}


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
        if np.isnan(f) or np.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _round(value, digits: int = 4):
    f = _safe_float(value)
    if f is None:
        return None
    return round(f, digits)


def _pct(part: int, total: int, digits: int = 2) -> float:
    if not total:
        return 0.0
    return round(100.0 * part / total, digits)


def _name_matches(name: str, hints: tuple[str, ...]) -> bool:
    lower = name.lower()
    return any(hint in lower for hint in hints)


def _column_kind(df: pd.DataFrame, col: str, parsed_structure: dict | None) -> str:
    if parsed_structure:
        for item in parsed_structure.get("columns", []):
            if item.get("name") == col:
                return item.get("kind") or classify_column(df, col)
    return classify_column(df, col)


def infer_column_roles(df: pd.DataFrame, parsed_structure: dict | None = None) -> dict:
    roles: dict[str, list[str]] = {
        "geo": [],
        "money": [],
        "currency": [],
        "area": [],
        "numeric": [],
        "categorical": [],
        "datetime": [],
        "identifier": [],
    }
    for col in df.columns:
        kind = _column_kind(df, col, parsed_structure)
        if kind == "numeric":
            roles["numeric"].append(col)
        elif kind in ("categorical", "boolean"):
            roles["categorical"].append(col)
        elif kind == "datetime":
            roles["datetime"].append(col)
        elif kind == "identifier":
            roles["identifier"].append(col)

        if kind in ("categorical", "textual") and _name_matches(col, GEO_HINTS):
            roles["geo"].append(col)
        if kind == "numeric" and _name_matches(col, MONEY_HINTS):
            roles["money"].append(col)
        if kind in ("categorical", "textual") and _name_matches(col, CURRENCY_HINTS):
            roles["currency"].append(col)
        if kind == "numeric" and _name_matches(col, AREA_HINTS):
            roles["area"].append(col)

    if not roles["geo"]:
        for col in roles["categorical"]:
            nunique = int(df[col].nunique(dropna=True))
            if 4 <= nunique <= 80 and _name_matches(col, GEO_HINTS):
                roles["geo"].append(col)
    return roles


def _script_kind(value: str) -> str:
    letters = re.findall(r"[^\W\d_]+", value, flags=re.UNICODE)
    if not letters:
        return "other"
    sample = "".join(letters)
    cyr = len(re.findall(r"[А-Яа-яЁё]", sample))
    lat = len(re.findall(r"[A-Za-z]", sample))
    if cyr and not lat:
        return "cyrillic"
    if lat and not cyr:
        return "latin"
    if cyr and lat:
        return "mixed"
    return "other"


def _iqr_bounds(series: pd.Series, fence: float = 1.5) -> tuple[float, float, float, float, float] | None:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if len(s) < 8:
        return None
    q1 = float(s.quantile(0.25))
    q3 = float(s.quantile(0.75))
    iqr = q3 - q1
    if iqr <= 0:
        return None
    return q1, q3, iqr, q1 - fence * iqr, q3 + fence * iqr


def _modified_z_mask(series: pd.Series, threshold: float = 3.5) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    median = s.median()
    mad = (s - median).abs().median()
    if not mad or pd.isna(mad) or mad == 0:
        return pd.Series(False, index=s.index)
    z = 0.6745 * (s - median) / mad
    return z.abs() > threshold


def _numeric_series(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")


def _value_counts_table(series: pd.Series, total: int, limit: int = 30) -> list[dict]:
    vc = series.dropna().astype(str).value_counts()
    rows = []
    for value, count in vc.head(limit).items():
        rows.append({
            "value": str(value),
            "count": int(count),
            "share_pct": _pct(int(count), total),
        })
    return rows


def compute_derived_metrics(df: pd.DataFrame, roles: dict) -> tuple[pd.DataFrame, list[dict]]:
    work = df.copy()
    derived: list[dict] = []
    money_cols = roles.get("money") or []
    area_cols = roles.get("area") or []

    for money in money_cols:
        for area in area_cols:
            if money == area:
                continue
            name = f"{money} / {area}"
            num = _numeric_series(work, money)
            den = _numeric_series(work, area)
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio = num / den.replace(0, np.nan)
            work[name] = ratio
            s = ratio.dropna()
            if s.empty:
                continue
            derived.append({
                "name": name,
                "kind": "unit_price",
                "numerator": money,
                "denominator": area,
                "count": int(s.count()),
                "mean": _round(s.mean(), 2),
                "median": _round(s.median(), 2),
                "min": _round(s.min(), 2),
                "max": _round(s.max(), 2),
                "p90": _round(s.quantile(0.90), 2),
            })
    return work, derived


def compute_numeric_outliers(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    rows, findings = len(df), []
    for col in columns:
        if col not in df.columns:
            continue
        s = _numeric_series(df, col)
        valid = s.dropna()
        if len(valid) < 8 or valid.nunique() < 4:
            continue

        bounds = _iqr_bounds(s, fence=1.5)
        iqr_mask = pd.Series(False, index=df.index)
        lo = hi = None
        if bounds:
            _, _, _, lo, hi = bounds
            iqr_mask = (s < lo) | (s > hi)
            if int(iqr_mask.fillna(False).sum()) / max(rows, 1) > 0.12:
                bounds3 = _iqr_bounds(s, fence=3.0)
                if bounds3:
                    _, _, _, lo, hi = bounds3
                    iqr_mask = (s < lo) | (s > hi)
        nunique = int(valid.nunique())
        z_mask = pd.Series(False, index=df.index)
        if nunique >= 40:
            z_mask = _modified_z_mask(s)
        mask = iqr_mask.fillna(False) | z_mask.fillna(False)
        n_out = int(mask.sum())
        if n_out == 0:
            continue

        outlier_vals = s[mask].dropna()
        examples = (
            outlier_vals.value_counts()
            .head(MAX_EXAMPLES)
            .rename_axis("value")
            .reset_index(name="count")
        )
        findings.append({
            "column": col,
            "n_outliers": n_out,
            "pct": _pct(n_out, rows),
            "method": "IQR 1.5 и modified z-score",
            "lower": _round(lo, 2),
            "upper": _round(hi, 2),
            "min": _round(valid.min(), 2),
            "max": _round(valid.max(), 2),
            "median": _round(valid.median(), 2),
            "mean": _round(valid.mean(), 2),
            "examples": [
                {"value": _round(row["value"], 2), "count": int(row["count"])}
                for _, row in examples.iterrows()
            ],
        })
    return findings


def compute_implausible(df: pd.DataFrame, roles: dict) -> list[dict]:
    findings = []
    rows = len(df)
    for col in (roles.get("money") or []) + (roles.get("area") or []) + (roles.get("numeric") or []):
        if col not in df.columns:
            continue
        s = _numeric_series(df, col)
        negative = int((s < 0).sum())
        zero = int((s == 0).sum())
        if negative:
            findings.append({
                "column": col,
                "issue": "negative",
                "count": negative,
                "pct": _pct(negative, rows),
                "detail": f"Отрицательные значения в «{col}»: {negative} ({_pct(negative, rows)}%).",
            })
        if zero and col in (roles.get("money") or []) + (roles.get("area") or []):
            findings.append({
                "column": col,
                "issue": "zero",
                "count": zero,
                "pct": _pct(zero, rows),
                "detail": f"Нули в «{col}»: {zero} ({_pct(zero, rows)}%) — возможны ошибки ввода.",
            })

    for col in roles.get("area") or []:
        s = _numeric_series(df, col).dropna()
        if s.empty:
            continue
        ones = int((s == 1).sum())
        if ones >= max(10, 0.08 * len(s)):
            findings.append({
                "column": col,
                "issue": "tiny_area",
                "count": ones,
                "pct": _pct(ones, rows),
                "detail": (
                    f"В «{col}» значение 1 встречается {ones} раз ({_pct(ones, rows)}%). "
                    "Для площадей это часто ошибка единиц измерения или тестовые данные."
                ),
            })

    for col in roles.get("numeric") or []:
        s = _numeric_series(df, col).dropna()
        nunique = int(s.nunique())
        if nunique < 3 or nunique > 12:
            continue
        vc = s.value_counts()
        rare_cut = max(2, int(0.01 * len(s)))
        rare = vc[vc <= rare_cut]
        if rare.empty:
            continue
        parts = ", ".join(f"{_round(val, 2)}×{int(cnt)}" for val, cnt in rare.head(6).items())
        findings.append({
            "column": col,
            "issue": "rare_level",
            "count": int(rare.sum()),
            "pct": _pct(int(rare.sum()), rows),
            "detail": (
                f"В «{col}» {nunique} дискретных уровней; редкие: {parts}."
            ),
        })
    return findings


def compute_label_duplicates(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    findings = []
    for col in columns:
        if col not in df.columns:
            continue
        s = df[col].dropna().astype(str).str.strip()
        groups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for val in s:
            groups[val.casefold()][val] += 1
        for key, variants in groups.items():
            if len(variants) < 2:
                continue
            findings.append({
                "column": col,
                "canonical": key,
                "variants": [
                    {"value": name, "count": int(cnt)}
                    for name, cnt in sorted(variants.items(), key=lambda x: -x[1])
                ],
                "total": int(sum(variants.values())),
            })
    return findings


def compute_concentration(df: pd.DataFrame, columns: list[str], roles: dict) -> list[dict]:
    rows = len(df)
    findings = []
    geo_set = set(roles.get("geo") or [])
    for col in columns:
        if col not in df.columns:
            continue
        s = df[col].dropna().astype(str).str.strip()
        nunique = int(s.nunique())
        if nunique < 3 or nunique > 400:
            continue
        vc = s.value_counts()
        scripts = s.map(_script_kind)
        majority_script = scripts.mode().iloc[0] if not scripts.empty else "other"
        core_values = [value for value, count in vc.items() if count / max(rows, 1) >= CORE_MIN_SHARE]
        if not core_values or sum(int(vc[v]) for v in core_values) / max(rows, 1) < 0.50:
            cumulative = 0
            core_values = []
            for value, count in vc.items():
                core_values.append(value)
                cumulative += int(count)
                if cumulative / max(rows, 1) >= CORE_COVERAGE:
                    break

        core_set = set(core_values)
        core_count = int(vc[vc.index.isin(core_set)].sum())
        rare_cut = max(3, int(rows * RARE_SHARE))
        rare_cut = min(rare_cut, RARE_COUNT_CAP)

        def _row(value: str, count: int, in_core: bool) -> dict:
            script = _script_kind(value)
            flags = []
            if not in_core:
                flags.append("periphery")
            if count <= rare_cut:
                flags.append("rare")
            if majority_script in ("cyrillic", "latin") and script not in (majority_script, "other", "mixed"):
                flags.append("foreign_script")
            return {
                "value": value,
                "count": int(count),
                "share_pct": _pct(int(count), rows),
                "script": script,
                "flags": flags,
            }

        core_rows = [_row(v, int(vc[v]), True) for v in core_values]
        periphery_rows = [
            _row(v, int(c), False)
            for v, c in vc.items()
            if v not in core_set
        ]
        findings.append({
            "column": col,
            "role": "geo" if col in geo_set else "categorical",
            "n_categories": nunique,
            "core_coverage_pct": _pct(core_count, rows),
            "core_size": len(core_rows),
            "core": core_rows,
            "periphery": periphery_rows,
            "rare": [r for r in periphery_rows if "rare" in r["flags"]],
            "foreign": [r for r in periphery_rows if "foreign_script" in r["flags"]],
            "majority_script": majority_script,
        })
    return findings


def compute_group_profiles(
    df: pd.DataFrame,
    cat_cols: list[str],
    num_cols: list[str],
    *,
    max_groups: int = 20,
) -> list[dict]:
    profiles = []
    for cat in cat_cols:
        if cat not in df.columns:
            continue
        nunique = df[cat].nunique(dropna=True)
        if nunique < 2 or nunique > 80:
            continue
        for num in num_cols:
            if num not in df.columns or cat == num:
                continue
            frame = pd.DataFrame({
                "cat": df[cat].astype(str).str.strip(),
                "val": _numeric_series(df, num),
            }).dropna()
            if len(frame) < 8 or frame["cat"].nunique() < 2:
                continue
            overall_median = float(frame["val"].median())
            overall_mean = float(frame["val"].mean())
            grouped = frame.groupby("cat")["val"].agg(["count", "median", "mean", "min", "max"])
            grouped = grouped[grouped["count"] >= 5]
            if grouped.empty or len(grouped) < 2:
                continue
            grouped = grouped.sort_values("count", ascending=False).head(max_groups)
            groups = []
            for name, row in grouped.iterrows():
                median = float(row["median"])
                ratio = median / overall_median if overall_median else None
                flags = []
                if row["count"] <= RARE_COUNT_CAP:
                    flags.append("small_sample")
                if ratio is not None and (ratio >= 2.0 or ratio <= 0.5):
                    flags.append("far_from_center")
                groups.append({
                    "value": str(name),
                    "count": int(row["count"]),
                    "median": _round(median, 2),
                    "mean": _round(float(row["mean"]), 2),
                    "min": _round(float(row["min"]), 2),
                    "max": _round(float(row["max"]), 2),
                    "median_vs_overall": _round(ratio, 2) if ratio is not None else None,
                    "flags": flags,
                })
            medians_src = grouped[grouped["count"] >= 10] if (grouped["count"] >= 10).sum() >= 2 else grouped
            medians = medians_src["median"]
            profiles.append({
                "categorical": cat,
                "numeric": num,
                "overall_median": _round(overall_median, 2),
                "overall_mean": _round(overall_mean, 2),
                "median_range": {
                    "high_group": str(medians.idxmax()),
                    "high": _round(float(medians.max()), 2),
                    "low_group": str(medians.idxmin()),
                    "low": _round(float(medians.min()), 2),
                    "ratio": _round(float(medians.max() / medians.min()), 2) if float(medians.min()) else None,
                },
                "groups": groups,
            })
    return profiles


def _spearman(a: pd.Series, b: pd.Series) -> float | None:
    frame = pd.DataFrame({"a": a, "b": b}).dropna()
    if len(frame) < 8:
        return None
    ra = frame["a"].rank()
    rb = frame["b"].rank()
    return _round(ra.corr(rb), 4)


def _kruskal_h(frame: pd.DataFrame, cat: str, num: str) -> float | None:
    data = frame[[cat, num]].dropna()
    if len(data) < 12:
        return None
    data["_rank"] = data[num].rank()
    groups = data.groupby(data[cat].astype(str), observed=True)
    if groups.ngroups < 2:
        return None
    n = len(data)
    h = 0.0
    for _, g in groups:
        ni = len(g)
        if ni < 1:
            continue
        r_bar = float(g["_rank"].mean())
        h += ni * r_bar ** 2
    h = 12.0 / (n * (n + 1)) * h - 3.0 * (n + 1)
    return _round(h, 3)


def compute_tests(
    df: pd.DataFrame,
    roles: dict,
    correlations: dict | None,
) -> list[dict]:
    tests = []
    money = (roles.get("money") or roles.get("numeric") or [])
    area = roles.get("area") or []
    geo = roles.get("geo") or roles.get("categorical") or []

    for a in area:
        for m in money:
            if a == m or a not in df.columns or m not in df.columns:
                continue
            rho = _spearman(_numeric_series(df, a), _numeric_series(df, m))
            if rho is None:
                continue
            tests.append({
                "type": "spearman",
                "columns": [a, m],
                "stat": rho,
                "detail": f"Spearman ρ={rho} между «{a}» и «{m}».",
            })

    eta_pairs = (correlations or {}).get("categorical_numeric") or []
    eta_index = {(p.get("categorical"), p.get("numeric")): p for p in eta_pairs}

    for cat in geo[:4]:
        for num in money[:3]:
            if cat not in df.columns or num not in df.columns:
                continue
            frame = pd.DataFrame({
                cat: df[cat],
                num: _numeric_series(df, num),
            })
            h = _kruskal_h(frame, cat, num)
            eta = (eta_index.get((cat, num)) or {}).get("eta")
            if h is None and eta is None:
                continue
            tests.append({
                "type": "group_difference",
                "columns": [cat, num],
                "kruskal_h": h,
                "eta": eta,
                "detail": (
                    f"Различия «{num}» по «{cat}»: "
                    + (f"Kruskal-Wallis H={h}" if h is not None else "")
                    + (f", η={eta}" if eta is not None else "")
                    + "."
                ).replace(" :", ":"),
            })
    return tests


def _highlights_from_parts(
    concentration: list[dict],
    outliers: list[dict],
    implausible: list[dict],
    duplicates: list[dict],
    tests: list[dict],
    derived: list[dict],
) -> list[dict]:
    highlights = []
    for item in concentration:
        peri = item.get("periphery") or []
        if item.get("role") == "geo" and peri:
            names = ", ".join(r["value"] for r in peri[:8])
            highlights.append({
                "kind": "geo_outlier",
                "severity": "high",
                "title": f"Значения «{item['column']}» вне основной области",
                "detail": (
                    f"Ядро ({item['core_size']} категорий) покрывает "
                    f"{item['core_coverage_pct']}% строк; вне ядра: {names}."
                ),
            })
        foreign = item.get("foreign") or []
        if foreign:
            names = ", ".join(r["value"] for r in foreign)
            highlights.append({
                "kind": "geo_outlier",
                "severity": "high",
                "title": f"Иноязычные значения в «{item['column']}»",
                "detail": f"На фоне основной письменности выделяются: {names}.",
            })
        rare = item.get("rare") or []
        if rare and item.get("role") != "geo":
            names = ", ".join(f"{r['value']} ({r['count']})" for r in rare[:6])
            highlights.append({
                "kind": "rare_category",
                "severity": "medium",
                "title": f"Редкие категории в «{item['column']}»",
                "detail": names,
            })

    for item in outliers:
        if item["n_outliers"] <= 0:
            continue
        highlights.append({
            "kind": "numeric_outlier",
            "severity": "high" if item["pct"] >= 1 else "medium",
            "title": f"Выбросы в «{item['column']}»",
            "detail": (
                f"{item['n_outliers']} значений ({item['pct']}%), "
                f"диапазон {item['min']}…{item['max']}, медиана {item['median']}."
            ),
        })

    for item in implausible:
        highlights.append({
            "kind": "implausible",
            "severity": "high",
            "title": f"Подозрительные значения: {item['column']}",
            "detail": item["detail"],
        })

    for item in duplicates:
        variants = ", ".join(f"«{v['value']}»×{v['count']}" for v in item["variants"])
        highlights.append({
            "kind": "quality",
            "severity": "medium",
            "title": f"Дубликаты написания в «{item['column']}»",
            "detail": variants,
        })

    for item in tests:
        if item.get("type") == "group_difference" and (item.get("eta") or 0) >= 0.3:
            highlights.append({
                "kind": "group_difference",
                "severity": "high",
                "title": "Группы статистически различаются",
                "detail": item["detail"],
            })
        if item.get("type") == "spearman" and abs(item.get("stat") or 0) >= 0.3:
            highlights.append({
                "kind": "correlation",
                "severity": "medium",
                "title": "Монотонная связь числовых признаков",
                "detail": item["detail"],
            })

    for item in derived:
        highlights.append({
            "kind": "derived",
            "severity": "medium",
            "title": f"Производная метрика {item['name']}",
            "detail": (
                f"Медиана {item['median']}, среднее {item['mean']}, "
                f"диапазон {item['min']}…{item['max']}."
            ),
        })
    return highlights[:16]


def hypotheses_from_discovery(discovery: dict) -> list[dict]:
    hyps: list[dict] = []
    roles = discovery.get("roles") or {}
    geo_cols = roles.get("geo") or []

    def add(kind: str, title: str, statement: str, rationale: str,
            columns: list[str], verification: str, priority: str = "high"):
        if len(hyps) >= MAX_HYPOTHESES:
            return
        hyps.append({
            "id": len(hyps) + 1,
            "kind": kind,
            "kind_label": KIND_LABELS.get(kind, kind),
            "title": title,
            "statement": statement,
            "rationale": rationale,
            "columns": columns,
            "verification": verification,
            "priority": priority,
            "priority_label": {"high": "высокий", "medium": "средний", "low": "низкий"}[priority],
            "source": "python",
        })

    for item in discovery.get("concentration") or []:
        peri = item.get("periphery") or []
        if not peri:
            continue
        col = item["column"]
        is_geo = item.get("role") == "geo" or col in geo_cols
        core_names = ", ".join(r["value"] for r in item.get("core") or [])
        peri_names = ", ".join(r["value"] for r in peri[:10])
        kind = "geo_outlier" if is_geo else "concentration"
        title = (
            f"«{col}»: значения вне основной области"
            if is_geo else f"Концентрация категорий в «{col}»"
        )
        add(
            kind,
            title,
            (
                f"Если основная область задаётся ядром «{col}» "
                f"({item['core_size']} значений, {item['core_coverage_pct']}% строк: {core_names}), "
                f"то {len(peri)} значений не принадлежат ей: {peri_names}."
            ),
            (
                f"Правило покрытия {int(CORE_COVERAGE * 100)}% строк. "
                f"Периферия: {peri_names}."
            ),
            [col],
            "Сравнить частоты ядра и хвоста; проверить, не являются ли редкие значения ошибками ввода или другим рынком.",
            "high" if is_geo else "medium",
        )
        foreign = item.get("foreign") or []
        if foreign and is_geo:
            names = ", ".join(r["value"] for r in foreign)
            add(
                "geo_outlier",
                f"Иноязычные локации в «{col}»",
                (
                    f"Если основной рынок записан {SCRIPT_LABELS.get(item.get('majority_script'), 'одной письменностью')}, "
                    f"то {names} — инородные точки, которые не должны смешиваться с основным регионом."
                ),
                f"Скрипт большинства: {item.get('majority_script')}; иноязычные: {names}.",
                [col],
                "Отфильтровать записи с иноязычными значениями и сравнить их метрики с ядром.",
                "high",
            )

    for item in discovery.get("label_duplicates") or []:
        variants = ", ".join(f"«{v['value']}» ({v['count']})" for v in item["variants"])
        add(
            "quality",
            f"Один объект, разный регистр: {item['column']}",
            (
                f"Если {variants} обозначают одну категорию, то текущая кардинальность "
                f"«{item['column']}» завышена, а частоты занижены."
            ),
            f"Совпадение без учёта регистра, суммарно {item['total']} строк.",
            [item["column"]],
            "Нормализовать регистр и пробелы, затем пересчитать частоты и групповые медианы.",
            "medium",
        )

    for item in discovery.get("outliers") or []:
        examples = ", ".join(
            f"{ex['value']}×{ex['count']}" for ex in (item.get("examples") or [])[:5]
        )
        add(
            "numeric_outlier",
            f"Выбросы «{item['column']}» искажают среднее",
            (
                f"Если отсечь {item['n_outliers']} выбросов ({item['pct']}%) в «{item['column']}», "
                f"среднее станет ближе к медиане {item['median']} "
                f"(сейчас среднее {item['mean']}, max {item['max']})."
            ),
            (
                f"{item['method']}: границы {item['lower']}…{item['upper']}. "
                f"Примеры: {examples or '—'}. min={item['min']}."
            ),
            [item["column"]],
            "Boxplot и сравнение mean/median до и после удаления IQR-выбросов; отдельно проверить минимум.",
            "high",
        )

    for item in discovery.get("implausible") or []:
        add(
            "implausible",
            f"Подозрительная шкала «{item['column']}»",
            item["detail"].rstrip(".") + " — такие значения, скорее всего, не сопоставимы с остальной выборкой.",
            item["detail"],
            [item["column"]],
            "Проверить единицы измерения, фильтр по значению и влияние на производные метрики.",
            "high",
        )

    for item in discovery.get("concentration") or []:
        if item.get("role") == "geo":
            continue
        rare = item.get("rare") or []
        if not rare:
            continue
        names = ", ".join(f"«{r['value']}» ({r['count']})" for r in rare[:6])
        add(
            "rare_category",
            f"Редкие значения «{item['column']}»",
            (
                f"Если рабочие категории — ядро «{item['column']}» "
                f"({item['core_coverage_pct']}% строк), то {names} — шум или отдельный сегмент."
            ),
            f"Редкие (≤{RARE_COUNT_CAP} или <{int(RARE_SHARE * 100)}%): {names}.",
            [item["column"]],
            "Сгруппировать хвост в «прочее» и сравнить метрики ядра с хвостом.",
            "medium",
        )

    group_added = 0
    for profile in discovery.get("group_profiles") or []:
        if group_added >= 2:
            break
        rng = profile.get("median_range") or {}
        ratio = rng.get("ratio") or 0
        if ratio and ratio >= 1.8:
            cat, num = profile["categorical"], profile["numeric"]
            add(
                "group_difference",
                f"«{cat}» определяет уровень «{num}»",
                (
                    f"Если сегментировать по «{cat}», медианы «{num}» различаются в {ratio} раза: "
                    f"«{rng.get('high_group')}» {rng.get('high')} vs «{rng.get('low_group')}» {rng.get('low')} "
                    f"(общая медиана {profile.get('overall_median')})."
                ),
                f"Групповые медианы; overall mean={profile.get('overall_mean')}.",
                [cat, num],
                f"Kruskal-Wallis / сравнение медиан; boxplot «{num}» по «{cat}».",
                "high",
            )
            group_added += 1

    for test in discovery.get("tests") or []:
        if test.get("type") != "spearman":
            continue
        rho = abs(test.get("stat") or 0)
        cols = test.get("columns") or []
        if rho < 0.25 or len(cols) < 2:
            continue
        direction = "растёт" if (test.get("stat") or 0) > 0 else "падает"
        add(
            "correlation",
            f"Связь {cols[0]} и {cols[1]}",
            (
                f"Если «{cols[0]}» увеличивается, «{cols[1]}» {direction} "
                f"(Spearman ρ={test.get('stat')})."
            ),
            test.get("detail", ""),
            cols,
            "Scatter + Spearman; проверить устойчивость без выбросов.",
            "medium",
        )

    for item in discovery.get("derived") or []:
        add(
            "derived",
            f"Нормированная метрика {item['name']}",
            (
                f"Если сравнивать объекты по {item['name']}, а не по числителю, "
                f"разброс остаётся высоким: медиана {item['median']}, max {item['max']} "
                f"(в {round(item['max'] / item['median'], 1) if item.get('median') else '—'} раз больше медианы)."
            ),
            f"mean={item['mean']}, p90={item.get('p90')}, n={item['count']}.",
            [item.get("numerator"), item.get("denominator")],
            "Рассчитать метрику на всех строках, boxplot по гео/категории, отдельно выбросы знаменателя.",
            "high",
        )

    money = (roles.get("money") or [None])[0]
    currency = (roles.get("currency") or [None])[0]
    if money and currency and currency in (discovery.get("roles") or {}).get("categorical", []) + [currency]:
        conc = next((c for c in discovery.get("concentration") or [] if c["column"] == currency), None)
        if conc and conc.get("core_coverage_pct", 0) >= 80 and conc.get("periphery"):
            peri = ", ".join(f"{r['value']} ({r['count']})" for r in conc["periphery"][:6])
            core = ", ".join(r["value"] for r in conc.get("core") or [])
            add(
                "quality",
                f"Смешение валют ломает сравнение «{money}»",
                (
                    f"Если {core} — рабочая валюта ({conc['core_coverage_pct']}% строк), "
                    f"то суммы в {peri} нельзя сравнивать с основной шкалой без конвертации."
                ),
                f"Ядро валют покрывает {conc['core_coverage_pct']}% выборки.",
                [money, currency],
                "Разложить «{money}» по «{currency}» и повторить выбросы внутри основной валюты.".replace("{money}", money).replace("{currency}", currency),
                "high",
            )

    return hyps[:MAX_HYPOTHESES]


def format_discovery_brief(discovery: dict, limit: int = 7000) -> str:
    lines = ["НАЙДЕННЫЕ ИНСАЙТЫ (Python)", "=" * 36]
    roles = discovery.get("roles") or {}
    role_bits = []
    for key in ("geo", "money", "area", "currency"):
        if roles.get(key):
            role_bits.append(f"{key}: {', '.join(roles[key])}")
    if role_bits:
        lines.append("Роли столбцов: " + "; ".join(role_bits))
        lines.append("")

    if discovery.get("highlights"):
        lines.append("Ключевые находки:")
        for h in discovery["highlights"]:
            lines.append(f"  • [{h.get('kind')}] {h.get('title')}: {h.get('detail')}")
        lines.append("")

    for item in discovery.get("concentration") or []:
        if item.get("role") != "geo" and not item.get("periphery"):
            continue
        lines.append(
            f"Концентрация «{item['column']}»: ядро {item['core_size']} кат. "
            f"({item['core_coverage_pct']}%), всего {item['n_categories']}."
        )
        core = ", ".join(f"{r['value']} {r['share_pct']}%" for r in item.get("core") or [])
        peri = ", ".join(
            f"{r['value']} n={r['count']}" + (f"/{',' .join(r['flags'])}" if r.get("flags") else "")
            for r in item.get("periphery") or []
        )
        lines.append(f"  ядро: {core}")
        if peri:
            lines.append(f"  вне ядра: {peri}")
        lines.append("")

    for item in discovery.get("outliers") or []:
        examples = ", ".join(f"{e['value']}×{e['count']}" for e in item.get("examples") or [])
        lines.append(
            f"Выбросы «{item['column']}»: n={item['n_outliers']} ({item['pct']}%), "
            f"med={item['median']}, mean={item['mean']}, min={item['min']}, max={item['max']}. "
            f"Примеры: {examples}"
        )
    if discovery.get("outliers"):
        lines.append("")

    for item in discovery.get("implausible") or []:
        lines.append(f"Подозрительно: {item['detail']}")
    if discovery.get("implausible"):
        lines.append("")

    for item in discovery.get("label_duplicates") or []:
        variants = ", ".join(f"{v['value']}×{v['count']}" for v in item["variants"])
        lines.append(f"Дубликаты регистра «{item['column']}»: {variants}")
    if discovery.get("label_duplicates"):
        lines.append("")

    for profile in (discovery.get("group_profiles") or [])[:4]:
        rng = profile.get("median_range") or {}
        lines.append(
            f"Профиль {profile['categorical']} → {profile['numeric']}: "
            f"медиана {profile.get('overall_median')}, "
            f"max {rng.get('high_group')}={rng.get('high')}, "
            f"min {rng.get('low_group')}={rng.get('low')}, "
            f"кратность {rng.get('ratio')}."
        )
        notable = [
            g for g in profile.get("groups") or []
            if g.get("flags")
        ][:6]
        for g in notable:
            lines.append(
                f"  • {g['value']}: n={g['count']}, med={g['median']}, "
                f"vs overall×{g.get('median_vs_overall')} [{', '.join(g['flags'])}]"
            )
        lines.append("")

    for test in discovery.get("tests") or []:
        lines.append(f"Тест: {test.get('detail')}")

    for item in discovery.get("derived") or []:
        lines.append(
            f"Производная {item['name']}: med={item['median']}, mean={item['mean']}, "
            f"min={item['min']}, max={item['max']}"
        )

    text = "\n".join(lines).strip()
    if len(text) > limit:
        return text[:limit] + "\n… (сокращено)"
    return text


def format_discovery_report(discovery: dict) -> str:
    return format_discovery_brief(discovery, limit=20000)


def discover_insights(
    df: pd.DataFrame,
    parsed_structure: dict | None = None,
    correlations: dict | None = None,
) -> dict:
    roles = infer_column_roles(df, parsed_structure)
    work, derived = compute_derived_metrics(df, roles)

    cat_for_conc = list(dict.fromkeys(
        (roles.get("geo") or [])
        + (roles.get("currency") or [])
        + (roles.get("categorical") or [])
    ))
    concentration = compute_concentration(work, cat_for_conc, roles)
    outlier_cols = list(dict.fromkeys(
        (roles.get("money") or [])
        + (roles.get("area") or [])
        + (roles.get("numeric") or [])
        + [d["name"] for d in derived]
    ))
    outliers = compute_numeric_outliers(work, outlier_cols)
    implausible = compute_implausible(work, roles)
    label_cols = list(dict.fromkeys((roles.get("geo") or []) + (roles.get("categorical") or [])))
    duplicates = compute_label_duplicates(work, label_cols)

    profile_cats = list(dict.fromkeys((roles.get("geo") or []) + (roles.get("currency") or []) + (roles.get("categorical") or [])[:4]))
    profile_nums = list(dict.fromkeys(
        (roles.get("money") or [])
        + [d["name"] for d in derived]
        + (roles.get("numeric") or [])[:3]
    ))
    group_profiles = compute_group_profiles(work, profile_cats, profile_nums)
    tests = compute_tests(work, roles, correlations)
    highlights = _highlights_from_parts(
        concentration, outliers, implausible, duplicates, tests, derived
    )

    discovery = convert_numpy_types({
        "roles": roles,
        "derived": derived,
        "highlights": highlights,
        "concentration": concentration,
        "outliers": outliers,
        "implausible": implausible,
        "label_duplicates": duplicates,
        "group_profiles": group_profiles,
        "tests": tests,
        "kind_labels": KIND_LABELS,
    })
    discovery["hypotheses"] = hypotheses_from_discovery(discovery)
    return discovery
