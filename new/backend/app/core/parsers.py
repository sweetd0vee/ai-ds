import re
import logging

logger = logging.getLogger(__name__)


def parse_struct_analyze_response(response_text: str) -> dict:
    parsed_data = {"columns": [], "datetime_candidates": []}

    columns_match = re.search(
        r"---COLUMNS_START---(.*?)---COLUMNS_END---", response_text, re.DOTALL
    )
    if columns_match:
        columns_text = columns_match.group(1).strip()
        column_blocks = re.split(r"\n\s*\n", columns_text)
        for block in column_blocks:
            if not block.strip():
                continue
            lines = block.strip().split("\n")
            col_info = {}
            for line in lines:
                if line.startswith("Столбец:"):
                    col_info["name"] = line[len("Столбец:") :].strip()
                elif line.startswith("Тип:"):
                    col_info["type"] = line[len("Тип:") :].strip()
                elif line.startswith("Описание:"):
                    col_info["description"] = line[len("Описание:") :].strip()
            if col_info:
                parsed_data["columns"].append(col_info)
    else:
        logger.warning("Не найден блок ---COLUMNS_START---...---COLUMNS_END---")
        return {}

    datetime_match = re.search(
        r"---DATETIME_CANDIDATES_START---(.*?)---DATETIME_CANDIDATES_END---",
        response_text,
        re.DOTALL,
    )
    if datetime_match:
        datetime_text = datetime_match.group(1).strip()
        if datetime_text:
            parsed_data["datetime_candidates"] = [
                name.strip() for name in datetime_text.split(",") if name.strip()
            ]

    return parsed_data


def parse_metrics_plan_response(response_text: str) -> dict:
    parsed_data = {}
    metrics_match = re.search(
        r"---METRICS_START---(.*?)---METRICS_END---", response_text, re.DOTALL
    )
    if metrics_match:
        metrics_text = metrics_match.group(1).strip()
        column_blocks = re.split(r"\n\s*\n", metrics_text)
        for block in column_blocks:
            if not block.strip():
                continue
            lines = block.strip().split("\n")
            col_name = None
            metrics_list = []
            for line in lines:
                if line.startswith("Столбец:"):
                    col_name = line[len("Столбец:") :].strip()
                elif line.startswith("Метрики:"):
                    metrics_str = line[len("Метрики:") :].strip()
                    metrics_list = [m.strip() for m in metrics_str.split(",") if m.strip()]
            if col_name:
                parsed_data[col_name] = metrics_list
    else:
        logger.warning("Не найден блок ---METRICS_START---...---METRICS_END---")
        return {}

    return parsed_data
