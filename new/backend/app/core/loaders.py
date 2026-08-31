import re
from pathlib import Path

import pandas as pd


MAX_UPLOAD_FILES = 10
MAX_TABLES = 20
ALLOWED_EXTS = {".csv", ".xlsx"}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [" ".join(str(c).split()) for c in df.columns]
    return df


def _slug(text: str) -> str:
    slug = re.sub(r"[^\w]+", "_", str(text), flags=re.UNICODE).strip("_")
    return slug or "table"


def _unique_id(base: str, existing: set[str]) -> str:
    name = _slug(base)
    if name not in existing:
        return name
    i = 2
    while f"{name}_{i}" in existing:
        i += 1
    return f"{name}_{i}"


def load_dataframe(file_path: str) -> pd.DataFrame:
    path = str(file_path)
    if path.endswith(".csv"):
        try:
            df = pd.read_csv(path, encoding="utf-8")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(path, encoding="latin1")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="cp1251")
        return _normalize_columns(df)
    if path.endswith(".xlsx"):
        return _normalize_columns(pd.read_excel(path))
    raise ValueError("Поддерживаются только .csv и .xlsx файлы.")


def _load_csv(path: str) -> pd.DataFrame:
    return load_dataframe(path)


def _load_excel_sheets(path: str) -> list[tuple[str | None, pd.DataFrame]]:
    with pd.ExcelFile(path) as xl:
        names = list(xl.sheet_names)
        sheets: list[tuple[str | None, pd.DataFrame]] = []
        for sheet in names:
            df = _normalize_columns(pd.read_excel(xl, sheet_name=sheet))
            if df.empty or len(df.columns) == 0:
                continue
            label = sheet if len(names) > 1 else None
            sheets.append((label, df))
    if not sheets:
        raise ValueError(f"В файле нет заполненных листов: {Path(path).name}")
    return sheets


def load_tables(file_entries: list[tuple[str, str]]) -> list[dict]:
    """Загружает один или несколько файлов как именованные таблицы.

    file_entries: [(path, original_filename), ...]
    """
    if not file_entries:
        raise ValueError("Не указаны файлы для загрузки")

    tables: list[dict] = []
    used_ids: set[str] = set()

    for path, original_name in file_entries:
        filename = Path(original_name or path).name
        stem = Path(filename).stem
        ext = Path(filename).suffix.lower() or Path(path).suffix.lower()

        if ext == ".csv":
            sheets = [(None, _load_csv(path))]
        elif ext == ".xlsx":
            sheets = _load_excel_sheets(path)
        else:
            raise ValueError(f"Неподдерживаемый формат: {filename}")

        for sheet, df in sheets:
            display = f"{filename} / {sheet}" if sheet else filename
            table_id = _unique_id(f"{stem}_{sheet}" if sheet else stem, used_ids)
            used_ids.add(table_id)
            tables.append({
                "id": table_id,
                "name": display,
                "filename": filename,
                "sheet": sheet,
                "path": str(path),
                "rows": int(df.shape[0]),
                "cols": int(df.shape[1]),
                "columns": [str(c) for c in df.columns],
                "df": df,
            })
            if len(tables) >= MAX_TABLES:
                return tables

    if not tables:
        raise ValueError("Не удалось загрузить данные или файлы пусты")
    return tables


def tables_meta(tables: list[dict], preview_rows: int = 20) -> list[dict]:
    meta = []
    for table in tables:
        df = table["df"]
        preview = df.head(preview_rows).fillna("").astype(str).to_dict(orient="records")
        meta.append({
            "id": table["id"],
            "name": table["name"],
            "filename": table["filename"],
            "sheet": table.get("sheet"),
            "rows": table["rows"],
            "cols": table["cols"],
            "columns": table["columns"],
            "preview": preview,
            "shape": [table["rows"], table["cols"]],
        })
    return meta
