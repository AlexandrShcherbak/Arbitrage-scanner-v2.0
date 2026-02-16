from arbitrage_bot import ArbitrageEngine, Quote


def test_engine_finds_positive_opportunity():
    engine = ArbitrageEngine(taker_fee_percent=0.1, slippage_percent=0.2, min_profit_percent=0.5)
    quotes = [
        Quote(symbol="BTC", source="mexc", market_type="cex", bid=100.0, ask=100.2),
        Quote(symbol="BTC", source="bybit", market_type="cex", bid=102.0, ask=102.2),
    ]

    opportunities = engine.find(quotes)

    assert opportunities
    assert opportunities[0].symbol == "BTC"
    assert opportunities[0].buy_source == "mexc"
    assert opportunities[0].sell_source == "bybit"


def test_engine_ignores_unprofitable():
    engine = ArbitrageEngine(taker_fee_percent=0.1, slippage_percent=0.5, min_profit_percent=1.0)
    quotes = [
        Quote(symbol="ETH", source="dex:a", market_type="dex", bid=100.0, ask=100.1),
        Quote(symbol="ETH", source="cex:b", market_type="cex", bid=100.2, ask=100.3),
    ]

    opportunities = engine.find(quotes)

    assert not opportunities
