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
