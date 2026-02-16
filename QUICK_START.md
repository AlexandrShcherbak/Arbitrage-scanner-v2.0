# Быстрый старт

## 1. Установка
```bash
# Создайте виртуальное окружение
python -m venv venv

# Активируйте его
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements-minimal.txt
# Утилиты
python-dateutil==2.8.2
ccxt==4.1.59
websockets==12.0
aiohttp==3.9.1
