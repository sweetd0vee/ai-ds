import logging
import pandas as pd

logger = logging.getLogger(__name__)


def preprocess_dates_based_on_llm(df: pd.DataFrame, datetime_columns: list) -> pd.DataFrame:
    df_processed = df.copy()
    if not datetime_columns:
        return df_processed

    for col in datetime_columns:
        if col not in df_processed.columns:
            logger.warning("Столбец '%s' не найден в DataFrame.", col)
            continue
        try:
            df_processed[col] = pd.to_datetime(df_processed[col], errors="coerce")
        except Exception as e:
            logger.error("Не удалось преобразовать столбец '%s': %s", col, e)

    return df_processed


def handle_missing_values_before_analysis(
    df: pd.DataFrame, metrics_plan_dict: dict
) -> pd.DataFrame:
    if not metrics_plan_dict:
        return df.copy()

    df_handled = df.copy()
    for col in metrics_plan_dict.keys():
        if col not in df_handled.columns:
            continue

        dtype = df_handled[col].dtype
        if pd.api.types.is_datetime64_any_dtype(dtype):
            df_handled = df_handled.dropna(subset=[col])
            continue

        if df_handled[col].isna().any():
            if pd.api.types.is_numeric_dtype(dtype):
                df_handled[col] = df_handled[col].fillna(0)
            else:
                df_handled[col] = df_handled[col].fillna("нет данных")

    return df_handled
