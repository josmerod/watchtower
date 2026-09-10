"""Pure portfolio math for the Markets "💼 Mi cartera" section (T-086).

A holding is a small dict stored in the browser (localStorage via dcc.Store):

    {"coin_id": str, "symbol": str, "name": str,
     "amount": float, "avg_buy_price": float}

Everything here is pure (no Dash imports) so it is unit-testable without a
Dash app: parsing user input, merging duplicate buys at a weighted-average
price, and valuing positions against the CoinGecko snapshot the Markets tab
already loads.
"""

import math
from typing import Any


def parse_amount(value: Any) -> float | None:
    """Parse a user-entered amount; must be a finite number greater than 0."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(amount) or amount <= 0:
        return None
    return amount


def parse_price(value: Any) -> float | None:
    """Parse a buy price; must be finite and >= 0 (0 = mined/airdropped coins)."""
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(price) or price < 0:
        return None
    return price


def weighted_avg_price(old_amount: float, old_price: float, add_amount: float, add_price: float) -> float:
    """New average buy price after adding a buy to an existing position."""
    total_amount = old_amount + add_amount
    if total_amount <= 0:
        return float(add_price)
    return (old_amount * old_price + add_amount * add_price) / total_amount


def add_holding(holdings: list[dict[str, Any]], coin_id: str, symbol: str, name: str, amount: float, avg_buy_price: float) -> list[dict[str, Any]]:
    """Return a new holdings list with the buy recorded; duplicates merge by ``coin_id``.

    Re-buying an existing coin sums the amounts and sets the buy price to the
    amount-weighted average of the previous position and the new buy, so the
    cost basis stays correct without keeping lot history. The input list is
    never mutated.
    """
    merged = [dict(h) for h in holdings]
    for holding in merged:
        if holding.get("coin_id") == coin_id:
            old_amount = float(holding.get("amount") or 0)
            old_price = float(holding.get("avg_buy_price") or 0)
            holding["amount"] = old_amount + amount
            holding["avg_buy_price"] = weighted_avg_price(old_amount, old_price, amount, avg_buy_price)
            holding.setdefault("symbol", symbol)
            holding.setdefault("name", name)
            return merged
    merged.append({"coin_id": coin_id, "symbol": symbol, "name": name, "amount": amount, "avg_buy_price": avg_buy_price})
    return merged


def remove_holding(holdings: list[dict[str, Any]], coin_id: str) -> list[dict[str, Any]]:
    """Return a new holdings list without the coin; unknown ids leave it unchanged."""
    return [dict(h) for h in holdings if h.get("coin_id") != coin_id]


def normalize_holdings(data: Any) -> list[dict[str, Any]]:
    """Coerce arbitrary Store data (hand-edited localStorage) into clean holdings.

    Rows without a usable ``coin_id`` or with an invalid amount are dropped as
    meaningless; a missing/invalid ``avg_buy_price`` defaults to 0 (treated as
    costless coins) rather than destroying the row.
    """
    if not isinstance(data, list):
        return []
    holdings: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        coin_id = row.get("coin_id")
        if not coin_id or not isinstance(coin_id, str):
            continue
        amount = parse_amount(row.get("amount"))
        if amount is None:
            continue
        price = parse_price(row.get("avg_buy_price"))
        holdings.append(
            {
                "coin_id": coin_id,
                "symbol": str(row.get("symbol") or coin_id),
                "name": str(row.get("name") or coin_id),
                "amount": amount,
                "avg_buy_price": price if price is not None else 0.0,
            }
        )
    return holdings


def price_lookup(coins: list[dict[str, Any]]) -> dict[str, float]:
    """Map coin_id -> current USD price from the CoinGecko snapshot rows."""
    prices: dict[str, float] = {}
    for coin in coins or []:
        coin_id = coin.get("id")
        raw = coin.get("price_usd")
        if not coin_id or raw is None:
            continue
        try:
            price = float(raw)
        except (TypeError, ValueError):
            continue
        if math.isfinite(price):
            prices[str(coin_id)] = price
    return prices


def compute_position(holding: dict[str, Any], price: float | None) -> dict[str, Any]:
    """Value one holding at ``price``; ``price=None`` means no live quote.

    ``pl_pct`` is None when the cost basis is 0 (free coins have no meaningful
    percentage) or when there is no live price.
    """
    amount = float(holding.get("amount") or 0)
    buy_price = float(holding.get("avg_buy_price") or 0)
    cost = amount * buy_price
    if price is None:
        return {"known": False, "value_usd": None, "cost_usd": cost, "pl_usd": None, "pl_pct": None}
    value = amount * price
    pl = value - cost
    return {"known": True, "value_usd": value, "cost_usd": cost, "pl_usd": pl, "pl_pct": (pl / cost * 100) if cost > 0 else None}


def compute_totals(holdings: list[dict[str, Any]], prices: dict[str, float]) -> dict[str, Any]:
    """Aggregate value/cost/P/L over the holdings that have a live price.

    Positions without a quote are kept in ``missing_prices`` (and in
    ``positions``) but excluded from the money sums so the total P/L% stays
    honest.
    """
    total_value = 0.0
    total_cost = 0.0
    total_pl = 0.0
    missing = 0
    for holding in holdings:
        position = compute_position(holding, prices.get(str(holding.get("coin_id"))))
        if not position["known"]:
            missing += 1
            continue
        total_value += float(position["value_usd"] or 0)
        total_cost += float(position["cost_usd"] or 0)
        total_pl += float(position["pl_usd"] or 0)
    return {
        "positions": len(holdings),
        "value_usd": total_value,
        "cost_usd": total_cost,
        "pl_usd": total_pl,
        "pl_pct": (total_pl / total_cost * 100) if total_cost > 0 else None,
        "missing_prices": missing,
    }
