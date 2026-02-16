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
