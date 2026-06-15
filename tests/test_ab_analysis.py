from pathlib import Path
import pandas as pd
import pytest
from src.analyzer import calculate_significance, calculate_statistics, prepare_data
from src.data_load import load_csv
from src.report import build_report
from src.validator import validate_dataframe


def create_test_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5, 6],
            "timestamp": [
                "2017-01-02 10:00:00",
                "2017-01-02 11:00:00",
                "2017-01-02 12:00:00",
                "2017-01-02 13:00:00",
                "2017-01-02 14:00:00",
                "2017-01-02 15:00:00",
            ],
            "group": ["control", "treatment", "control", "treatment", "control", "treatment"],
            "landing_page": ["old_page", "new_page", "old_page", "new_page", "old_page", "new_page"],
            "converted": [0, 1, 1, 0, 0, 1]
        }
    )


def test_load_csv(tmp_path: Path) -> None:
    file_path = tmp_path / "data.csv"
    create_test_data().to_csv(file_path, index=False)

    data = load_csv(file_path)
    assert len(data) == 6
    assert list(data.columns) == ["user_id", "timestamp", "group", "landing_page", "converted"]


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        load_csv(tmp_path / "missing.csv")


def test_validate_dataframe() -> None:
    data = validate_dataframe(create_test_data())
    assert pd.api.types.is_datetime64_any_dtype(data["timestamp"])
    assert data["converted"].dtype == "int8"


def test_missing_column() -> None:
    data = create_test_data().drop(columns="converted")
    with pytest.raises(ValueError):
        validate_dataframe(data)


def test_invalid_converted() -> None:
    data = create_test_data()
    data.loc[0, "converted"] = 2
    with pytest.raises(ValueError):
        validate_dataframe(data)


def test_prepare_data_removes() -> None:
    data = validate_dataframe(create_test_data())

    invalid_row = data.iloc[[0]].copy()
    invalid_row["group"] = "treatment"
    invalid_row["landing_page"] = "old_page"

    duplicate_row = data.iloc[[1]].copy()
    extended_data = pd.concat([data, invalid_row, duplicate_row], ignore_index=True)
    cleaned_data, cleaning_info = prepare_data(extended_data)
    assert len(cleaned_data) == 6
    assert cleaning_info["loaded_rows"] == 8
    assert cleaning_info["inconsistent_rows"] == 1
    assert cleaning_info["duplicated_users"] == 1
    assert cleaning_info["cleaned_rows"] == 6


def test_calculate_statistics() -> None:
    data = validate_dataframe(create_test_data())
    cleaned_data, _ = prepare_data(data)
    summary_data, daily_data, comparison = calculate_statistics(cleaned_data)

    control = summary_data.loc[summary_data["group"] == "control"].iloc[0]
    treatment = summary_data.loc[summary_data["group"] == "treatment"].iloc[0]

    assert control["impressions"] == 3
    assert control["clicks"] == 1
    assert control["ctr"] == pytest.approx(33.333333)

    assert treatment["impressions"] == 3
    assert treatment["clicks"] == 2
    assert treatment["ctr"] == pytest.approx(66.666667)

    assert len(daily_data) == 2
    assert comparison["p_value"] == pytest.approx(0.414216, abs=0.000001)
    assert comparison["significant"] is False


def test_calculate_significance() -> None:
    result = calculate_significance(1, 3, 2, 3)

    assert result["alpha"] == 0.05
    assert result["z_score"] == pytest.approx(0.816497, abs=0.000001)
    assert result["p_value"] == pytest.approx(0.414216, abs=0.000001)
    assert result["significant"] is False


def test_build_report() -> None:
    data = validate_dataframe(create_test_data())
    cleaned_data, cleaning_info = prepare_data(data)
    summary_data, _, comparison = calculate_statistics(cleaned_data)

    report = build_report(summary_data, cleaning_info, comparison)

    assert "ОТЧЁТ ПО РЕЗУЛЬТАТАМ A/B-ЭКСПЕРИМЕНТА" in report
    assert "Загружено строк: 6" in report
    assert "CTR варианта A: 33.3333%" in report
    assert "P-value: 0.414216" in report
