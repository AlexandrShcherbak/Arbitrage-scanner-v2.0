#!/bin/bash

set -e

echo "🚀 Настройка Crypto Arbitrage Bot..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен"
    exit 1
fi

python3 -m venv venv

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

pip install --upgrade pip
pip install -r requirements-minimal.txt

if [ ! -f "config.bot.json" ]; then
    echo "❌ config.bot.json не найден"
        exit 1
fi

echo "✅ Установка завершена!"
echo "Запуск (один проход): python arbitrage_bot.py --config config.bot.json --once"
