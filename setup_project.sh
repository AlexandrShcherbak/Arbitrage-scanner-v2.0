#!/bin/bash

# ===========================================
# 1. СОЗДАНИЕ СТРУКТУРЫ ПАПОК
# ===========================================

echo "🔧 Создание структуры проекта..."

# Основные директории
mkdir -p data/opportunities data/trades data/logs data/history
mkdir -p utils scripts config backups
mkdir -p logs/daily logs/trades logs/system
mkdir -p tests/unit tests/integration

# Создаем README
cat > README.md << 'EOF'
# Crypto Arbitrage Scanner

Профессиональный сканер арбитражных возможностей на криптобиржах.

## Быстрый старт

1. Установите зависимости: `pip install -r requirements.txt`
2. Настройте config.json и .env файлы
3. Запустите сканер: `python arbitrage_scanner.py`

## Поддерживаемые биржи
- KuCoin
- Huobi
- Poloniex
- Latoken
- Dcoin
EOF

# ===========================================
# 2. СОЗДАНИЕ КОНФИГУРАЦИОННЫХ ФАЙЛОВ
# ===========================================

echo "📝 Создание конфигурационных файлов..."

# Создаем .env файл
cat > .env << 'EOF'
# Базовые настройки
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false

# Пути
DATA_DIR=./data
LOG_DIR=./logs

# Безопасность
ENCRYPTION_KEY=change_this_in_production

# API CoinMarketCap (опционально)
TELEGRAM_CHAT_ID=

# Лимиты
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=30
cat > requirements.txt << 'EOF'
# Основные зависимости
requests==2.31.0
pandas==2.1.4
numpy==1.26.2
python-dotenv==1.0.0
asyncio==3.4.3

# Для работы с API
kucoin-python==1.0.9
python-poloniex==0.2.5

# Логирование
loguru==0.7.2
colorama==0.4.6
pytz==2023.3
tzlocal==5.2
tqdm==4.66.1

# Безопасность
cryptography==41.0.7

# Для анализа
scipy==1.11.4
EOF

# Создаем requirements-minimal.txt
cat > requirements-minimal.txt << 'EOF'
requests==2.31.0
pandas==2.1.4
numpy==1.26.2
python-dotenv==1.0.0
ccxt==4.1.59
loguru==0.7.2
colorama==0.4.6
python-dateutil==2.8.2
pytz==2023.3
EOF

# ===========================================
# 3. СОЗДАНИЕ ДОПОЛНИТЕЛЬНЫХ СКРИПТОВ
# ===========================================

echo "💻 Создание вспомогательных скриптов..."

# 1. Скрипт установки
cat > setup.sh << 'EOF'
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
EOF

chmod +x setup.sh

# 2. Скрипт запуска
cat > run_scanner.sh << 'EOF'
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
EOF

chmod +x run_scanner.sh

# 3. Скрипт обновления цен
cat > utils/update_prices.py << 'EOF'
#!/usr/bin/env python3
"""
Скрипт для обновления цен с бирж
"""
import requests
import json
import time
from datetime import datetime

