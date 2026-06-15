import pandas as pd


def load_dataframe(file_path: str) -> pd.DataFrame:
    if file_path.endswith(".csv"):
        try:
            return pd.read_csv(file_path, encoding="utf-8")
        except UnicodeDecodeError:
            try:
                return pd.read_csv(file_path, encoding="latin1")
            except UnicodeDecodeError:
                return pd.read_csv(file_path, encoding="cp1251")
    if file_path.endswith(".xlsx"):
        return pd.read_excel(file_path)
    raise ValueError("Поддерживаются только .csv и .xlsx файлы.")
