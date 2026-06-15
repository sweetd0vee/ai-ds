import re
import ast
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def extract_python_code(markdown_text) -> str:
    if not isinstance(markdown_text, str):
        return str(markdown_text)
    pattern = r"```(?:python|Python)\s*(.*?)\s*```"
    match = re.search(pattern, markdown_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    cleaned_text = re.sub(r"```.*?\n", "", markdown_text)
    cleaned_text = re.sub(r"```", "", cleaned_text)
    return cleaned_text.strip()


def convert_numpy_types(obj):
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            if isinstance(k, (np.integer, np.floating)):
                try:
                    new_key = k.item()
                except (AttributeError, ValueError):
                    new_key = str(k)
            elif isinstance(k, (pd.Timestamp, pd.Timedelta)) or hasattr(k, "isoformat"):
                try:
                    new_key = k.isoformat()
                except Exception:
                    new_key = str(k)
            elif not isinstance(k, (str, int, float, bool)) or k is None:
                new_key = str(k)
            else:
                new_key = k
            new_dict[new_key] = convert_numpy_types(v)
        return new_dict
    if isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        if np.isnan(obj) or np.isinf(obj):
            return str(obj)
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.str_):
        return str(obj)
    if isinstance(obj, np.ndarray):
        try:
            if obj.ndim == 0:
                return convert_numpy_types(obj.item())
            return obj.tolist()
        except Exception:
            return str(obj)
    if isinstance(obj, (pd.Timestamp, pd.Timedelta)):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)
    if hasattr(obj, "isoformat"):
        try:
            return obj.isoformat()
        except Exception:
            return str(obj)
    return obj


def static_code_analysis(code_str: str, context_name: str = "") -> list[str]:
    warnings = []
    try:
        ast.parse(code_str)
    except SyntaxError as e:
        warnings.append(f"Синтаксическая ошибка: {e}")
        return warnings

    lines = code_str.split("\n")
    for i, line in enumerate(lines):
        if ".resample(" in line and not (
            "set_index(" in code_str
            and code_str.find("set_index(") < code_str.find(".resample(")
        ):
            if line.strip().startswith("df.") or ".resample(" in line.split("=")[-1]:
                warnings.append(
                    f"Потенциальная проблема resample в строке {i + 1}: {line.strip()}"
                )
    return warnings


def build_file_info_summary(df: pd.DataFrame, label: str = "сырые данные") -> str:
    from io import StringIO

    buffer = StringIO()
    df.info(buf=buffer)
    df_info = buffer.getvalue()
    return (
        f"DataFrame Info ({label}):\n{df_info}\n"
        f"DataFrame Head:\n{df.head(10).to_string()}\n"
        f"DataFrame Dtypes:\n{df.dtypes.to_string()}\n"
        f"DataFrame Shape: {df.shape}\n"
    )


def build_df_structure_info(df: pd.DataFrame) -> str:
    info = f"DataFrame имеет {df.shape[0]} строк и {df.shape[1]} столбцов.\n"
    info += "Типы данных столбцов (после обработки):\n"
    for col in df.columns:
        info += f"  - {col}: {df[col].dtype}\n"
    return info
