#!/bin/bash

echo "🚀 Настройка Crypto Arbitrage Scanner..."

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен"
    exit 1
fi

# Создание виртуального окружения
python3 -m venv venv

# Активация окружения
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements-minimal.txt

# Создание необходимых файлов
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Отредактируйте .env файл"
fi

if [ ! -f "config.json" ]; then
    echo "❌ config.json не найден"
    exit 1
fi

echo "✅ Установка завершена!"
echo "Для запуска: python arbitrage_scanner.py"
