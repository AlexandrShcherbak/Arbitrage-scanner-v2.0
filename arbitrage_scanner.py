import requests
import json
import time
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Tuple
import numpy as np

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage.log'),
        logging.StreamHandler()
    ]
)

class CryptoArbitrageScanner:
    def __init__(self, config_path: str = "config.json"):
        """Инициализация сканера арбитража"""
        self.load_config(config_path)
        self.setup_exchange_apis()
        self.opportunities = []
        
    def load_config(self, config_path: str):
        """Загрузка конфигурации"""
        try:
            with open(config_path, "r") as f:
                self.config = json.load(f)
                
            self.currency = self.config.get("currency", "USDT")
            self.ex_filter = self.config.get("exchanges-filter", "true")
            self.investment = float(self.config.get("investment", 1000))
            self.coins = self.config.get("coins", [])
            self.exchanges = self.config.get("exchanges", [])
            self.min_profit_percent = float(self.config.get("min_profit_percent", 1.0))
            self.min_volume = float(self.config.get("min_volume", 10000))
            
            # Комиссии бирж (примерные значения)
            self.exchange_fees = {
                "binance": {"maker": 0.1, "taker": 0.1},
                "kucoin": {"maker": 0.1, "taker": 0.1},
                "huobi": {"maker": 0.2, "taker": 0.2},
                "okex": {"maker": 0.1, "taker": 0.15},
                "bybit": {"maker": 0.1, "taker": 0.1},
                "gate.io": {"maker": 0.2, "taker": 0.2}
            }
            
        except Exception as e:
            logging.error(f"Ошибка загрузки конфигурации: {e}")
            raise
            
    def setup_exchange_apis(self):
        """Настройка подключений к API бирж"""
        self.api_endpoints = {
            "coinmarketcap": "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/market-pairs/latest",
            "binance": "https://api.binance.com/api/v3",
            "kucoin": "https://api.kucoin.com/api/v1",
            # Добавьте другие биржи по необходимости
        }
        
    def get_market_data(self, coin: str) -> Dict:
        """Получение рыночных данных для монеты"""
        try:
            params = {
                "slug": coin,
                "start": 1,
                "limit": 100,
                "category": "spot",
                "sort": "cmc_rank_advanced"
            }
            
            response = requests.get(
                self.api_endpoints["coinmarketcap"],
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logging.warning(f"Ошибка API для {coin}: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка соединения для {coin}: {e}")
            return None
            
    def calculate_real_profit(self, buy_price: float, sell_price: float, 
                             buy_exchange: str, sell_exchange: str) -> Dict:
        """Расчет реальной прибыли с учетом комиссий"""
        
        # Приведение имени биржи к нижнему регистру для поиска комиссий
        buy_exchange_lower = buy_exchange.lower()
        sell_exchange_lower = sell_exchange.lower()
        
        # Получение комиссий (по умолчанию 0.2% если биржа не найдена)
        buy_fee = self.exchange_fees.get(buy_exchange_lower, {}).get("taker", 0.2)
        sell_fee = self.exchange_fees.get(sell_exchange_lower, {}).get("taker", 0.2)
        
        # Расчет с учетом комиссий
        buy_cost = self.investment * (1 + buy_fee/100)
        coins_bought = self.investment / buy_price
        sell_revenue = coins_bought * sell_price * (1 - sell_fee/100)
        
        # Расчеты
        gross_profit = sell_revenue - self.investment
        gross_profit_percent = (gross_profit / self.investment) * 100
        
        net_profit = sell_revenue - buy_cost
        net_profit_percent = (net_profit / self.investment) * 100
        
        return {
            "gross_profit": gross_profit,
            "gross_percent": gross_profit_percent,
            "net_profit": net_profit,
            "net_percent": net_profit_percent,
            "total_fees": (buy_cost - self.investment) + (self.investment - sell_revenue + gross_profit),
            "buy_fee_percent": buy_fee,
            "sell_fee_percent": sell_fee
        }
        
    def check_liquidity(self, exchange: str, coin: str, volume_needed: float) -> bool:
        """Проверка ликвидности (упрощенная версия)"""
        # В реальной реализации здесь должен быть запрос к API биржи
        # для получения стакана заявок и расчета ликвидности
        
        # Временная заглушка - предполагаем достаточную ликвидность
        # для популярных бирж и монет
        high_liquidity_exchanges = ["binance", "kucoin", "huobi", "okex", "bybit"]
        high_liquidity_coins = ["bitcoin", "ethereum", "bnb", "solana", "xrp"]
        
        if exchange.lower() in high_liquidity_exchanges and coin.lower() in high_liquidity_coins:
            return volume_needed <= 100000  # До 100к USDT ликвидность есть
        return volume_needed <= 10000  # Для остальных до 10к USDT
        
    def scan_coin(self, coin: str) -> List[Dict]:
        """Сканирование арбитражных возможностей для одной монеты"""
        opportunities = []
        
        market_data = self.get_market_data(coin)
        if not market_data or "data" not in market_data:
            return opportunities
            
        market_pairs = market_data["data"].get("marketPairs", [])
        
        # Сбор данных о ценах
        price_data = []
        for pair in market_pairs:
            if f"/{self.currency}" in str(pair):
                exchange_name = pair.get("exchangeName", "")
                
                # Фильтрация по биржам если включено
                if self.ex_filter == "true" and exchange_name.lower() not in [e.lower() for e in self.exchanges]:
                    continue
                    
                price = float(pair.get("price", 0))
                volume_24h = float(pair.get("volume24h", 0))
                market_url = pair.get("marketUrl", "")
                
                if price > 0 and volume_24h >= self.min_volume:
                    price_data.append({
                        "exchange": exchange_name,
                        "price": price,
                        "volume": volume_24h,
                        "url": market_url
                    })
                    
        if len(price_data) < 2:
            return opportunities
            
        # Поиск лучших пар для арбитража
        for i, buy_data in enumerate(price_data):
            for j, sell_data in enumerate(price_data):
                if i == j:
                    continue
                    
                buy_price = buy_data["price"]
                sell_price = sell_data["price"]
                
                # Расчет прибыли
                profit_data = self.calculate_real_profit(
                    buy_price, sell_price,
                    buy_data["exchange"], sell_data["exchange"]
                )
                
                # Проверка минимальной прибыли
                if profit_data["net_percent"] >= self.min_profit_percent:
                    # Проверка ликвидности
                    if self.check_liquidity(buy_data["exchange"], coin, self.investment):
                        opportunity = {
                            "coin": coin,
                            "buy_exchange": buy_data["exchange"],
                            "buy_price": buy_price,
                            "buy_url": buy_data["url"],
                            "sell_exchange": sell_data["exchange"],
                            "sell_price": sell_price,
                            "sell_url": sell_data["url"],
                            "investment": self.investment,
                            "gross_profit": profit_data["gross_profit"],
                            "gross_percent": profit_data["gross_percent"],
                            "net_profit": profit_data["net_profit"],
                            "net_percent": profit_data["net_percent"],
                            "volume_buy": buy_data["volume"],
                            "volume_sell": sell_data["volume"],
                            "timestamp": datetime.now().isoformat(),
                            "status": "potential"
                        }
                        opportunities.append(opportunity)
                        
        return opportunities
        
    def scan_all_coins(self):
        """Сканирование всех монет из конфигурации"""
        all_opportunities = []
        
        logging.info(f"Начало сканирования {len(self.coins)} монет")
        
        for coin in self.coins:
            try:
                opportunities = self.scan_coin(coin)
                if opportunities:
                    all_opportunities.extend(opportunities)
                    # Вывод найденных возможностей
                    for opp in opportunities:
                        self.print_opportunity(opp)
                time.sleep(0.5)  # Задержка чтобы не перегружать API
                
            except Exception as e:
                logging.error(f"Ошибка при сканировании {coin}: {e}")
                
        # Сортировка по прибыльности
        all_opportunities.sort(key=lambda x: x["net_percent"], reverse=True)
        
        # Сохранение результатов
        self.save_results(all_opportunities)
        
        return all_opportunities
        
    def print_opportunity(self, opportunity: Dict):
        """Вывод информации об арбитражной возможности"""
        print("\n" + "="*60)
        print(f"💰 АРБИТРАЖНАЯ ВОЗМОЖНОСТЬ")
        print(f"Монета: {opportunity['coin'].upper()}")
        print(f"Инвестиция: {opportunity['investment']} {self.currency}")
        print("\n📈 ПОКУПКА:")
        print(f"  Биржа: {opportunity['buy_exchange']}")
        print(f"  Цена: {opportunity['buy_price']} {self.currency}")
        print(f"  Объем 24ч: {opportunity['volume_buy']:,.0f} {self.currency}")
        
        print("\n📉 ПРОДАЖА:")
        print(f"  Биржа: {opportunity['sell_exchange']}")
        print(f"  Цена: {opportunity['sell_price']} {self.currency}")
        print(f"  Объем 24ч: {opportunity['volume_sell']:,.0f} {self.currency}")
        
        print("\n💵 ПРИБЫЛЬ:")
        print(f"  Валовая: {opportunity['gross_profit']:.2f} {self.currency} "
              f"(+{opportunity['gross_percent']:.2f}%)")
        print(f"  Чистая: {opportunity['net_profit']:.2f} {self.currency} "
              f"(+{opportunity['net_percent']:.2f}%)")
        print("\n🔗 Ссылки:")
        print(f"  Купить: {opportunity['buy_url']}")
        print(f"  Продать: {opportunity['sell_url']}")
        print("="*60)
        
    def save_results(self, opportunities: List[Dict]):
        """Сохранение результатов в файл"""
        try:
            if opportunities:
                df = pd.DataFrame(opportunities)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"arbitrage_opportunities_{timestamp}.csv"
                df.to_csv(filename, index=False)
                logging.info(f"Результаты сохранены в {filename}")
                
                # Также сохраняем в JSON для удобства
                json_filename = f"arbitrage_opportunities_{timestamp}.json"
                with open(json_filename, "w") as f:
                    json.dump(opportunities, f, indent=2)
                    
        except Exception as e:
            logging.error(f"Ошибка сохранения результатов: {e}")
            
    def continuous_scan(self, interval_minutes: int = 5):
        """Непрерывное сканирование с заданным интервалом"""
        logging.info(f"Запуск непрерывного сканирования каждые {interval_minutes} минут")
        
        while True:
            try:
                print(f"\n{'='*60}")
                print(f"Сканирование начато: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                
                opportunities = self.scan_all_coins()
                
                if not opportunities:
                    print("⚠️  Арбитражные возможности не найдены")
                    
                print(f"\n⏳ Следующее сканирование через {interval_minutes} минут...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                print("\n⏹️  Сканирование остановлено пользователем")
                break
            except Exception as e:
                logging.error(f"Ошибка в непрерывном сканировании: {e}")
                time.sleep(60)  # Пауза при ошибке

# Пример файла config.json
"""
{
  "currency": "USDT",
  "exchanges-filter": "true",
  "investment": 1000,
  "min_profit_percent": 0.5,
  "min_volume": 5000,
  "coins": ["bitcoin", "ethereum", "bnb", "solana", "cardano", "ripple", "polkadot"],
  "exchanges": ["Binance", "KuCoin", "Huobi", "OKX", "Bybit", "Gate.io"]
}
"""

def main():
    """Основная функция"""
    print("🚀 Криптоарбитражный сканер запущен")
    
    try:
        scanner = CryptoArbitrageScanner("config.json")
        
        print("\nВыберите режим работы:")
        print("1. Однократное сканирование")
        print("2. Непрерывное сканирование")
        print("3. Проверить конкретную монету")
        
        choice = input("\nВведите номер (1-3): ").strip()
        
        if choice == "1":
            scanner.scan_all_coins()
        elif choice == "2":
            interval = input("Интервал сканирования в минутах (по умолчанию 5): ").strip()
            interval = int(interval) if interval else 5
            scanner.continuous_scan(interval)
        elif choice == "3":
            coin = input("Введите название монеты (например, bitcoin): ").strip().lower()
            opportunities = scanner.scan_coin(coin)
            if opportunities:
                for opp in opportunities:
                    scanner.print_opportunity(opp)
            else:
                print(f"Арбитражные возможности для {coin} не найдены")
        else:
            print("Неверный выбор")
            
    except FileNotFoundError:
        print("❌ Файл config.json не найден")
        print("Создайте config.json по примеру выше")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()