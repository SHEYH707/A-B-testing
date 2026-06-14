"""Графический интерфейс приложения для анализа A/B-тестов."""

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
from src.data_load import load_csv, LoadError
from src.validator import validate_dataframe, ValidationError
from src.analyzer import AnalysisError, calculate_statistics, prepare_data
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from src.visualizer import VisualizationError, figures
from src.report import ReportError, save_report_files

ROW_LIMIT = 500


class ABapp:
    """Главное окно приложения для анализа A/B-тестов."""
    
    def __init__(self):
        """Инициализировать главное окно приложения."""
        self.root = tk.Tk()
        self.root.title("A/B-тестирование для показателей кликабельности (CTR)")
        self.root.geometry("1100x700")
        self.root.minsize(850, 550)
        self.data: pd.DataFrame | None = None
        self.file_path: Path | None = None
        self.cleaned_data: pd.DataFrame | None = None
        self.summary_data: pd.DataFrame | None = None
        self.daily_data: pd.DataFrame | None = None
        self.graphs_window: tk.Toplevel | None = None
        self.graph_canvases = []
        self.graph_figures = []
        self.cleaning_info: dict[str, int] | None = None
        self.comparison: dict[str, float | bool | str] | None = None
        self.create_widgets()

    def create_widgets(self):
        """Создать элементы главного окна."""
        main_frame = ttk.LabelFrame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        title_label = ttk.Label(main_frame, text="A/B-тестирование для показателей кликабельности (CTR)", font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 20))

        description_label = ttk.Label(
            main_frame, text="Загрузите датасет эксперимента, чтобы рассчитать CTR, сравнить варианты и построить графики.", font=("Arial", 11)
        )
        description_label.pack(pady=(0, 20))

        buttons_frame = ttk.LabelFrame(main_frame)
        buttons_frame.pack(pady=(0, 10))
        self.load_button = ttk.Button(buttons_frame, text="Загрузить датасет", command=self.load_data)
        self.load_button.grid(row=0, column=0, padx=5)

        self.analysis_button = ttk.Button(buttons_frame, text="Выполнить анализ", command=self.run_analysis, state=tk.DISABLED)
        self.analysis_button.grid(row=0, column=1, padx=5)

        self.graphs_button = ttk.Button(buttons_frame, text="Построить графики", command=self.show_graphs, state=tk.DISABLED)
        self.graphs_button.grid(row=0, column=2, padx=5)

        self.report_button = ttk.Button(buttons_frame, text="Сформировать отчет", command=self.create_report, state=tk.DISABLED)
        self.report_button.grid(row=0, column=3, padx=5)

        self.file_label = ttk.Label(main_frame, text="Файл не выбран", font=("Arial", 9))
        self.file_label.pack(pady=(5, 5))

        self.status_label = ttk.Label(main_frame, text="Статус: ожидание загрузки данных...", font=("Arial", 10))
        self.status_label.pack(pady=(0, 10))

        table_frame = ttk.LabelFrame(main_frame, text="Предпросмотр данных", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True)

        self.data_table = ttk.Treeview(table_frame, show="headings")

        vertical_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.data_table.yview)

        horizontal_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.data_table.xview)

        self.data_table.configure(yscrollcommand=vertical_scrollbar.set, xscrollcommand=horizontal_scrollbar.set)
        self.data_table.grid(row=0, column=0, sticky="nsew")
        vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

    def load_data(self) -> None:
        """Загрузить и проверить выбранный CSV-файл."""
        initial_dir = Path.cwd()
        selected_file = filedialog.askopenfilename(
            title="Выберите датасет A/B-эксперимента", initialdir=initial_dir, filetypes=(("CSV-файлы", "*.csv"), ("Все файлы", "*.*"))
        )

        if not selected_file:
            return

        self.disable_result_buttons()
        self.status_label.config(text="Статус: загрузка и проверка данных...")
        self.root.update_idletasks()

        try:
            loaded_data = load_csv(selected_file)
            validated_data = validate_dataframe(loaded_data)
        except (LoadError, ValidationError) as error:
            self.data = None
            self.file_path = None
            self.file_label.config(text="Файл не выбран")
            self.status_label.config(text="Статус: ошибка загрузки данных")
            messagebox.showerror("Ошибка загрузки данных", str(error))
            return

        self.data = validated_data
        self.file_path = Path(selected_file)
        self.cleaned_data = None
        self.summary_data = None
        self.daily_data = None
        self.cleaning_info = None
        self.comparison = None
        if self.graphs_window is not None and self.graphs_window.winfo_exists():
            self.close_graphs_window()
        self.display_data(validated_data)
        self.analysis_button.config(text="Выполнить анализ", state=tk.NORMAL)

        displayed_rows = min(len(self.data), ROW_LIMIT)

        self.file_label.config(text=f"Файл: {self.file_path.name} (отображено {displayed_rows} из {len(self.data)} строк)")
        self.status_label.config(
            text=(f"Статус: загружено {len(self.data)} строк данных В таблице отображено {displayed_rows} строк").replace(",", ".")
        )

    def display_data(self, data: pd.DataFrame) -> None:
        """Отобразить первые строки датасета в таблице."""
        current_rows = self.data_table.get_children()
        if current_rows:
            self.data_table.delete(*current_rows)

        columns = list(data.columns)
        self.data_table["columns"] = columns

        for column in columns:
            self.data_table.heading(
                column,
                text=column,
            )
            self.data_table.column(
                column,
                width=self.get_column_width(column),
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
                formated_values.append(self.format_table_value(value))

            self.data_table.insert("", tk.END, values=formated_values)

    @staticmethod
    def get_column_width(column: str) -> int:
        """Вернуть ширину столбца таблицы."""
        column_widths = {"user_id": 100, "timestamp": 180, "group": 110, "landing_page": 130, "converted": 100}
        return column_widths.get(column, 130)

    @staticmethod
    def format_table_value(value: object) -> str:
        """Преобразовать значение для отображения в таблице."""
        if isinstance(value, pd.Timestamp):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)

    def disable_result_buttons(self) -> None:
        """Отключить кнопки анализа, графиков и отчёта."""
        self.analysis_button.config(state=tk.DISABLED)
        self.graphs_button.config(state=tk.DISABLED)
        self.report_button.config(state=tk.DISABLED)

    def run_analysis(self) -> None:
        """Очистить данные и рассчитать показатели CTR."""
        if self.data is None:
            messagebox.showwarning("Нет данных", "Сначала загрузите CSV-файл.")
            return
        if self.summary_data is not None and self.cleaning_info is not None and self.comparison is not None:
            self.show_analysis_window()
            return
        self.status_label.config(text="Статус: выполняется анализ данных...")
        self.root.update_idletasks()

        try:
            self.cleaned_data, self.cleaning_info = prepare_data(self.data)
            (self.summary_data, self.daily_data, self.comparison) = calculate_statistics(self.cleaned_data)
        except AnalysisError as error:
            self.status_label.config(text="Статус: ошибка анализа данных")
            messagebox.showerror("Ошибка анализа данных", str(error))
            return
        self.show_analysis_window()
        self.analysis_button.config(text="Открыть результаты", state=tk.NORMAL)
        self.graphs_button.config(state=tk.NORMAL)
        self.report_button.config(state=tk.NORMAL)
        self.status_label.config(text="Статус: анализ данных завершен. Графики и отчет доступны.")

    def show_graphs(self) -> None:
        """Открыть окно с графиками результатов анализа."""
        if self.summary_data is None or self.daily_data is None:
            messagebox.showwarning(
                "Нет результатов",
                "Сначала выполните анализ данных.",
            )
            return

        if self.graphs_window is not None and self.graphs_window.winfo_exists():
            self.graphs_window.lift()
            self.graphs_window.focus_force()
            return

        try:
            figuree = figures(self.summary_data, self.daily_data)
        except VisualizationError as error:
            messagebox.showerror("Ошибка построения графиков", str(error))
            return

        self.graphs_window = tk.Toplevel(self.root)

        self.graphs_window.title("Графические результаты A/B-эксперимента")
        self.graphs_window.geometry("950x700")
        self.graphs_window.minsize(750, 550)

        main_frame = ttk.Frame(self.graphs_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = ttk.Label(main_frame, text="Графический отчёт", font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 10))

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.graph_canvases = []
        self.graph_figures = list(figuree.values())

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

            self.graph_canvases.append(canvas)

        self.graphs_window.protocol("WM_DELETE_WINDOW", self.close_graphs_window)

    def show_analysis_window(self) -> None:
        """Открыть окно со статистическими результатами."""
        if self.summary_data is None or self.cleaning_info is None or self.comparison is None:
            return

        analysis_window = tk.Toplevel(self.root)

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

        loaded_rows = self.cleaning_info["loaded_rows"]
        inconsistent_rows = self.cleaning_info["inconsistent_rows"]
        duplicated_users = self.cleaning_info["duplicated_users"]
        cleaned_rows = self.cleaning_info["cleaned_rows"]

        report_text.insert(
            tk.END,
            "ОЧИСТКА ДАННЫХ\n"
            "----------------------------------------\n"
            f"Загружено строк: {loaded_rows:,}\n"
            f"Удалено несогласованных записей: "
            f"{inconsistent_rows:,}\n"
            f"Удалено повторных пользователей: "
            f"{duplicated_users:,}\n"
            f"Осталось строк: {cleaned_rows:,}\n\n",
        )

        for row in self.summary_data.itertuples(index=False):
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
                f"{row.max_ctr:.4f}%\n\n",
            )

        report_text.insert(
            tk.END,
            "СРАВНЕНИЕ ВАРИАНТОВ\n"
            "----------------------------------------\n"
            f"CTR варианта A: "
            f"{self.comparison['control_ctr']:.4f}%\n"
            f"CTR варианта B: "
            f"{self.comparison['treatment_ctr']:.4f}%\n"
            f"Абсолютная разница: "
            f"{self.comparison['absolute_difference']:+.4f} п.п.\n"
            f"Относительное изменение: "
            f"{self.comparison['relative_difference']:+.4f}%\n\n"
            f"{self.comparison['winner']}\n",
        )
        report_text.insert(
            tk.END,
            "\nСТАТИСТИЧЕСКАЯ ПРОВЕРКА\n"
            "----------------------------------------\n"
            "H₀: CTR вариантов A и B одинаков.\n"
            "H₁: CTR вариантов A и B различается.\n"
            f"Уровень значимости: {self.comparison['alpha']:.2f}\n"
            f"Z-статистика: {self.comparison['z_score']:.4f}\n"
            f"P-value: {self.comparison['p_value']:.6f}\n"
            "95%-й доверительный интервал разницы: "
            f"[{self.comparison['confidence_interval_lower']:+.4f}; "
            f"{self.comparison['confidence_interval_upper']:+.4f}] п.п.\n\n"
            f"{self.comparison['hypothesis_conclusion']}\n"
            f"{self.comparison['statistical_conclusion']}\n",
        )

        report_text.config(state=tk.DISABLED)

    def create_report(self) -> None:
        """Сформировать и сохранить итоговые файлы."""
        if self.cleaned_data is None or self.summary_data is None or self.daily_data is None or self.cleaning_info is None or self.comparison is None:
            messagebox.showwarning("Нет результатов", "Сначала выполните анализ данных.")
            return

        self.status_label.config(text="Статус: формирование отчёта...")
        self.root.update_idletasks()

        try:
            report_directory = save_report_files(
                self.cleaned_data,
                self.summary_data,
                self.daily_data,
                self.cleaning_info,
                self.comparison,
                Path.cwd() / "output",
            )

        except ReportError as error:
            self.status_label.config(text="Статус: ошибка формирования отчёта")

            messagebox.showerror("Ошибка формирования отчёта", str(error))
            return

        self.status_label.config(text=(f"Статус: отчёт успешно сформирован в папке {report_directory.name}"))

        messagebox.showinfo(
            "Отчёт сформирован",
            (f"Итоговые файлы успешно сохранены.\n\nПапка:\n{report_directory.resolve()}"),
        )

    def close_graphs_window(self) -> None:
        """Закрыть окно графиков и освободить память."""
        for figure in self.graph_figures:
            plt.close(figure)

        self.graph_canvases.clear()
        self.graph_figures.clear()
        if self.graphs_window is not None and self.graphs_window.winfo_exists():
            self.graphs_window.destroy()

        self.graphs_window = None

    def run(self):
        """Запуск главного цикла."""
        self.root.mainloop()
