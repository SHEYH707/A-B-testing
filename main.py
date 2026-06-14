"""Точка входа в приложение анализа A/B-тестов."""

from src.gui import ABapp


def main() -> None:
    """Запустить графическое приложение."""
    app = ABapp()
    app.run()


if __name__ == "__main__":
    main()
