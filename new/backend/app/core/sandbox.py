"""Выполнение пользовательского Python-кода в контексте задачи."""

import contextlib
import io
import logging
import pickle
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

from .data_analysis import compute_metrics, format_metrics_results, format_metrics_summary
from .loaders import load_dataframe, load_tables
from .preprocess import preprocess_dates_based_on_llm
from .utils import extract_python_code, static_code_analysis

logger = logging.getLogger(__name__)

SANDBOX_IMPORTS = [
    "import pandas as pd",
    "import numpy as np",
]


def _load_analysis_frame(analysis_path: str | None, file_path: str, datetime_candidates: list | None):
    if analysis_path:
        path = Path(analysis_path)
        if path.exists():
            with path.open("rb") as fh:
                df = pickle.load(fh)
            if datetime_candidates:
                df = preprocess_dates_based_on_llm(df, datetime_candidates)
            return df
    df = load_dataframe(file_path)
    if datetime_candidates:
        df = preprocess_dates_based_on_llm(df, datetime_candidates)
    return df


def _load_named_tables(file_paths: list[str] | None, filenames: list[str] | None) -> dict[str, pd.DataFrame]:
    if not file_paths:
        return {}
    names = filenames or []
    entries = [
        (path, names[i] if i < len(names) else Path(path).name)
        for i, path in enumerate(file_paths)
    ]
    tables = load_tables(entries)
    return {table["id"]: table["df"] for table in tables}


def run_sandbox_code(
    code: str,
    file_path: str,
    datetime_candidates: list | None = None,
    metrics_plan: dict | None = None,
    file_paths: list[str] | None = None,
    filenames: list[str] | None = None,
    analysis_path: str | None = None,
) -> dict:
    clean_code = extract_python_code(code or "")
    if not clean_code.strip():
        return {
            "success": False,
            "output": "",
            "error": "Код пустой",
            "warnings": [],
        }

    final_code = "\n".join(SANDBOX_IMPORTS + [clean_code])
    warnings = static_code_analysis(final_code)

    try:
        df = _load_analysis_frame(analysis_path, file_path, datetime_candidates)
    except Exception:
        logger.exception("Sandbox failed to load analysis frame")
        df = None
    if df is None or getattr(df, "empty", True):
        return {
            "success": False,
            "output": "",
            "error": "Не удалось загрузить данные задачи",
            "warnings": warnings,
        }

    try:
        dfs = _load_named_tables(file_paths, filenames)
    except Exception:
        logger.exception("Sandbox failed to load source tables")
        dfs = {}

    namespace = {
        "df": df,
        "dfs": dfs,
        "tables": list(dfs.keys()),
        "pd": pd,
        "np": np,
        "metrics_plan": metrics_plan or {},
        "compute_metrics": compute_metrics,
        "format_metrics_results": format_metrics_results,
        "format_metrics_summary": format_metrics_summary,
    }

    stdout = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout):
            exec(final_code, namespace, namespace)  # noqa: S102
        output = stdout.getvalue().strip()
        return {
            "success": True,
            "output": output,
            "error": None,
            "warnings": warnings,
        }
    except Exception:
        logger.exception("Sandbox execution failed")
        return {
            "success": False,
            "output": stdout.getvalue().strip(),
            "error": traceback.format_exc(),
            "warnings": warnings,
        }