def fetch_prices():
    """Получение текущих цен"""
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    coins = config['coins']
    currency = config['currency']
    
    prices = {}
    
    for coin in coins:
        try:
            url = f"https://api.coinmarketcap.com/data-api/v3/cryptocurrency/market-pairs/latest"
            params = {
                "slug": coin,
                "start": 1,
                "limit": 20,
                "category": "spot",
                "sort": "cmc_rank_advanced"
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                prices[coin] = {
                    'timestamp': datetime.now().isoformat(),
                    'pairs': data.get('data', {}).get('marketPairs', [])
                }
            
            time.sleep(0.5)  # Чтобы не блокировали
            
        except Exception as e:
            print(f"Ошибка для {coin}: {e}")
    
    # Сохранение цен
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"data/history/prices_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(prices, f, indent=2)
    
    print(f"✅ Цены сохранены в {filename}")
    return prices

if __name__ == "__main__":
    fetch_prices()
EOF

# 4. Скрипт анализа результатов
cat > utils/analyze_results.py << 'EOF'
#!/usr/bin/env python3
"""
Анализ найденных арбитражных возможностей
"""
import json
import pandas as pd
import glob
from datetime import datetime

def analyze_opportunities():
    """Анализ сохраненных возможностей"""
    
    # Поиск всех CSV файлов
    csv_files = glob.glob("data/opportunities/*.csv")
    
    if not csv_files:
        print("❌ Файлы с возможностями не найдены")
        return
    
    all_data = []
    
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            all_data.append(df)
        except Exception as e:
            print(f"Ошибка чтения {file}: {e}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Анализ
        print("\n📊 АНАЛИЗ АРБИТРАЖНЫХ ВОЗМОЖНОСТЕЙ")
        print("="*50)
        
        # Топ возможностей по прибыли
        top_10 = combined_df.nlargest(10, 'net_percent')
        print("\n🔝 Топ 10 по прибыльности:")
        print(top_10[['coin', 'buy_exchange', 'sell_exchange', 'net_percent']].to_string())
        
        # Статистика по монетам
        print("\n📈 Статистика по монетам:")
        coin_stats = combined_df.groupby('coin').agg({
            'net_percent': ['count', 'mean', 'max'],
            'net_profit': 'sum'
        }).round(2)
        print(coin_stats.to_string())
        
        # Статистика по биржам
        print("\n🏦 Частота появления бирж (покупка):")
        buy_stats = combined_df['buy_exchange'].value_counts()
        print(buy_stats.to_string())
        
        print("\n🏦 Частота появления бирж (продажа):")
        sell_stats = combined_df['sell_exchange'].value_counts()
        print(sell_stats.to_string())
        
        # Сохранение анализа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        analysis_file = f"data/analysis/report_{timestamp}.xlsx"
        
        with pd.ExcelWriter(analysis_file) as writer:
            combined_df.to_excel(writer, sheet_name='Все возможности', index=False)
            top_10.to_excel(writer, sheet_name='Топ 10', index=False)
            coin_stats.to_excel(writer, sheet_name='По монетам')
        
        print(f"\n✅ Анализ сохранен в {analysis_file}")

if __name__ == "__main__":
    analyze_opportunities()
EOF

# 5. Скрипт проверки API
cat > utils/check_apis.py << 'EOF'
#!/usr/bin/env python3
"""
Проверка доступности API бирж
"""
import requests
import json
import time

def check_exchange_apis():
    """Проверка API поддерживаемых бирж"""
    
    exchanges = {
        'KuCoin': 'https://api.kucoin.com/api/v1/ping',
        'Huobi': 'https://api.huobi.pro/market/tickers',
        'Poloniex': 'https://poloniex.com/public?command=returnTicker',
        'Latoken': 'https://api.latoken.com/v2/ticker',
        'Dcoin': 'https://openapi.dcoin.com/api/v1/ping',
        'CoinMarketCap': 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    }
    
    print("🔍 Проверка доступности API бирж...")
    print("="*50)
    
    results = {}
    
    for exchange, url in exchanges.items():
        try:
            start_time = time.time()
            
            if exchange == 'CoinMarketCap':
                # Для CMC нужен API ключ
                response = requests.get(url, timeout=10)
            else:
                response = requests.get(url, timeout=10)
            
            response_time = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                status = "✅ Доступно"
                results[exchange] = {
                    'status': 'online',
                    'response_time': response_time
                }
            else:
                status = "⚠️  Проблемы"
                results[exchange] = {
                    'status': 'error',
                    'response_time': response_time,
                    'code': response.status_code
                }
            
            print(f"{exchange:15} {status:15} {response_time:6} ms")
            
        except requests.exceptions.Timeout:
            print(f"{exchange:15} ❌ Таймаут")
            results[exchange] = {'status': 'timeout'}
        except Exception as e:
            print(f"{exchange:15} ❌ Ошибка: {str(e)[:30]}")
            results[exchange] = {'status': 'error', 'details': str(e)}
        
        time.sleep(0.5)
    
    # Сохранение результатов
    with open('data/logs/api_check.json', 'w') as f:
        json.dump({
            'timestamp': time.time(),
            'results': results
        }, f, indent=2)
    
    return results

if __name__ == "__main__":
    check_exchange_apis()
EOF

# ===========================================
# 4. СОЗДАНИЕ УПРАВЛЯЮЩИХ СКРИПТОВ
# ===========================================

echo "⚙️ Создание управляющих скриптов..."

# 1. Makefile для удобства
cat > Makefile << 'EOF'
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
EOF

# 2. Скрипт мониторинга
cat > utils/monitor.py << 'EOF'
#!/usr/bin/env python3
"""
Мониторинг системы и уведомления
"""
import psutil
import json
import time
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SystemMonitor:
    def __init__(self):
        self.alert_thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'disk_percent': 90
        }
    
    def check_resources(self):
        """Проверка системных ресурсов"""
        stats = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_io': psutil.net_io_counters()._asdict()
        }
        
        # Проверка порогов
        alerts = []
        if stats['cpu_percent'] > self.alert_thresholds['cpu_percent']:
            alerts.append(f"CPU usage high: {stats['cpu_percent']}%")
        
        if stats['memory_percent'] > self.alert_thresholds['memory_percent']:
            alerts.append(f"Memory usage high: {stats['memory_percent']}%")
        
        if stats['disk_percent'] > self.alert_thresholds['disk_percent']:
            alerts.append(f"Disk usage high: {stats['disk_percent']}%")
        
        if alerts:
            logging.warning(" | ".join(alerts))
        
        return stats, alerts
    
    def log_stats(self, stats):
        """Логирование статистики"""
        filename = f"logs/system/monitor_{datetime.now().strftime('%Y%m%d')}.json"
        
        try:
            with open(filename, 'a') as f:
                f.write(json.dumps(stats) + '\n')
        except Exception as e:
            logging.error(f"Ошибка записи лога: {e}")

