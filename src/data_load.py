"""Загрузка экспериментальных данных из CSV-файлов."""

from pathlib import Path
import pandas as pd


def load_csv(file_path: str | Path) -> pd.DataFrame:
    """Загрузить данные A/B-эксперимента из CSV-файла."""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"Файл не найден: {file_path}")
    if not path.is_file():
        raise ValueError(f"Указанный путь не является файлом: {file_path}")
    if path.suffix.lower() != ".csv":
        raise ValueError("Необходимо выбрать файл формата .csv")

    try:
        data = pd.read_csv(path)
    except pd.errors.EmptyDataError as error:
        raise ValueError("CSV-файл пуст") from error
    except pd.errors.ParserError as error:
        raise ValueError(f"Ошибка при чтении CSV-файла: {error}") from error
    except UnicodeDecodeError as error:
        raise ValueError(f"Не удалось определить кодировку CSV-файла: {error}") from error
    except OSError as error:
        raise ValueError(f"Ошибка при чтении файла: {error}") from error

    return data
