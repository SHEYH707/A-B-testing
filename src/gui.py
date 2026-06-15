"""Графический интерфейс приложения для анализа A/B-тестов."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from src.data_load import load_csv
from src.validator import validate_dataframe
from src.analyzer import calculate_statistics, prepare_data
from src.visualizer import figures
from src.report import save_report_files

ROW_LIMIT = 500

root = None
data: pd.DataFrame | None = None
file_path: Path | None = None
cleaned_data: pd.DataFrame | None = None
summary_data: pd.DataFrame | None = None
daily_data: pd.DataFrame | None = None
graphs_window: tk.Toplevel | None = None
graph_canvases = []
graph_figures = []
cleaning_info: dict[str, int] | None = None
comparison: dict[str, float | bool | str] | None = None

load_button = None
analysis_button = None
graphs_button = None
report_button = None
file_label = None
status_label = None
data_table = None


def create_widgets():
    """Создать элементы главного окна."""
    global load_button, analysis_button, graphs_button, report_button, file_label, status_label, data_table

    main_frame = ttk.LabelFrame(root, padding=20)
    main_frame.pack(fill=tk.BOTH, expand=True)
    title_label = ttk.Label(main_frame, text="A/B-тестирование для показателей кликабельности (CTR)", font=("Arial", 18, "bold"))
    title_label.pack(pady=(0, 20))

    description_label = ttk.Label(
        main_frame, text="Загрузите датасет эксперимента, чтобы рассчитать CTR, сравнить варианты и построить графики.", font=("Arial", 11)
    )
    description_label.pack(pady=(0, 20))

    buttons_frame = ttk.LabelFrame(main_frame)
    buttons_frame.pack(pady=(0, 10))
    load_button = ttk.Button(buttons_frame, text="Загрузить датасет", command=load_data)
    load_button.grid(row=0, column=0, padx=5)

    analysis_button = ttk.Button(buttons_frame, text="Выполнить анализ", command=run_analysis, state=tk.DISABLED)
    analysis_button.grid(row=0, column=1, padx=5)

    graphs_button = ttk.Button(buttons_frame, text="Построить графики", command=show_graphs, state=tk.DISABLED)
    graphs_button.grid(row=0, column=2, padx=5)

    report_button = ttk.Button(buttons_frame, text="Сформировать отчет", command=create_report, state=tk.DISABLED)
    report_button.grid(row=0, column=3, padx=5)

    file_label = ttk.Label(main_frame, text="Файл не выбран", font=("Arial", 9))
    file_label.pack(pady=(5, 5))

    status_label = ttk.Label(main_frame, text="Статус: ожидание загрузки данных...", font=("Arial", 10))
    status_label.pack(pady=(0, 10))

    table_frame = ttk.LabelFrame(main_frame, text="Предпросмотр данных", padding=5)
    table_frame.pack(fill=tk.BOTH, expand=True)

    data_table = ttk.Treeview(table_frame, show="headings")

    vertical_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=data_table.yview)

    horizontal_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=data_table.xview)

    data_table.configure(yscrollcommand=vertical_scrollbar.set, xscrollcommand=horizontal_scrollbar.set)
    data_table.grid(row=0, column=0, sticky="nsew")
    vertical_scrollbar.grid(row=0, column=1, sticky="ns")
    horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)


def load_data() -> None:
    """Загрузить и проверить выбранный CSV-файл."""
    global data, file_path, cleaned_data, summary_data, daily_data, cleaning_info, comparison

    initial_dir = Path.cwd()
    selected_file = filedialog.askopenfilename(
        title="Выберите датасет A/B-эксперимента", initialdir=initial_dir, filetypes=(("CSV-файлы", "*.csv"), ("Все файлы", "*.*"))
    )

    if not selected_file:
        return

    disable_result_buttons()
    status_label.config(text="Статус: загрузка и проверка данных...")
    root.update_idletasks()

    try:
        loaded_data = load_csv(selected_file)
        validated_data = validate_dataframe(loaded_data)
    except ValueError as error:
        data = None
        file_path = None
        file_label.config(text="Файл не выбран")
        status_label.config(text="Статус: ошибка загрузки данных")
        messagebox.showerror("Ошибка загрузки данных", str(error))
        return

    data = validated_data
    file_path = Path(selected_file)
    cleaned_data = None
    summary_data = None
    daily_data = None
    cleaning_info = None
    comparison = None
    if graphs_window is not None and graphs_window.winfo_exists():
        close_graphs_window()
    display_data(validated_data)
    analysis_button.config(text="Выполнить анализ", state=tk.NORMAL)

    displayed_rows = min(len(data), ROW_LIMIT)

    file_label.config(text=f"Файл: {file_path.name} (отображено {displayed_rows} из {len(data)} строк)")
    status_label.config(text=(f"Статус: загружено {len(data)} строк данных В таблице отображено {displayed_rows} строк").replace(",", "."))


def display_data(data: pd.DataFrame) -> None:
    """Отобразить первые строки датасета в таблице."""
    current_rows = data_table.get_children()
    if current_rows:
        data_table.delete(*current_rows)

    columns = list(data.columns)
    data_table["columns"] = columns

    for column in columns:
        data_table.heading(
            column,
            text=column,
        )
        data_table.column(
            column,
            width=get_column_width(column),
            minwidth=80,
            anchor=tk.CENTER,
            stretch=True,
        )

    preview_data = data.head(ROW_LIMIT)

    for row in preview_data.itertuples(
        index=False,
        name=None,
    ):
        formated_values = []
        for value in row:
            formated_values.append(format_table_value(value))

        data_table.insert("", tk.END, values=formated_values)


def get_column_width(column: str) -> int:
    """Вернуть ширину столбца таблицы."""
    column_widths = {"user_id": 100, "timestamp": 180, "group": 110, "landing_page": 130, "converted": 100}
    return column_widths.get(column, 130)


def format_table_value(value: object) -> str:
    """Преобразовать значение для отображения в таблице."""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def disable_result_buttons() -> None:
    """Отключить кнопки анализа, графиков и отчёта."""
    analysis_button.config(state=tk.DISABLED)
    graphs_button.config(state=tk.DISABLED)
    report_button.config(state=tk.DISABLED)


def run_analysis() -> None:
    """Очистить данные и рассчитать показатели CTR."""
    global cleaned_data, summary_data, daily_data, cleaning_info, comparison

    if data is None:
        messagebox.showwarning("Нет данных", "Сначала загрузите CSV-файл.")
        return
    if summary_data is not None and cleaning_info is not None and comparison is not None:
        show_analysis_window()
        return
    status_label.config(text="Статус: выполняется анализ данных...")
    root.update_idletasks()

    try:
        cleaned_data, cleaning_info = prepare_data(data)
        (summary_data, daily_data, comparison) = calculate_statistics(cleaned_data)
    except ValueError as error:
        status_label.config(text="Статус: ошибка анализа данных")
        messagebox.showerror("Ошибка анализа данных", str(error))
        return
    show_analysis_window()
    analysis_button.config(text="Открыть результаты", state=tk.NORMAL)
    graphs_button.config(state=tk.NORMAL)
    report_button.config(state=tk.NORMAL)
    status_label.config(text="Статус: анализ данных завершен. Графики и отчет доступны.")


def show_graphs() -> None:
    """Открыть окно с графиками результатов анализа."""
    global graphs_window, graph_canvases, graph_figures

    if summary_data is None or daily_data is None:
        messagebox.showwarning(
            "Нет результатов",
            "Сначала выполните анализ данных.",
        )
        return

    if graphs_window is not None and graphs_window.winfo_exists():
        graphs_window.lift()
        graphs_window.focus_force()
        return

    try:
        figuree = figures(summary_data, daily_data)
    except ValueError as error:
        messagebox.showerror("Ошибка построения графиков", str(error))
        return

    graphs_window = tk.Toplevel(root)

    graphs_window.title("Графические результаты A/B-эксперимента")
    graphs_window.geometry("950x700")
    graphs_window.minsize(750, 550)

    main_frame = ttk.Frame(graphs_window, padding=10)
    main_frame.pack(fill=tk.BOTH, expand=True)

    title_label = ttk.Label(main_frame, text="Графический отчёт", font=("Arial", 18, "bold"))
    title_label.pack(pady=(0, 10))

    notebook = ttk.Notebook(main_frame)
    notebook.pack(fill=tk.BOTH, expand=True)

    graph_canvases = []
    graph_figures = list(figuree.values())

    for tab_name, figure in figuree.items():
        tab_frame = ttk.Frame(
            notebook,
            padding=5,
        )

        notebook.add(
            tab_frame,
            text=tab_name,
        )

        canvas = FigureCanvasTkAgg(
            figure,
            master=tab_frame,
        )
        canvas.draw()

        toolbar = NavigationToolbar2Tk(
            canvas,
            tab_frame,
            pack_toolbar=False,
        )
        toolbar.update()
        toolbar.pack(
            side=tk.BOTTOM,
            fill=tk.X,
        )

        canvas.get_tk_widget().pack(
            side=tk.TOP,
            fill=tk.BOTH,
            expand=True,
        )

        graph_canvases.append(canvas)

    graphs_window.protocol("WM_DELETE_WINDOW", close_graphs_window)


def show_analysis_window() -> None:
    """Открыть окно со статистическими результатами."""
    if summary_data is None or cleaning_info is None or comparison is None:
        return

    analysis_window = tk.Toplevel(root)

    analysis_window.title("Результаты анализа A/B-эксперимента")
    analysis_window.geometry("850x600")
    analysis_window.minsize(700, 500)

    main_frame = ttk.Frame(
        analysis_window,
        padding=20,
    )
    main_frame.pack(
        fill=tk.BOTH,
        expand=True,
    )

    title_label = ttk.Label(
        main_frame,
        text="Статистический отчёт",
        font=("Arial", 18, "bold"),
    )
    title_label.pack(pady=(0, 15))

    report_text = tk.Text(
        main_frame,
        wrap=tk.WORD,
        font=("Consolas", 11),
        padx=15,
        pady=15,
    )
    report_text.pack(
        fill=tk.BOTH,
        expand=True,
    )

    loaded_rows = cleaning_info["loaded_rows"]
    inconsistent_rows = cleaning_info["inconsistent_rows"]
    duplicated_users = cleaning_info["duplicated_users"]
    cleaned_rows = cleaning_info["cleaned_rows"]

    report_text.insert(
        tk.END,
        "ОЧИСТКА ДАННЫХ\n"
        "----------------------------------------\n"
        f"Загружено строк: {loaded_rows:,}\n"
        f"Удалено несогласованных записей: "
        f"{inconsistent_rows:,}\n"
        f"Удалено повторных пользователей: "
        f"{duplicated_users:,}\n"
        f"Осталось строк: {cleaned_rows:,}\n\n"
    )

    for row in summary_data.itertuples(index=False):
        report_text.insert(
            tk.END,
            f"ВАРИАНТ {row.variant} ({row.group})\n"
            "----------------------------------------\n"
            f"Количество показов: {row.impressions:,}\n"
            f"Количество целевых действий: "
            f"{row.clicks:,}\n"
            f"Общий CTR: {row.ctr:.4f}%\n"
            f"Средний дневной CTR: "
            f"{row.mean_ctr:.4f}%\n"
            f"Стандартное отклонение: "
            f"{row.std_ctr:.4f}\n"
            f"Минимальный дневной CTR: "
            f"{row.min_ctr:.4f}%\n"
            f"Максимальный дневной CTR: "
            f"{row.max_ctr:.4f}%\n\n"
        )

    report_text.insert(
        tk.END,
        "СРАВНЕНИЕ ВАРИАНТОВ\n"
        "----------------------------------------\n"
        f"CTR варианта A: "
        f"{comparison['control_ctr']:.4f}%\n"
        f"CTR варианта B: "
        f"{comparison['treatment_ctr']:.4f}%\n"
        f"Абсолютная разница: "
        f"{comparison['absolute_difference']:+.4f} п.п.\n"
        f"Относительное изменение: "
        f"{comparison['relative_difference']:+.4f}%\n\n"
        f"{comparison['winner']}\n"
    )
    report_text.insert(
        tk.END,
        "\nСТАТИСТИЧЕСКАЯ ПРОВЕРКА\n"
        "----------------------------------------\n"
        "H₀: CTR вариантов A и B одинаков.\n"
        "H₁: CTR вариантов A и B различается.\n"
        f"Уровень значимости: {comparison['alpha']:.2f}\n"
        f"Z-статистика: {comparison['z_score']:.4f}\n"
        f"P-value: {comparison['p_value']:.6f}\n"
        "95%-й доверительный интервал разницы: "
        f"[{comparison['confidence_interval_lower']:+.4f}; "
        f"{comparison['confidence_interval_upper']:+.4f}] п.п.\n\n"
        f"{comparison['hypothesis_conclusion']}\n"
        f"{comparison['statistical_conclusion']}\n"
    )

    report_text.config(state=tk.DISABLED)


def create_report() -> None:
    """Сформировать и сохранить итоговые файлы."""
    if cleaned_data is None or summary_data is None or daily_data is None or cleaning_info is None or comparison is None:
        messagebox.showwarning("Нет результатов", "Сначала выполните анализ данных.")
        return

    status_label.config(text="Статус: формирование отчёта...")
    root.update_idletasks()

    try:
        report_directory = save_report_files(
            cleaned_data,
            summary_data,
            daily_data,
            cleaning_info,
            comparison,
            Path.cwd() / "output"
        )

    except RuntimeError as error:
        status_label.config(text="Статус: ошибка формирования отчёта")

        messagebox.showerror("Ошибка формирования отчёта", str(error))
        return

    status_label.config(text=(f"Статус: отчёт успешно сформирован в папке {report_directory.name}"))

    messagebox.showinfo(
        "Отчёт сформирован",
        (f"Итоговые файлы успешно сохранены.\n\nПапка:\n{report_directory.resolve()}"),
    )


def close_graphs_window() -> None:
    """Закрыть окно графиков и освободить память."""
    global graphs_window

    for figure in graph_figures:
        plt.close(figure)

    graph_canvases.clear()
    graph_figures.clear()
    if graphs_window is not None and graphs_window.winfo_exists():
        graphs_window.destroy()

    graphs_window = None


def run_app() -> None:
    """Запуск главного цикла."""
    global root

    root = tk.Tk()
    root.title("A/B-тестирование для показателей кликабельности (CTR)")
    root.geometry("1100x700")
    root.minsize(850, 550)
    create_widgets()
    root.mainloop()