def main():
    monitor = SystemMonitor()
    
    print("📊 Мониторинг системы запущен")
    print("Нажмите Ctrl+C для остановки")
    
    try:
        while True:
            stats, alerts = monitor.check_resources()
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                  f"CPU: {stats['cpu_percent']:.1f}% | "
                  f"Mem: {stats['memory_percent']:.1f}% | "
                  f"Disk: {stats['disk_percent']:.1f}%")
            
            if alerts:
                print("⚠️  " + " | ".join(alerts))
            
            monitor.log_stats(stats)
            time.sleep(60)  # Проверка каждую минуту
            
    except KeyboardInterrupt:
        print("\n⏹️  Мониторинг остановлен")

if __name__ == "__main__":
    main()
EOF

# ===========================================
# 5. СОЗДАНИЕ ФАЙЛОВ ДЛЯ БЕКАПОВ И ЛОГОВ
# ===========================================

echo "📁 Создание файлов для логирования..."

# Файл для логирования сделок
cat > data/trades/trades_template.json << 'EOF'
{
  "trades": [],
  "summary": {
    "total_trades": 0,
    "successful_trades": 0,
    "failed_trades": 0,
    "total_profit_usdt": 0,
    "total_volume_usdt": 0
  }
}
EOF

# Конфиг для логгера
cat > config/logging_config.json << 'EOF'
{
  "version": 1,
  "disable_existing_loggers": false,
  "formatters": {
    "detailed": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "simple": {
      "format": "%(levelname)s - %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "INFO",
      "formatter": "simple"
    },
    "file": {
      "class": "logging.handlers.RotatingFileHandler",
      "filename": "logs/system/arbitrage.log",
      "maxBytes": 10485760,
      "backupCount": 5,
      "formatter": "detailed"
    },
    "trades_file": {
      "class": "logging.handlers.RotatingFileHandler",
      "filename": "logs/trades/trades.log",
      "maxBytes": 10485760,
      "backupCount": 10,
      "formatter": "detailed"
    }
  },
  "loggers": {
    "arbitrage": {
      "handlers": ["console", "file"],
      "level": "INFO"
    },
    "trades": {
      "handlers": ["trades_file"],
      "level": "INFO"
    }
  }
}
EOF

