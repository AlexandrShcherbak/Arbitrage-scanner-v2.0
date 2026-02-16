#!/bin/bash

# Активация виртуального окружения
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# Проверка конфига
if [ ! -f "config.json" ]; then
    echo "❌ config.json не найден"
    exit 1
fi

# Запуск сканера
echo "🚀 Запуск сканера арбитража..."
echo "📊 Монеты: $(python -c "import json; print(', '.join(json.load(open('config.json'))['coins'][:3]))")..."
echo "🏦 Биржи: $(python -c "import json; print(', '.join(json.load(open('config.json'))['exchanges']))")"

python arbitrage_scanner.py "$@"
