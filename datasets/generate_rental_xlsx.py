"""Synthetic rental datasets: listings 1000x10 and contracts 2000x20."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
OUT_DIR = Path(__file__).resolve().parent

CITIES = [
    dict(city="Минск", country="Беларусь", currency="BYN", ppm=13.5, sigma=2.8, w=0.18),
    dict(city="Москва", country="Россия", currency="RUB", ppm=1850.0, sigma=380, w=0.16),
    dict(city="Варшава", country="Польша", currency="PLN", ppm=78.0, sigma=14, w=0.12),
    dict(city="Берлин", country="Германия", currency="EUR", ppm=23.5, sigma=4.8, w=0.10),
    dict(city="Прага", country="Чехия", currency="CZK", ppm=490.0, sigma=85, w=0.08),
    dict(city="Вильнюс", country="Литва", currency="EUR", ppm=15.8, sigma=3.2, w=0.08),
    dict(city="Киев", country="Украина", currency="UAH", ppm=430.0, sigma=90, w=0.08),
    dict(city="Стамбул", country="Турция", currency="TRY", ppm=880.0, sigma=190, w=0.07),
    dict(city="Дубай", country="ОАЭ", currency="AED", ppm=115.0, sigma=28, w=0.07),
    dict(city="Лондон", country="Великобритания", currency="GBP", ppm=49.0, sigma=11, w=0.06),
]

HISTORIC_CITIES = {"Прага", "Берлин", "Лондон"}
EU_CITIES = {"Берлин", "Прага", "Вильнюс", "Варшава"}
HIGH_COMMISSION = {"Дубай", "Лондон"}

PROPERTY_TYPES = [
    dict(name="Студия", w=0.12, rooms=(1, 1), area_per_room=26, ppm_k=1.28),
    dict(name="Квартира", w=0.44, rooms=(1, 4), area_per_room=22, ppm_k=1.00),
    dict(name="Апартаменты", w=0.10, rooms=(1, 4), area_per_room=28, ppm_k=1.38),
    dict(name="Дом", w=0.08, rooms=(3, 7), area_per_room=32, ppm_k=0.82),
    dict(name="Офис", w=0.14, rooms=(1, 8), area_per_room=18, ppm_k=1.18),
    dict(name="Склад", w=0.04, rooms=(0, 0), area_per_room=0, ppm_k=0.32),
    dict(name="Коммерческое помещение", w=0.08, rooms=(1, 4), area_per_room=24, ppm_k=1.12),
]

TENANT_TYPES = ["физлицо", "юрлицо"]
STATUSES = ["активен", "завершён", "расторгнут", "просрочен", "запланирован"]
NATIONALITIES = [
    "белорус", "россиянин", "поляк", "немец", "чех", "литвин",
    "украинец", "турок", "эмиратец", "британец", "индиец", "китаец",
]
CITY_NATIONALITY = {
    "Минск": "белорус",
    "Москва": "россиянин",
    "Варшава": "поляк",
    "Берлин": "немец",
    "Прага": "чех",
    "Вильнюс": "литвин",
    "Киев": "украинец",
    "Стамбул": "турок",
    "Дубай": "индиец",
    "Лондон": "британец",
}

TODAY = date(2026, 8, 31)


def _choice(rng: np.random.Generator, items: list, p=None, size=None):
    if p is not None:
        p = np.asarray(p, dtype=float)
        p = p / p.sum()
    idx = rng.choice(len(items), size=size, p=p)
    if size is None:
        return items[int(idx)]
    return [items[int(i)] for i in idx]


def _clip_round(value: float, digits: int = 2, lo: float | None = None) -> float:
    if lo is not None:
        value = max(lo, value)
    return round(float(value), digits)


def generate_listings(rng: np.random.Generator, n: int = 1000) -> pd.DataFrame:
    city_w = np.array([c["w"] for c in CITIES], dtype=float)
    city_w /= city_w.sum()
    type_w = np.array([t["w"] for t in PROPERTY_TYPES], dtype=float)
    type_w /= type_w.sum()

    rows = []
    for i in range(n):
        city = CITIES[int(rng.choice(len(CITIES), p=city_w))]
        ptype = PROPERTY_TYPES[int(rng.choice(len(PROPERTY_TYPES), p=type_w))]
        rooms = int(rng.integers(ptype["rooms"][0], ptype["rooms"][1] + 1))
        if ptype["name"] == "Склад":
            area = float(rng.uniform(220, 1400))
        else:
            area = rooms * ptype["area_per_room"] * rng.uniform(0.88, 1.14) + rng.normal(0, 3)
            area = float(np.clip(area, 16 if ptype["name"] == "Студия" else 22, 420))
        year = int(rng.integers(1952, 2025))
        if rng.random() < 0.07:
            year = int(rng.integers(1890, 1945))

        ppm = rng.normal(city["ppm"], city["sigma"]) * ptype["ppm_k"]
        age = 2026 - year
        ppm *= 1.0 - 0.0035 * age
        if city["city"] in HISTORIC_CITIES and year < 1940:
            ppm *= 1.28
        if rooms >= 4 and ptype["name"] in {"Квартира", "Апартаменты", "Дом"}:
            ppm *= 0.96
        ppm = max(city["ppm"] * 0.25, ppm)
        rent = area * ppm * rng.uniform(0.97, 1.03)

        rows.append({
            "ID объявления": f"LST-{i + 1:04d}",
            "Город": city["city"],
            "Страна": city["country"],
            "Валюта": city["currency"],
            "Площадь, м²": _clip_round(area, 1, 8),
            "Арендная плата, мес.": _clip_round(rent, 2, 1),
            "Цена за м²": _clip_round(ppm, 2, 0.1),
            "Тип недвижимости": ptype["name"],
            "Комнат": rooms,
            "Год постройки": year,
        })

    df = pd.DataFrame(rows)
    _inject_listing_anomalies(df, rng)
    return df


def _inject_listing_anomalies(df: pd.DataFrame, rng: np.random.Generator) -> None:
    n = len(df)
    luxury = rng.choice(n, size=12, replace=False)
    for i in luxury:
        df.at[i, "Цена за м²"] = _clip_round(df.at[i, "Цена за м²"] * rng.uniform(3.8, 6.5), 2)
        df.at[i, "Арендная плата, мес."] = _clip_round(
            df.at[i, "Площадь, м²"] * df.at[i, "Цена за м²"], 2
        )
        if df.at[i, "Тип недвижимости"] in {"Квартира", "Студия"}:
            df.at[i, "Тип недвижимости"] = "Апартаменты"

    cheap = rng.choice([i for i in range(n) if i not in set(luxury)], size=8, replace=False)
    for i in cheap:
        df.at[i, "Цена за м²"] = _clip_round(df.at[i, "Цена за м²"] * rng.uniform(0.12, 0.28), 2)
        df.at[i, "Арендная плата, мес."] = _clip_round(
            df.at[i, "Площадь, м²"] * df.at[i, "Цена за м²"], 2
        )

    used = set(luxury) | set(cheap)
    rest = [i for i in range(n) if i not in used]

    for i in rng.choice(rest, size=4, replace=False):
        df.at[i, "Площадь, м²"] = float(rng.choice([1.0, 2.5, 8500.0, 9999.0]))
        used.add(i)

    rest = [i for i in range(n) if i not in used]
    for i in rng.choice(rest, size=5, replace=False):
        df.at[i, "Арендная плата, мес."] = 0.0
        used.add(i)

    rest = [i for i in range(n) if i not in used]
    years = [1888, 1891, 2027, 2031, 1805, 2100]
    for i, year in zip(rng.choice(rest, size=6, replace=False), years):
        df.at[i, "Год постройки"] = year
        used.add(int(i))

    rest = [i for i in range(n) if i not in used]
    mismatch_idx = rng.choice(rest, size=8, replace=False)
    mismatch_cur = ["USD", "EUR", "USD", "GBP", "CNY", "USD", "EUR", "KZT"]
    for i, cur in zip(mismatch_idx, mismatch_cur):
        df.at[int(i), "Валюта"] = cur
        used.add(int(i))

    rest = [i for i in range(n) if i not in used]
    for i in rng.choice(rest, size=20, replace=False):
        factor = float(rng.choice([0.45, 0.55, 1.7, 2.4, 3.1]))
        df.at[i, "Цена за м²"] = _clip_round(df.at[i, "Цена за м²"] * factor, 2)
        used.add(int(i))

    rest = [i for i in range(n) if i not in used]
    miss_cols = ["Город", "Валюта", "Год постройки", "Комнат", "Тип недвижимости"]
    for i, col in zip(rng.choice(rest, size=15, replace=False), (miss_cols * 4)[:15]):
        df.at[int(i), col] = np.nan
        used.add(int(i))

    rest = [i for i in range(n) if i not in used]
    typos = [("Минск", "г. Минск"), ("Москва", "Масква"), ("Берлин", "Berlin"), ("Варшава", "Warsaw")]
    for i, (src, dst) in zip(rng.choice(rest, size=4, replace=False), typos):
        if df.at[int(i), "Город"] == src:
            df.at[int(i), "Город"] = dst


def generate_contracts(rng: np.random.Generator, listings: pd.DataFrame, n: int = 2000) -> pd.DataFrame:
    valid = listings.dropna(subset=["ID объявления", "Город", "Страна", "Валюта"]).copy()
    ids = valid["ID объявления"].tolist()
    listing_map = valid.set_index("ID объявления").to_dict("index")

    popularity = []
    for lid in ids:
        row = listing_map[lid]
        rent = float(row["Арендная плата, мес."] or 1)
        area = float(row["Площадь, м²"] or 1)
        score = 1.0 / max(rent / max(area, 1), 0.1)
        if row["Тип недвижимости"] in {"Квартира", "Студия", "Апартаменты"}:
            score *= 1.4
        if row.get("Город") in {"Минск", "Москва", "Варшава"}:
            score *= 1.2
        popularity.append(max(score, 0.05))
    popularity = np.array(popularity, dtype=float)
    popularity /= popularity.sum()

    counts = rng.poisson(1.85, size=len(ids))
    extra = n - 18 - int(counts.sum())
    if extra > 0:
        extra_idx = rng.choice(len(ids), size=extra, p=popularity)
        for i in extra_idx:
            counts[i] += 1
    elif extra < 0:
        order = np.argsort(-counts)
        for i in order:
            if extra >= 0:
                break
            if counts[i] > 0:
                counts[i] -= 1
                extra += 1

    rows = []
    seq = 1
    city_med_ppm = valid.groupby("Город")["Цена за м²"].median().to_dict()

    for lid, k in zip(ids, counts):
        src = listing_map[lid]
        for j in range(int(k)):
            rows.append(_one_contract(rng, seq, lid, src, j, city_med_ppm))
            seq += 1

    while len(rows) < n - 18:
        lid = ids[int(rng.choice(len(ids), p=popularity))]
        rows.append(_one_contract(rng, seq, lid, listing_map[lid], 9, city_med_ppm))
        seq += 1

    ghost_cities = CITIES
    for _ in range(18):
        city = ghost_cities[int(rng.integers(0, len(ghost_cities)))]
        ghost_id = f"LST-9{rng.integers(800, 999):03d}"
        fake = {
            "Город": city["city"],
            "Страна": city["country"],
            "Валюта": city["currency"],
            "Арендная плата, мес.": _clip_round(rng.uniform(300, 2500), 2),
            "Площадь, м²": _clip_round(rng.uniform(30, 90), 1),
            "Цена за м²": city["ppm"],
            "Тип недвижимости": "Квартира",
            "Год постройки": 2005,
        }
        rows.append(_one_contract(rng, seq, ghost_id, fake, 0, city_med_ppm))
        seq += 1

    df = pd.DataFrame(rows[:n])
    _inject_contract_anomalies(df, rng)
    return df


def _one_contract(
    rng: np.random.Generator,
    seq: int,
    listing_id: str,
    src: dict,
    wave: int,
    city_med_ppm: dict,
) -> dict:
    city = src.get("Город") if isinstance(src.get("Город"), str) else "Минск"
    country = src.get("Страна") if isinstance(src.get("Страна"), str) else "Беларусь"
    currency = src.get("Валюта") if isinstance(src.get("Валюта"), str) else "BYN"
    base_rent = float(src.get("Арендная плата, мес.") or 500)
    area = float(src.get("Площадь, м²") or 40)
    year_built = int(src.get("Год постройки") or 2000) if pd.notna(src.get("Год постройки")) else 2000
    ptype = src.get("Тип недвижимости") or "Квартира"

    corporate_p = 0.42 if ptype in {"Офис", "Склад", "Коммерческое помещение"} else 0.16
    tenant_type = "юрлицо" if rng.random() < corporate_p else "физлицо"

    start = date(2023, 6, 1) + timedelta(days=int(rng.integers(0, 1200)))
    ppm = float(src.get("Цена за м²") or 1)
    med = float(city_med_ppm.get(city) or ppm or 1)
    rel = ppm / med if med else 1.0
    if tenant_type == "юрлицо":
        months = int(rng.choice([12, 24, 36], p=[0.30, 0.45, 0.25]))
    else:
        months = int(np.clip(round(rng.normal(24 - 9 * rel, 4)), 3, 36))

    end = start + timedelta(days=months * 30)
    inflation = 1.0 + 0.045 * wave + rng.normal(0, 0.02)
    if tenant_type == "юрлицо":
        inflation *= rng.uniform(1.04, 1.12)
    if city in {"Дубай", "Лондон"} and tenant_type == "физлицо" and rng.random() < 0.35:
        inflation *= rng.uniform(1.08, 1.18)
    rent = _clip_round(base_rent * max(0.7, inflation), 2, 1)

    deposit_months = 2.0 if city in HIGH_COMMISSION else (1.0 if tenant_type == "юрлицо" else 1.5)
    if city == "Лондон":
        deposit_months = 1.15
    deposit = _clip_round(rent * deposit_months * rng.uniform(0.95, 1.05), 2)

    late_p = 0.35 if tenant_type == "физлицо" else 0.12
    late = int(rng.poisson(2.2 if rng.random() < late_p else 0.3))
    late = min(late, 14)

    age = max(0, 2026 - year_built)
    maintenance = area * rng.uniform(0.35, 0.85) * (1 + 0.015 * age)
    if ptype in {"Склад", "Дом"}:
        maintenance *= 1.4
    maintenance = _clip_round(maintenance, 2, 0)

    utilities = "Да" if (city in EU_CITIES and rng.random() < 0.62) or rng.random() < 0.18 else "Нет"
    if utilities == "Да":
        rent = _clip_round(rent * rng.uniform(1.03, 1.08), 2)

    rating = 4.3 - 0.28 * late + (0.25 if year_built >= 2015 else 0) + rng.normal(0, 0.35)
    rating = float(np.clip(round(rating * 2) / 2, 1.0, 5.0))

    nat_local = CITY_NATIONALITY.get(city, "белорус")
    if rng.random() < (0.45 if city in {"Дубай", "Лондон", "Берлин"} else 0.18):
        nationality = _choice(rng, [x for x in NATIONALITIES if x != nat_local])
        if city in {"Дубай", "Лондон"}:
            rent = _clip_round(rent * rng.uniform(1.03, 1.10), 2)
    else:
        nationality = nat_local

    if city in HIGH_COMMISSION:
        commission = _clip_round(rng.uniform(90, 145), 1)
    elif city in {"Минск", "Москва", "Киев"}:
        commission = float(rng.choice([50, 75, 100]))
    else:
        commission = _clip_round(rng.uniform(40, 90), 1)

    if end < TODAY and late >= 5:
        status = "расторгнут"
    elif start > TODAY:
        status = "запланирован"
    elif end < TODAY:
        status = "завершён"
    elif late >= 3:
        status = "просрочен"
    else:
        status = "активен"

    payment_day = int(rng.choice([1, 5, 10, 15], p=[0.45, 0.25, 0.20, 0.10]))
    tenant_id = f"TNT-{int(rng.integers(1, 720)):04d}"

    return {
        "ID договора": f"CTR-{seq:05d}",
        "ID объявления": listing_id,
        "Город": city,
        "Страна": country,
        "Валюта": currency,
        "ID арендатора": tenant_id,
        "Дата начала": start,
        "Дата окончания": end,
        "Арендная плата, мес.": rent,
        "Залог": deposit,
        "День платежа": payment_day,
        "Срок аренды, мес.": months,
        "Тип арендатора": tenant_type,
        "Кол-во просрочек": late,
        "Расходы на содержание": maintenance,
        "Коммунальные включены": utilities,
        "Рейтинг объекта": rating,
        "Гражданство арендатора": nationality,
        "Комиссия агента, %": commission,
        "Статус договора": status,
    }


def _inject_contract_anomalies(df: pd.DataFrame, rng: np.random.Generator) -> None:
    n = len(df)
    idx = rng.choice(n, size=5, replace=False)
    for i in idx:
        start, end = df.at[i, "Дата начала"], df.at[i, "Дата окончания"]
        df.at[i, "Дата начала"] = end
        df.at[i, "Дата окончания"] = start
        df.at[i, "Срок аренды, мес."] = -abs(int(df.at[i, "Срок аренды, мес."]))

    for i in rng.choice(n, size=7, replace=False):
        df.at[i, "Залог"] = _clip_round(float(df.at[i, "Арендная плата, мес."]) * rng.uniform(8, 14), 2)

    for i in rng.choice(n, size=3, replace=False):
        df.at[i, "Расходы на содержание"] = _clip_round(-abs(float(df.at[i, "Расходы на содержание"])), 2)

    for i in rng.choice(n, size=10, replace=False):
        df.at[i, "ID арендатора"] = np.nan

    for i in rng.choice(n, size=8, replace=False):
        df.at[i, "Рейтинг объекта"] = float(rng.choice([0.0, 6.5, 9.0]))

    for i in rng.choice(n, size=6, replace=False):
        df.at[i, "Статус договора"] = np.nan

    for i in rng.choice(n, size=4, replace=False):
        df.at[i, "Арендная плата, мес."] = _clip_round(float(df.at[i, "Арендная плата, мес."]) * 25, 2)


def main() -> None:
    rng = np.random.default_rng(SEED)
    listings = generate_listings(rng, 1000)
    contracts = generate_contracts(rng, listings, 2000)

    listings_path = OUT_DIR / "rental_listings_10x1000.xlsx"
    contracts_path = OUT_DIR / "rental_contracts_20x2000.xlsx"
    listings.to_excel(listings_path, sheet_name="Объекты", index=False)
    contracts.to_excel(contracts_path, sheet_name="Договоры", index=False)

    overlap = set(listings["ID объявления"]) & set(contracts["ID объявления"])
    print(f"listings: {listings.shape} -> {listings_path.name}")
    print(f"contracts: {contracts.shape} -> {contracts_path.name}")
    print(f"join overlap: {len(overlap)}")
    print("ok")


if __name__ == "__main__":
    main()
