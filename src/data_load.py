"""Загрузка экспериментальных данных из CSV-файлов."""

from pathlib import Path
import pandas as pd


class LoadError(Exception):
    """Ошибка при загрузке файла с данными."""


def load_csv(file_path: str | Path) -> pd.DataFrame:
    """Загрузить данные A/B-эксперимента из CSV-файла."""
    path = Path(file_path)

    if not path.exists():
        raise LoadError(f"Файл не найден: {file_path}")
    if not path.is_file():
        raise LoadError(f"Указанный путь не является файлом: {file_path}")
    if path.suffix.lower() != ".csv":
        raise LoadError("Необходимо выбрать файл формата .csv")
    try:
        data = pd.read_csv(path)
    except pd.errors.EmptyDataError as error:
        raise LoadError("CSV-файл пуст") from error
    except pd.errors.ParserError as error:
        raise LoadError(f"Ошибка при чтении CSV-файла: {error}") from error
    except UnicodeDecodeError as error:
        raise LoadError(f"Не удалось определить кодировку csv-файла: {error}") from error
    except OSError as error:
        raise LoadError(f"Ошибка при чтении файла: {error}") from error
    return data
