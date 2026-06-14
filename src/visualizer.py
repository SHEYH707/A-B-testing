"""Построение графиков для результатов A/B-эксперимента."""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure


class VisualizationError(ValueError):
    """Ошибка при построении графиков."""


def figures(summary_data: pd.DataFrame, daily_data: pd.DataFrame) -> dict[str, Figure]:
    """
    Построить графики по результатам A/B-эксперимента.

    Args:
        summary_data: Общая статистика вариантов.
        daily_data: Дневные показатели вариантов.

    Returns:
        Словарь с названиями и объектами графиков.

    Raises:
        VisualizationError: Если данные для графиков отсутствуют.
    """
    if summary_data.empty:
        raise VisualizationError("Отсутствуют общие результаты анализа.")

    if daily_data.empty:
        raise VisualizationError("Отсутствуют дневные результаты анализа.")

    figures = {
        "Сравнение CTR": bar_chart(summary_data),
        "Распределение CTR": histogram(daily_data),
        "CTR по датам": scatter_plot(daily_data),
        "Boxplot": boxplot(daily_data),
    }

    return figures


def bar_chart(
    summary_data: pd.DataFrame,
) -> Figure:
    """
    Построить столбчатую диаграмму общего CTR.

    Args:
        summary_data: Общая статистика вариантов.

    Returns:
        Объект графика.
    """
    chart_data = summary_data.sort_values("variant")

    figure, axes = plt.subplots(
        figsize=(8, 5),
        constrained_layout=True,
    )

    bars = axes.bar(
        chart_data["variant"],
        chart_data["ctr"],
    )

    axes.bar_label(
        bars,
        labels=[f"{value:.4f}%" for value in chart_data["ctr"]],
        padding=4,
    )

    axes.set_title("Сравнение общего CTR вариантов A и B")
    axes.set_xlabel("Вариант")
    axes.set_ylabel("CTR, %")
    axes.grid(axis="y", alpha=0.3)

    maximum_ctr = float(chart_data["ctr"].max())

    axes.set_ylim(
        0,
        maximum_ctr * 1.2 if maximum_ctr > 0 else 1,
    )

    return figure


def histogram(daily_data: pd.DataFrame) -> Figure:
    """
    Построить гистограмму распределения дневного CTR.

    Args:
        daily_data: Дневные показатели вариантов.

    Returns:
        Объект графика.
    """
    figure, axes = plt.subplots(
        figsize=(8, 5),
        constrained_layout=True,
    )

    group_names = {
        "control": "Вариант A",
        "treatment": "Вариант B",
    }

    for group, label in group_names.items():
        group_values = daily_data.loc[
            daily_data["group"] == group,
            "ctr",
        ]

        if group_values.empty:
            continue

        bins_count = min(
            10,
            max(1, len(group_values)),
        )

        axes.hist(
            group_values,
            bins=bins_count,
            alpha=0.6,
            label=label,
        )

    axes.set_title("Распределение дневного CTR")
    axes.set_xlabel("Дневной CTR, %")
    axes.set_ylabel("Количество наблюдений")
    axes.legend()
    axes.grid(axis="y", alpha=0.3)

    return figure


def scatter_plot(daily_data: pd.DataFrame) -> Figure:
    """
    Построить диаграмму рассеяния CTR по датам.

    Args:
        daily_data: Дневные показатели вариантов.

    Returns:
        Объект графика.
    """
    figure, axes = plt.subplots(
        figsize=(9, 5),
        constrained_layout=True,
    )

    group_names = {
        "control": "Вариант A",
        "treatment": "Вариант B",
    }

    for group, label in group_names.items():
        group_data = daily_data.loc[daily_data["group"] == group].sort_values("date")

        if group_data.empty:
            continue

        axes.scatter(
            group_data["date"],
            group_data["ctr"],
            label=label,
            alpha=0.8,
        )
    unique_dates = pd.to_datetime(daily_data["date"].dropna().unique())

    if len(unique_dates) == 1:
        only_date = pd.Timestamp(unique_dates[0])

        axes.set_xlim(
            only_date - pd.Timedelta(days=1),
            only_date + pd.Timedelta(days=1),
        )

    axes.set_title("Дневной CTR по датам")
    axes.set_xlabel("Дата")
    axes.set_ylabel("CTR, %")
    axes.legend()
    axes.grid(alpha=0.3)

    date_locator = mdates.AutoDateLocator()
    date_formatter = mdates.ConciseDateFormatter(date_locator)

    axes.xaxis.set_major_locator(date_locator)
    axes.xaxis.set_major_formatter(date_formatter)

    return figure


def boxplot(
    daily_data: pd.DataFrame,
) -> Figure:
    """
    Построить boxplot дневного CTR.

    Args:
        daily_data: Дневные показатели вариантов.

    Returns:
        Объект графика.

    Raises:
        VisualizationError: Если отсутствует одна из групп.
    """
    control_values = daily_data.loc[
        daily_data["group"] == "control",
        "ctr",
    ].to_numpy()

    treatment_values = daily_data.loc[
        daily_data["group"] == "treatment",
        "ctr",
    ].to_numpy()

    if len(control_values) == 0:
        raise VisualizationError("Отсутствуют дневные данные варианта A.")

    if len(treatment_values) == 0:
        raise VisualizationError("Отсутствуют дневные данные варианта B.")

    figure, axes = plt.subplots(
        figsize=(8, 5),
        constrained_layout=True,
    )

    axes.boxplot(
        [
            control_values,
            treatment_values,
        ],
        showmeans=True,
    )

    axes.set_xticks(
        [1, 2],
        ["Вариант A", "Вариант B"],
    )

    axes.set_title("Распределение дневного CTR")
    axes.set_xlabel("Вариант")
    axes.set_ylabel("CTR, %")
    axes.grid(axis="y", alpha=0.3)

    return figure
