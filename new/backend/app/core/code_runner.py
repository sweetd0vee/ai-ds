import contextlib
import io
import logging
import traceback

from .loaders import load_dataframe
from .preprocess import preprocess_dates_based_on_llm, handle_missing_values_before_analysis
from .utils import extract_python_code, static_code_analysis

logger = logging.getLogger(__name__)


def safe_code_execution(
    code: str,
    file_path: str,
    context_name: str,
    datetime_candidates: list,
    metrics_plan_dict: dict,
    required_imports: list[str] | None = None,
) -> tuple[str, list[str]]:
    if required_imports is None:
        required_imports = []

    clean_code = extract_python_code(code)
    final_code_lines = list(required_imports) + clean_code.split("\n")
    final_code_to_execute = "\n".join(final_code_lines)

    warnings = static_code_analysis(final_code_to_execute, context_name)
    logger.info("Статический анализ %s: %s предупреждений", context_name, len(warnings))

    df = load_dataframe(file_path)
    if datetime_candidates:
        df = preprocess_dates_based_on_llm(df, datetime_candidates)
    if context_name in ("расчета метрик", "визуализации") and metrics_plan_dict:
        df = handle_missing_values_before_analysis(df, metrics_plan_dict)

    namespace = {"df": df}
    stdout = io.StringIO()
    stderr = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            exec(final_code_to_execute, namespace, namespace)  # noqa: S102
        parts = [stdout.getvalue(), stderr.getvalue()]
        output = "\n".join(p for p in parts if p).strip()
        return output, warnings
    except Exception:
        logger.exception("Ошибка выполнения кода (%s)", context_name)
        parts = [stdout.getvalue(), stderr.getvalue(), traceback.format_exc()]
        output = "\n".join(p for p in parts if p).strip()
        return output, warnings