# ===========================================
# 6. СОЗДАНИЕ БЭКАП СКРИПТОВ
# ===========================================

echo "💾 Создание скриптов для бэкапа..."

# Скрипт бэкапа
cat > scripts/backup.sh << 'EOF'
#!/bin/bash

# Скрипт для создания бэкапа проекта

BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="arbitrage_backup_${TIMESTAMP}.tar.gz"

echo "💾 Создание бэкапа проекта..."

# Создаем директорию для бэкапов если нет
mkdir -p $BACKUP_DIR

# Архивируем важные файлы
tar -czf $BACKUP_DIR/$BACKUP_NAME \
    *.py \
    *.json \
    *.sh \
    *.md \
    config/ \
    utils/ \
    data/opportunities/ \
    data/trades/ \
    --exclude="__pycache__" \
    --exclude="*.log" \
    --exclude="*.tmp"

# Проверяем размер
SIZE=$(du -h $BACKUP_DIR/$BACKUP_NAME | cut -f1)

echo "✅ Бэкап создан: $BACKUP_DIR/$BACKUP_NAME ($SIZE)"

# Удаляем старые бэкапы (оставляем последние 10)
cd $BACKUP_DIR
ls -t | tail -n +11 | xargs -r rm
cd ..

echo "🗑️  Удалены старые бэкапы (оставлено последних 10)"
EOF

chmod +x scripts/backup.sh

# Скрипт восстановления
cat > scripts/restore.sh << 'EOF'
#!/bin/bash

# Скрипт для восстановления из бэкапа

BACKUP_DIR="backups"

if [ -z "$1" ]; then
    echo "❌ Укажите файл бэкапа для восстановления"
    echo "Доступные бэкапы:"
    ls -la $BACKUP_DIR/*.tar.gz 2>/dev/null || echo "   Нет бэкапов"
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Файл $BACKUP_FILE не найден"
    exit 1
fi

echo "⚠️  Восстановление из бэкапа: $BACKUP_FILE"
echo "Это перезапишет существующие файлы!"
read -p "Продолжить? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 Восстановление..."
    
    # Создаем временную директорию
    TEMP_DIR=$(mktemp -d)
    
    # Распаковываем бэкап
    tar -xzf "$BACKUP_FILE" -C "$TEMP_DIR"
    
    # Копируем файлы
    cp -r "$TEMP_DIR"/* .
    
    # Очищаем
    rm -rf "$TEMP_DIR"
    
    echo "✅ Восстановление завершено"
else
    echo "❌ Восстановление отменено"
fi
EOF

chmod +x scripts/restore.sh

# ===========================================
# 7. СОЗДАНИЕ GITIGNORE
# ===========================================

echo "🐙 Создание .gitignore..."

cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Logs
logs/
*.log
logs.json

# Data files
data/opportunities/*.csv
data/opportunities/*.json
data/history/*.json
data/trades/*.json
backups/*.tar.gz

# API keys
*.key
*.pem
secret*
config_private.json

# OS
.DS_Store
Thumbs.db

# Temporary
temp/
tmp/
*.tmp
*.temp

# Test
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/

# Backups
*.bak
*.backup
EOF

# ===========================================
# 8. ФИНАЛЬНЫЕ КОМАНДЫ И НАСТРОЙКА
# ===========================================

echo "🎯 Выполнение финальных настроек..."

# Делаем все Python скрипты исполняемыми
find . -name "*.py" -type f -exec chmod +x {} \;

# Создаем пустые __init__.py файлы
touch utils/__init__.py
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py

# Проверяем структуру
echo "📁 Конечная структура проекта:"
tree -I 'venv|__pycache__' -L 3

# Создаем инструкцию для запуска
cat > QUICK_START.md << 'EOF'
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
EOF

# Создаем requirements.txt
CMC_API_KEY=
ENABLE_TELEGRAM=false
TELEGRAM_BOT_TOKEN=

