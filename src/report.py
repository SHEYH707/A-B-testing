"""Формирование и сохранение отчётов A/B-эксперимента."""

from datetime import datetime
from pathlib import Path
import shutil
import matplotlib.pyplot as plt
import pandas as pd
from src.visualizer import figures


def build_report(summary_data: pd.DataFrame, cleaning_info: dict[str, int], comparison: dict[str, float | bool | str]) -> str:
    """Сформировать текстовый отчёт по результатам A/B-эксперимента."""
    report_lines = [
        "ОТЧЁТ ПО РЕЗУЛЬТАТАМ A/B-ЭКСПЕРИМЕНТА",
        "=" * 55,
        "",
        f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}",
        "",
        "ОПИСАНИЕ",
        "-" * 55,
        "В рамках анализа значение converted = 1 интерпретируется как совершение пользователем целевого действия.",
        "CTR рассчитывается как отношение количества целевых действий к количеству показов, умноженное на 100%.",
        "",
        "ОЧИСТКА ДАННЫХ",
        "-" * 55,
        f"Загружено строк: {cleaning_info['loaded_rows']:,}",
        f"Удалено несогласованных записей: {cleaning_info['inconsistent_rows']:,}",
        f"Удалено повторных пользователей: {cleaning_info['duplicated_users']:,}",
        f"Осталось строк: {cleaning_info['cleaned_rows']:,}",
        ""
    ]

    for row in summary_data.itertuples(index=False):
        report_lines.extend(
            [
                f"ВАРИАНТ {row.variant} ({row.group})",
                "-" * 55,
                f"Количество показов: {row.impressions:,}",
                f"Количество целевых действий: {row.clicks:,}",
                f"Общий CTR: {row.ctr:.4f}%",
                f"Средний дневной CTR: {row.mean_ctr:.4f}%",
                f"Стандартное отклонение: {row.std_ctr:.4f}",
                f"Минимальный дневной CTR: {row.min_ctr:.4f}%",
                f"Максимальный дневной CTR: {row.max_ctr:.4f}%",
                ""
            ]
        )

    report_lines.extend(
        [
            "СРАВНЕНИЕ ВАРИАНТОВ",
            "-" * 55,
            f"CTR варианта A: {comparison['control_ctr']:.4f}%",
            f"CTR варианта B: {comparison['treatment_ctr']:.4f}%",
            f"Абсолютная разница: {comparison['absolute_difference']:+.4f} п.п.",
            f"Относительное изменение: {comparison['relative_difference']:+.4f}%",
            "",
            str(comparison["winner"]),
            "",
            "СТАТИСТИЧЕСКАЯ ПРОВЕРКА",
            "-" * 55,
            "H0: CTR вариантов A и B одинаков.",
            "H1: CTR вариантов A и B различается.",
            f"Уровень значимости: {comparison['alpha']:.2f}",
            f"Z-статистика: {comparison['z_score']:.4f}",
            f"P-value: {comparison['p_value']:.6f}",
            (
                "95%-й доверительный интервал разницы: "
                f"[{comparison['confidence_interval_lower']:+.4f}; "
                f"{comparison['confidence_interval_upper']:+.4f}] п.п."
            ),
            "",
            str(comparison["hypothesis_conclusion"]),
            str(comparison["statistical_conclusion"]),
            "",
            "=" * 55
        ]
    )

    return "\n".join(report_lines)


def save_report_files(cleaned_data: pd.DataFrame, summary_data: pd.DataFrame, daily_data: pd.DataFrame, cleaning_info: dict[str, int], comparison: dict[str, float | bool | str], output_dir: str | Path) -> Path:  # noqa: E501
    """
    Сохранить текстовый отчёт, таблицы и графики.

    Raises:
        RuntimeError: Если итоговые файлы не удалось сформировать.
    """
    output_path = Path(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_directory = output_path / f"report_{timestamp}"
    figuree = {}

    try:
        report_directory.mkdir(parents=True, exist_ok=False)

        report_text = build_report(summary_data, cleaning_info, comparison)
        report_file = report_directory / "analysis_report.txt"
        report_file.write_text(report_text, encoding="utf-8-sig")

        cleaned_data.to_csv(report_directory / "cleaned_data.csv", index=False, encoding="utf-8-sig")
        summary_data.to_csv(report_directory / "summary.csv", index=False, encoding="utf-8-sig")
        daily_data.to_csv(report_directory / "daily_metrics.csv", index=False, encoding="utf-8-sig")

        figuree = figures(summary_data, daily_data)

        figure_names = {
            "Сравнение CTR": "ctr_comparison.png",
            "Распределение CTR": "ctr_distribution.png",
            "CTR по датам": "ctr_by_date.png",
            "Boxplot": "ctr_boxplot.png"
        }

        for figure_title, figure in figuree.items():
            file_name = figure_names[figure_title]
            figure.savefig(report_directory / file_name, dpi=150, bbox_inches="tight")

    except (OSError, ValueError, KeyError) as error:
        if report_directory.exists():
            shutil.rmtree(report_directory, ignore_errors=True)

        raise RuntimeError(f"Не удалось сформировать отчёт: {error}") from error

    finally:
        for figure in figuree.values():
            plt.close(figure)

    return report_directory
