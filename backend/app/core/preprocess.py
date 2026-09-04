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
