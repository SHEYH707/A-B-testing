"""Очистка и статистический анализ данных A/B-эксперимента."""

import pandas as pd
from math import erfc, sqrt
from statistics import NormalDist


class AnalysisError(ValueError):
    """Ошибка при анализе данных."""


def calculate_significance(
    control_clicks: int, control_impressions: int, treatment_clicks: int, treatment_impressions: int, alpha: float = 0.05
) -> dict[str, float | bool | str]:
    """Выполнить z-тест для сравнения двух долей."""
    if control_impressions <= 0 or treatment_impressions <= 0:
        raise AnalysisError("Количество показов в обеих группах должно быть больше нуля")

    control_rate = control_clicks / control_impressions
    treatment_rate = treatment_clicks / treatment_impressions
    difference = treatment_rate - control_rate

    pooled_rate = (control_clicks + treatment_clicks) / (control_impressions + treatment_impressions)
    pooled_standard_error = sqrt(pooled_rate * (1 - pooled_rate) * (1 / control_impressions + 1 / treatment_impressions))
    if pooled_standard_error == 0:
        z_score = 0.0
        p_value = 1.0
    else:
        z_score = difference / pooled_standard_error
        p_value = erfc(abs(z_score) / sqrt(2))

    confidence_standard_error = sqrt(
        control_rate * (1 - control_rate) / control_impressions + treatment_rate * (1 - treatment_rate) / treatment_impressions
    )

    critical_value = NormalDist().inv_cdf(1 - alpha / 2)
    confidence_interval_lower = (difference - critical_value * confidence_standard_error) * 100
    confidence_interval_upper = (difference + critical_value * confidence_standard_error) * 100
    significant = p_value < alpha

    if significant:
        hypothesis_conclusion = "Нулевая гипотеза отклоняется. Различие между вариантами статистически значимо."
    else:
        hypothesis_conclusion = "Нет оснований отклонять нулевую гипотезу. Статистически значимое различие не обнаружено."

    if not significant:
        statistical_conclusion = "Статистически значимого преимущества ни одного варианта не обнаружено."
    elif treatment_rate > control_rate:
        statistical_conclusion = "Вариант B статистически значимо превосходит вариант A."
    elif treatment_rate < control_rate:
        statistical_conclusion = "Вариант A статистически значимо превосходит вариант B."
    else:
        statistical_conclusion = "Показатели вариантов статистически не различаются."

    return {
        "alpha": alpha,
        "z_score": z_score,
        "p_value": p_value,
        "significant": significant,
        "confidence_interval_lower": confidence_interval_lower,
        "confidence_interval_upper": confidence_interval_upper,
        "hypothesis_conclusion": hypothesis_conclusion,
        "statistical_conclusion": statistical_conclusion,
    }


def prepare_data(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Очистить данные A/B-эксперимента.

    Удаляются записи, в которых группа не соответствует
    показанной странице, а также повторные пользователи.

    Args:
        data: Проверенный датафрейм.

    Returns:
        Кортеж из очищенного датафрейма и информации об очистке.

    Raises:
        AnalysisError: Если после очистки данные отсутствуют.
    """
    cleaned_data = data.copy()

    loaded_rows = len(cleaned_data)

    consistent_rows = ((cleaned_data["group"] == "control") & (cleaned_data["landing_page"] == "old_page")) | (
        (cleaned_data["group"] == "treatment") & (cleaned_data["landing_page"] == "new_page")
    )

    inconsistent_rows = int((~consistent_rows).sum())

    cleaned_data = cleaned_data.loc[consistent_rows].copy()

    duplicated_users = int(
        cleaned_data.duplicated(
            subset="user_id",
            keep="first",
        ).sum()
    )

    cleaned_data = cleaned_data.drop_duplicates(
        subset="user_id",
        keep="first",
    ).copy()

    cleaned_data = cleaned_data.reset_index(drop=True)

    if cleaned_data.empty:
        raise AnalysisError("После очистки в датасете не осталось записей.")

    cleaning_info = {
        "loaded_rows": loaded_rows,
        "inconsistent_rows": inconsistent_rows,
        "duplicated_users": duplicated_users,
        "cleaned_rows": len(cleaned_data),
    }

    return cleaned_data, cleaning_info


def calculate_statistics(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float | str]]:
    """
    Рассчитать CTR и описательные статистики.

    Args:
        data: Очищенный датафрейм.

    Returns:
        Сводная таблица, дневные показатели и результаты сравнения.

    Raises:
        AnalysisError: Если отсутствует одна из групп эксперимента.
    """
    available_groups = set(data["group"].unique())
    required_groups = {"control", "treatment"}

    missing_groups = required_groups - available_groups

    if missing_groups:
        raise AnalysisError("После очистки отсутствуют группы: " + ", ".join(sorted(missing_groups)))

    analysis_data = data.copy()

    analysis_data["date"] = analysis_data["timestamp"].dt.normalize()

    daily_data = analysis_data.groupby(
        ["date", "group"],
        as_index=False,
    ).agg(
        impressions=("user_id", "size"),
        clicks=("converted", "sum"),
    )

    daily_data["ctr"] = daily_data["clicks"] / daily_data["impressions"] * 100

    total_data = analysis_data.groupby(
        "group",
        as_index=False,
    ).agg(
        impressions=("user_id", "size"),
        clicks=("converted", "sum"),
    )

    total_data["ctr"] = total_data["clicks"] / total_data["impressions"] * 100

    descriptive_data = daily_data.groupby("group", as_index=False).agg(
        mean_ctr=("ctr", "mean"),
        std_ctr=("ctr", "std"),
        min_ctr=("ctr", "min"),
        max_ctr=("ctr", "max"),
    )

    descriptive_data["std_ctr"] = descriptive_data["std_ctr"].fillna(0.0)

    summary_data = total_data.merge(
        descriptive_data,
        on="group",
        how="left",
    )

    summary_data["variant"] = summary_data["group"].map(
        {
            "control": "A",
            "treatment": "B",
        }
    )

    summary_data = summary_data[
        [
            "variant",
            "group",
            "impressions",
            "clicks",
            "ctr",
            "mean_ctr",
            "std_ctr",
            "min_ctr",
            "max_ctr",
        ]
    ]

    control_row = summary_data.loc[summary_data["group"] == "control"].iloc[0]

    treatment_row = summary_data.loc[summary_data["group"] == "treatment"].iloc[0]

    control_ctr = float(control_row["ctr"])
    treatment_ctr = float(treatment_row["ctr"])

    absolute_difference = treatment_ctr - control_ctr

    if control_ctr == 0:
        relative_difference = 0.0
    else:
        relative_difference = absolute_difference / control_ctr * 100

    if treatment_ctr > control_ctr:
        winner = "Вариант B показывает более высокий CTR."
    elif treatment_ctr < control_ctr:
        winner = "Вариант A показывает более высокий CTR."
    else:
        winner = "CTR вариантов A и B одинаков."

    comparison = {
        "control_ctr": control_ctr,
        "treatment_ctr": treatment_ctr,
        "absolute_difference": absolute_difference,
        "relative_difference": relative_difference,
        "winner": winner,
    }

    significance = calculate_significance(
        int(control_row["clicks"]),
        int(control_row["impressions"]),
        int(treatment_row["clicks"]),
        int(treatment_row["impressions"]),
    )

    comparison.update(significance)

    return summary_data, daily_data, comparison
