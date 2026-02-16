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
