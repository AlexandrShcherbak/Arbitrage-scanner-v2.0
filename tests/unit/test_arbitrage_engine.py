from arbitrage_bot import ArbitrageEngine, Quote


def test_engine_finds_positive_opportunity_same_fiat():
    engine = ArbitrageEngine(taker_fee_percent=0.1, slippage_percent=0.2, min_profit_percent=0.5)
    quotes = [
        Quote(symbol="BTC", source="mexc", market_type="cex", bid=100.0, ask=100.2, fiat="USDT"),
        Quote(symbol="BTC", source="bybit", market_type="cex", bid=102.0, ask=102.2, fiat="USDT"),
    ]

    opportunities = engine.find(quotes)

    assert opportunities
    assert opportunities[0].symbol == "BTC"
    assert opportunities[0].buy_source == "mexc"
    assert opportunities[0].sell_source == "bybit"
    assert opportunities[0].fiat == "USDT"


def test_engine_ignores_unprofitable():
    engine = ArbitrageEngine(taker_fee_percent=0.1, slippage_percent=0.5, min_profit_percent=1.0)
    quotes = [
        Quote(symbol="ETH", source="dex:a", market_type="dex", bid=100.0, ask=100.1, fiat="USDT"),
        Quote(symbol="ETH", source="cex:b", market_type="cex", bid=100.2, ask=100.3, fiat="USDT"),
    ]

    opportunities = engine.find(quotes)

    assert not opportunities


def test_engine_blocks_cross_fiat_by_default():
    engine = ArbitrageEngine(taker_fee_percent=0.1, slippage_percent=0.2, min_profit_percent=0.1)
    quotes = [
        Quote(symbol="USDT", source="bybit_p2p", market_type="p2p", bid=100.0, ask=100.5, fiat="RUB"),
        Quote(symbol="USDT", source="mexc", market_type="cex", bid=1.01, ask=1.02, fiat="USDT"),
    ]

    opportunities = engine.find(quotes)

    assert opportunities == []


def test_engine_cross_fiat_with_fx_enabled():
    engine = ArbitrageEngine(
        taker_fee_percent=0.1,
        slippage_percent=0.1,
        min_profit_percent=0.1,
        fx_rates_to_usdt={"RUB": 0.01, "USDT": 1.0},
    )
    quotes = [
        Quote(symbol="USDT", source="bybit_p2p", market_type="p2p", bid=102.0, ask=100.0, fiat="RUB"),
        Quote(symbol="USDT", source="mexc", market_type="cex", bid=1.05, ask=1.06, fiat="USDT"),
    ]

    opportunities = engine.find(quotes, allow_cross_fiat=True)

    assert opportunities
    assert opportunities[0].fiat == "USDT"
