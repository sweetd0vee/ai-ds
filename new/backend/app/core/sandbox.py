"""Выполнение пользовательского Python-кода в контексте задачи."""

import contextlib
import io
import logging
import traceback

import numpy as np
import pandas as pd

from .data_analysis import compute_metrics, format_metrics_results
from .loaders import load_dataframe
from .preprocess import preprocess_dates_based_on_llm
from .utils import extract_python_code, static_code_analysis

logger = logging.getLogger(__name__)

SANDBOX_IMPORTS = [
    "import pandas as pd",
    "import numpy as np",
]


def run_sandbox_code(
    code: str,
    file_path: str,
    datetime_candidates: list | None = None,
    metrics_plan: dict | None = None,
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
    warnings = static_code_analysis(final_code, "sandbox")

    df = load_dataframe(file_path)
    if df is None or df.empty:
        return {
            "success": False,
            "output": "",
            "error": "Не удалось загрузить данные задачи",
            "warnings": warnings,
        }

    if datetime_candidates:
        df = preprocess_dates_based_on_llm(df, datetime_candidates)

    namespace = {
        "df": df,
        "pd": pd,
        "np": np,
        "metrics_plan": metrics_plan or {},
        "compute_metrics": compute_metrics,
        "format_metrics_results": format_metrics_results,
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
