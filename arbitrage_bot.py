from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import ccxt
import requests


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("arbitrage_bot")


@dataclass
class Quote:
    symbol: str
    source: str
    market_type: str  # cex | dex | p2p
    bid: float
    ask: float
    volume_quote: float = 0.0
    fiat: str = "USDT"
    ts: float = 0.0


@dataclass
class Opportunity:
    symbol: str
    buy_source: str
    sell_source: str
    buy_price: float
    sell_price: float
    gross_percent: float
    net_percent: float
    spread_value: float
    fiat: str
    market_type_buy: str
    market_type_sell: str


class CoinCapUniverseClient:
    URL = "https://api.coincap.io/v2/assets"

    def get_symbols(self, limit: int = 30) -> List[str]:
        try:
            response = requests.get(self.URL, params={"limit": limit}, timeout=10)
            response.raise_for_status()
            payload = response.json()
            assets = payload.get("data", [])
            return [asset["symbol"].upper() for asset in assets if asset.get("symbol")]
        except Exception as exc:
            logger.warning("CoinCap недоступен, fallback на symbols из конфига: %s", exc)
            return []


class CEXCollector:
    def __init__(self, exchange_ids: Iterable[str], quote_asset: str, min_quote_volume: float = 0.0):
        self.exchange_ids = list(exchange_ids)
        self.quote_asset = quote_asset.upper()
        self.min_quote_volume = float(min_quote_volume)

    def _collect_batch(self, exchange: ccxt.Exchange, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Пытаемся взять тикеры батчем, иначе fallback на fetch_ticker по одному."""
        if not symbols:
            return {}
        try:
            if exchange.has.get("fetchTickers"):
                tickers = exchange.fetch_tickers(symbols)
                return {k: v for k, v in tickers.items() if isinstance(v, dict)}
        except Exception as exc:
            logger.debug("fetch_tickers fallback на %s: %s", exchange.id, exc)

        result: Dict[str, Dict[str, Any]] = {}
        for symbol in symbols:
            try:
                result[symbol] = exchange.fetch_ticker(symbol)
            except Exception:
                continue
        return result

    def collect(self, base_symbols: Iterable[str]) -> List[Quote]:
        quotes: List[Quote] = []
        base_symbols = [symbol.upper() for symbol in base_symbols]

        for exchange_id in self.exchange_ids:
            try:
                exchange_class = getattr(ccxt, exchange_id)
            except AttributeError:
                logger.warning("CEX %s не поддерживается ccxt", exchange_id)
                continue

            exchange = exchange_class({"enableRateLimit": True})
            try:
                exchange.load_markets()
                symbols = [f"{base}/{self.quote_asset}" for base in base_symbols if f"{base}/{self.quote_asset}" in exchange.markets]
                tickers = self._collect_batch(exchange, symbols)

                for market_symbol, ticker in tickers.items():
                    bid = ticker.get("bid")
                    ask = ticker.get("ask")
                    if not bid or not ask:
                        continue
                    volume_quote = float(ticker.get("quoteVolume") or 0.0)
                    if volume_quote < self.min_quote_volume:
                        continue
                    base = market_symbol.split("/")[0].upper()
                    quotes.append(
                        Quote(
                            symbol=base,
                            source=exchange_id,
                            market_type="cex",
                            bid=float(bid),
                            ask=float(ask),
                            volume_quote=volume_quote,
                            fiat=self.quote_asset,
                            ts=time.time(),
                        )
                    )
            except Exception as exc:
                logger.warning("Ошибка CEX %s: %s", exchange_id, exc)
            finally:
                try:
                    exchange.close()
                except Exception:
                    pass
        return quotes


class DexScreenerCollector:
    URL = "https://api.dexscreener.com/latest/dex/search"

    def __init__(self, quote_assets: Optional[List[str]] = None, min_liquidity_usd: float = 0.0):
        self.quote_assets = {asset.upper() for asset in (quote_assets or ["USDT", "USDC"])}
        self.min_liquidity_usd = float(min_liquidity_usd)

    def collect(self, base_symbols: Iterable[str]) -> List[Quote]:
        quotes: List[Quote] = []
        for base in [symbol.upper() for symbol in base_symbols]:
            try:
                response = requests.get(self.URL, params={"q": base}, timeout=12)
                response.raise_for_status()
                pairs = response.json().get("pairs", [])

                best_pair: Optional[Dict[str, Any]] = None
                for pair in pairs:
                    quote_symbol = ((pair.get("quoteToken") or {}).get("symbol") or "").upper()
                    if quote_symbol not in self.quote_assets:
                        continue
                    price = pair.get("priceUsd")
                    liquidity = float(((pair.get("liquidity") or {}).get("usd") or 0.0))
                    if not price or liquidity < self.min_liquidity_usd:
                        continue
                    if best_pair is None or liquidity > best_pair["liquidity"]:
                        best_pair = {
                            "price": float(price),
                            "liquidity": liquidity,
                            "dex": pair.get("dexId", "dex"),
                        }

                if best_pair:
                    fair_price = best_pair["price"]
                    quotes.append(
                        Quote(
                            symbol=base,
                            source=f"dex:{best_pair['dex']}",
                            market_type="dex",
                            bid=fair_price * 0.998,
                            ask=fair_price * 1.002,
                            volume_quote=best_pair["liquidity"],
                            fiat="USD",
                            ts=time.time(),
                        )
                    )
            except Exception as exc:
                logger.warning("Ошибка DEX для %s: %s", base, exc)
        return quotes


class BybitP2PCollector:
    URL = "https://api2.bybit.com/fiat/otc/item/online"

    def _request_side_prices(self, token: str, side: str, amount_rub: int, size: int) -> List[float]:
        payload = {
            "tokenId": token,
            "currencyId": "RUB",
            "side": side,
            "size": str(size),
            "page": "1",
            "amount": str(amount_rub),
            "authMaker": False,
            "canTrade": False,
        }
        response = requests.post(self.URL, json=payload, timeout=15)
        response.raise_for_status()
        items = (((response.json() or {}).get("result") or {}).get("items") or [])
        return [float(item.get("price")) for item in items if item.get("price")]

    def collect_rub(self, base_symbols: Iterable[str], amount_rub: int = 30000, size: int = 20) -> List[Quote]:
        quotes: List[Quote] = []
        for token in [symbol.upper() for symbol in base_symbols]:
            try:
                ask_prices = self._request_side_prices(token=token, side="1", amount_rub=amount_rub, size=size)
                bid_prices = self._request_side_prices(token=token, side="0", amount_rub=amount_rub, size=size)
                if not ask_prices or not bid_prices:
                    continue

                quotes.append(
                    Quote(
                        symbol=token,
                        source="bybit_p2p",
                        market_type="p2p",
                        bid=max(bid_prices),
                        ask=min(ask_prices),
                        volume_quote=0.0,
                        fiat="RUB",
                        ts=time.time(),
                    )
                )
            except Exception as exc:
                logger.warning("Ошибка Bybit P2P %s: %s", token, exc)
        return quotes


class ArbitrageEngine:
    def __init__(
        self,
        taker_fee_percent: float,
        slippage_percent: float,
        min_profit_percent: float,
        fx_rates_to_usdt: Optional[Dict[str, float]] = None,
    ):
        self.taker_fee_percent = float(taker_fee_percent)
        self.slippage_percent = float(slippage_percent)
        self.min_profit_percent = float(min_profit_percent)
        self.fx_rates_to_usdt = {"USDT": 1.0, "USD": 1.0, **(fx_rates_to_usdt or {})}

    def _normalize_price(self, price: float, fiat: str) -> Optional[float]:
        rate = self.fx_rates_to_usdt.get(fiat.upper())
        if not rate:
            return None
        return price * rate

    def _quote_pairs(self, quotes: Iterable[Quote]) -> Dict[Tuple[str, str], List[Quote]]:
        grouped: Dict[Tuple[str, str], List[Quote]] = {}
        for quote in quotes:
            grouped.setdefault((quote.symbol, quote.fiat.upper()), []).append(quote)
        return grouped

    def find(self, quotes: Iterable[Quote], allow_cross_fiat: bool = False) -> List[Opportunity]:
        groups = self._quote_pairs(quotes)

        opportunities: List[Opportunity] = []
        if allow_cross_fiat:
            # Дополнительно создаем единый пул по symbol в USDT-эквиваленте.
            symbol_pool: Dict[str, List[Quote]] = {}
            for (symbol, _fiat), fiat_quotes in groups.items():
                symbol_pool.setdefault(symbol, []).extend(fiat_quotes)
            candidate_groups = [(symbol, "USDT", items) for symbol, items in symbol_pool.items()]
        else:
            candidate_groups = [(symbol, fiat, items) for (symbol, fiat), items in groups.items()]

        for symbol, fiat, items in candidate_groups:
            for buy in items:
                for sell in items:
                    if buy.source == sell.source:
                        continue
                    if buy.ask <= 0 or sell.bid <= 0:
                        continue

                    buy_ask = buy.ask
                    sell_bid = sell.bid
                    result_fiat = fiat

                    if allow_cross_fiat and buy.fiat.upper() != sell.fiat.upper():
                        buy_norm = self._normalize_price(buy.ask, buy.fiat)
                        sell_norm = self._normalize_price(sell.bid, sell.fiat)
                        if buy_norm is None or sell_norm is None:
                            continue
                        buy_ask = buy_norm
                        sell_bid = sell_norm
                        result_fiat = "USDT"
                    elif buy.fiat.upper() != sell.fiat.upper():
                        continue

                    gross = ((sell_bid - buy_ask) / buy_ask) * 100
                    fees = 2 * self.taker_fee_percent
                    net = gross - fees - self.slippage_percent
                    if net < self.min_profit_percent:
                        continue

                    opportunities.append(
                        Opportunity(
                            symbol=symbol,
                            buy_source=buy.source,
                            sell_source=sell.source,
                            buy_price=buy_ask,
                            sell_price=sell_bid,
                            gross_percent=gross,
                            net_percent=net,
                            spread_value=sell_bid - buy_ask,
                            fiat=result_fiat,
                            market_type_buy=buy.market_type,
                            market_type_sell=sell.market_type,
                        )
                    )

        opportunities.sort(key=lambda item: item.net_percent, reverse=True)
        return opportunities


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def prepare_symbols(scanner_cfg: Dict[str, Any]) -> List[str]:
    symbols = [symbol.upper() for symbol in scanner_cfg.get("symbols", [])]

    if scanner_cfg.get("use_coincap_universe", True):
        universe = CoinCapUniverseClient().get_symbols(limit=int(scanner_cfg.get("coincap_limit", 30)))
        if universe:
            return [symbol for symbol in (symbols or universe) if symbol in set(universe)]

    return symbols


def run_once(config: Dict[str, Any]) -> List[Opportunity]:
    scanner_cfg = config["scanner"]
    symbols = prepare_symbols(scanner_cfg)

    cex_quotes = CEXCollector(
        exchange_ids=scanner_cfg.get("cex_exchanges", ["mexc", "bybit", "bitget"]),
        quote_asset=scanner_cfg.get("quote_asset", "USDT"),
        min_quote_volume=float(scanner_cfg.get("min_quote_volume", 0)),
    ).collect(symbols)

    dex_quotes: List[Quote] = []
    if scanner_cfg.get("enable_dex", True):
        dex_quotes = DexScreenerCollector(
            quote_assets=scanner_cfg.get("dex_quote_assets", ["USDT", "USDC"]),
            min_liquidity_usd=float(scanner_cfg.get("dex_min_liquidity_usd", 0)),
        ).collect(symbols)

    p2p_quotes: List[Quote] = []
    if scanner_cfg.get("enable_p2p_rub", True):
        p2p_quotes = BybitP2PCollector().collect_rub(
            base_symbols=scanner_cfg.get("p2p_symbols", ["USDT", "BTC", "ETH"]),
            amount_rub=int(scanner_cfg.get("p2p_amount_rub", 30000)),
            size=int(scanner_cfg.get("p2p_page_size", 20)),
        )

    quotes = cex_quotes + dex_quotes + p2p_quotes
    logger.info("Собрано котировок: %s", len(quotes))

    engine = ArbitrageEngine(
        taker_fee_percent=float(scanner_cfg.get("taker_fee_percent", 0.1)),
        slippage_percent=float(scanner_cfg.get("slippage_percent", 0.2)),
        min_profit_percent=float(scanner_cfg.get("min_profit_percent", 0.5)),
        fx_rates_to_usdt=scanner_cfg.get("fx_rates_to_usdt", {"RUB": 0.0105}),
    )
    opportunities = engine.find(quotes, allow_cross_fiat=bool(scanner_cfg.get("allow_cross_fiat", False)))

    for opportunity in opportunities[: int(scanner_cfg.get("print_top", 20))]:
        logger.info(
            "%s [%s] | buy %s %.6f -> sell %s %.6f | net=%.3f%%",
            opportunity.symbol,
            opportunity.fiat,
            opportunity.buy_source,
            opportunity.buy_price,
            opportunity.sell_source,
            opportunity.sell_price,
            opportunity.net_percent,
        )

    output_path = Path(scanner_cfg.get("output", "data/trades/opportunities_latest.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quotes_count": len(quotes),
        "opportunities": [asdict(item) for item in opportunities],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return opportunities


def main() -> None:
    parser = argparse.ArgumentParser(description="Арбитражный бот: CEX + DEX + P2P RUB")
    parser.add_argument("--config", default="config.bot.json", help="Путь к конфигу")
    parser.add_argument("--once", action="store_true", help="Один прогон")
    args = parser.parse_args()

    config = load_config(args.config)
    interval_sec = int(config.get("scanner", {}).get("interval_sec", 120))

    if args.once:
        run_once(config)
        return

    while True:
        try:
            run_once(config)
        except Exception as exc:
            logger.exception("Ошибка цикла: %s", exc)
        time.sleep(interval_sec)


if __name__ == "__main__":
    main()
