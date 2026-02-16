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
