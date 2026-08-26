import pandas as pd


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [" ".join(str(c).split()) for c in df.columns]
    return df


def load_dataframe(file_path: str) -> pd.DataFrame:
    if file_path.endswith(".csv"):
        try:
            df = pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(file_path, encoding="latin1")
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, encoding="cp1251")
        return _normalize_columns(df)
    if file_path.endswith(".xlsx"):
        return _normalize_columns(pd.read_excel(file_path))
    raise ValueError("Поддерживаются только .csv и .xlsx файлы.")
