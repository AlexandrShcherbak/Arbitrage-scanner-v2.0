.PHONY: install install-full venv run run-once test clean backup monitor help

install:
	@echo "Установка минимальных зависимостей..."
	pip install -r requirements-minimal.txt

install-full:
	@echo "Установка всех зависимостей..."
	pip install -r requirements.txt

venv:
	@echo "Создание виртуального окружения..."
	python -m venv venv

run:
	@echo "Запуск бота в цикле..."
	python arbitrage_bot.py --config config.bot.json

run-once:
	@echo "Запуск бота (один проход)..."
	python arbitrage_bot.py --config config.bot.json --once

test:
	@echo "Запуск тестов..."
	python -m pytest tests/ -v

clean:
	@echo "Очистка временных файлов..."
	rm -rf __pycache__ */__pycache__ .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "*.log" -delete

backup:
	@echo "Создание бэкапа..."
	tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz *.py *.json data/ config/ utils/ scripts/

monitor:
	@echo "Запуск системного мониторинга..."
	python utils/monitor.py

help:
	@echo "Доступные команды:"
	@echo "  install      - Установить минимальные зависимости"
	@echo "  install-full - Установить все зависимости"
	@echo "  venv         - Создать виртуальное окружение"
	@echo "  run          - Запустить бота в цикле"
	@echo "  run-once     - Запустить один проход"
	@echo "  test         - Запустить тесты"
	@echo "  clean        - Очистить временные файлы"
	@echo "  backup       - Создать бэкап"
	@echo "  monitor      - Системный мониторинг"
