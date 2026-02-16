.PHONY: install run test clean backup monitor analyze

install:
	@echo "Установка зависимостей..."
	pip install -r requirements-minimal.txt

install-full:
	@echo "Установка всех зависимостей..."
	pip install -r requirements.txt

venv:
	@echo "Создание виртуального окружения..."
	python -m venv venv

run:
	@echo "Запуск сканера..."
	python arbitrage_scanner.py

run-continuous:
	@echo "Запуск непрерывного сканирования..."
	python arbitrage_scanner.py --continuous --interval 5

test:
	@echo "Запуск тестов..."
	python -m pytest tests/ -v

clean:
	@echo "Очистка временных файлов..."
	rm -rf __pycache__
	rm -rf */__pycache__
	rm -rf data/opportunities/*.csv
	rm -rf data/opportunities/*.json
	find . -name "*.pyc" -delete
	find . -name "*.log" -delete

backup:
	@echo "Создание бэкапа..."
	tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz *.py *.json data/ config/ utils/

monitor:
	@echo "Запуск мониторинга..."
	python utils/monitor.py

analyze:
	@echo "Анализ результатов..."
	python utils/analyze_results.py

check-apis:
	@echo "Проверка API..."
	python utils/check_apis.py

update-prices:
	@echo "Обновление цен..."
	python utils/update_prices.py

help:
	@echo "Доступные команды:"
	@echo "  install     - Установить зависимости"
	@echo "  run         - Запустить сканер"
	@echo "  run-continuous - Непрерывное сканирование"
	@echo "  test        - Запустить тесты"
	@echo "  clean       - Очистить временные файлы"
	@echo "  backup      - Создать бэкап"
	@echo "  monitor     - Запустить мониторинг"
	@echo "  analyze     - Анализ результатов"
	@echo "  check-apis  - Проверка API бирж"
	@echo "  update-prices - Обновление цен"
