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
