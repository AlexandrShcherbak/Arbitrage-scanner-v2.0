from arbitrage_bot import ArbitrageEngine, PreTradeValidator, Quote, RiskManager


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


def test_pretrade_validator_blocks_unrealistic_spread_and_source():
    validator = PreTradeValidator(min_quote_volume=1000, max_spread_percent=20, blocked_sources=["badex"])
    opportunity = ArbitrageEngine(0.1, 0.1, 0.1).find(
        [
            Quote(symbol="BTC", source="badex", market_type="cex", bid=100, ask=90, volume_quote=3000, fiat="USDT"),
            Quote(symbol="BTC", source="okex", market_type="cex", bid=130, ask=131, volume_quote=3000, fiat="USDT"),
        ]
    )[0]
    quote_index = {
        ("BTC", "badex"): Quote(symbol="BTC", source="badex", market_type="cex", bid=100, ask=90, volume_quote=3000, fiat="USDT"),
        ("BTC", "okex"): Quote(symbol="BTC", source="okex", market_type="cex", bid=130, ask=131, volume_quote=3000, fiat="USDT"),
    }

    ok, reasons = validator.validate(opportunity, quote_index)

    assert not ok
    assert "buy source blocked: badex" in reasons
    assert "spread exceeds sanity threshold" in reasons


def test_risk_manager_blocks_on_daily_loss(tmp_path):
    state_path = tmp_path / "risk_state.json"
    state_path.write_text('{"date":"2099-01-01","realized_pnl_usdt":0}', encoding="utf-8")
    manager = RiskManager(max_signals_per_cycle=2, max_daily_loss_usdt=100, state_path=str(state_path))

    # Сбросит дату на сегодня
    can_signal, _ = manager.can_signal()
    assert can_signal

    state_path.write_text(
        '{"date":"' + manager._today() + '","realized_pnl_usdt":-150}',
        encoding="utf-8",
    )
    can_signal, reason = manager.can_signal()

    assert not can_signal
    assert reason == "daily loss limit reached"
