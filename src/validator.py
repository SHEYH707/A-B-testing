"""Проверка структуры и содержимого экспериментальных данных."""

import pandas as pd

REQUIRED_COLUMNS = ["user_id", "timestamp", "group", "landing_page", "converted"]
ALLOWED_GROUPS = ["control", "treatment"]
ALLOWED_PAGES = ["old_page", "new_page"]


class ValidationError(ValueError):
    """Ошибка проверки экспериментальных данных."""


def validate_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """
    Проверить и подготовить данные A/B-эксперимента.

    Args:
        data: Исходный датафрейм.

    Returns:
        Проверенный датафрейм с преобразованными типами данных.

    Raises:
        DataValidationError: Если данные не соответствуют требованиям.
    """
    if data.empty:
        raise ValidationError("Датасет пустой")
    validate_data = data.copy()
    duplicated_columns = validate_data.columns[validate_data.columns.duplicated()].tolist()
    if duplicated_columns:
        raise ValidationError("Датасет содержит повторяющиеся столбцы: " + ", ".join(duplicated_columns))
    missing_columns = []
    for col in REQUIRED_COLUMNS:
        if col not in validate_data.columns:
            missing_columns.append(col)
    if missing_columns:
        raise ValidationError("Отсутствуют обязательные столбцы: " + ", ".join(missing_columns))
    required_data = validate_data[list(REQUIRED_COLUMNS)]
    columns_missing_values = []
    for col in REQUIRED_COLUMNS:
        if required_data[col].isnull().any():
            columns_missing_values.append(col)

    if columns_missing_values:
        raise ValidationError("Обнаружены пустые значения в столбцах: " + ", ".join(columns_missing_values))

    validate_data["group"] = validate_data["group"].astype(str).str.strip().str.lower()
    validate_data["landing_page"] = validate_data["landing_page"].astype(str).str.strip().str.lower()

    invalid_groups = sorted(set(validate_data["group"]) - set(ALLOWED_GROUPS))
    if invalid_groups:
        raise ValidationError("Недопустимые значения в столбце group: " + ", ".join(invalid_groups))

    invalid_pages = sorted(set(validate_data["landing_page"]) - set(ALLOWED_PAGES))
    if invalid_pages:
        raise ValidationError("Недопустимые значения в столбце landing_page: " + ", ".join(invalid_pages))
    converted_values = pd.to_numeric(validate_data["converted"], errors="coerce")
    if converted_values.isna().any():
        raise ValidationError("Столбец converted должен содержать только числовые значения 0 и 1")
    if not converted_values.isin([0, 1]).all():
        invalid_values = sorted(converted_values[~converted_values.isin([0, 1])].unique())
        raise ValidationError("Столбец converted содержит недопустимые значения: " + ", ".join(map(str, invalid_values)))

    validate_data["converted"] = converted_values.astype("int8")

    parsed_timestamp = pd.to_datetime(validate_data["timestamp"], errors="coerce")
    if parsed_timestamp.isna().any():
        invalid_count = int(parsed_timestamp.isna().sum())
        raise ValidationError(f"Не удалось преобразовать timestamp в дату. Количество недопустимых значений: {invalid_count}")
    validate_data["timestamp"] = parsed_timestamp

    return validate_data
