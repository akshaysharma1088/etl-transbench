"""Executable legacy oracle for t3e_effective_lookup_route.
Normalise the key, pick the price valid on the order date (latest valid_from,
then lowest list_id), default to 0 with a flag, route by ordered rules, then
aggregate by route and day."""
import pandas as pd


def _norm(s):
    return None if pd.isna(s) else str(s).strip().upper()


def run(inputs):
    orders = inputs["orders"].copy()
    prices = inputs["price_list"].copy()
    prices["sku_norm"] = prices["sku"].map(_norm)
    by_sku = {k: g.sort_values(["valid_from", "list_id"], ascending=[False, True])
              for k, g in prices.dropna(subset=["sku_norm"]).groupby("sku_norm")}
    rows = []
    for o in orders.to_dict("records"):
        sku = _norm(o["sku"])
        price, flag = 0.0, "NO_PRICE"
        if sku is not None and sku in by_sku:
            ok = by_sku[sku][by_sku[sku]["valid_from"] <= o["order_date"]]
            if len(ok):
                price, flag = float(ok.iloc[0]["unit_price"]), "OK"
        qty = o["qty"]
        ext = None if pd.isna(qty) else float(qty) * price
        if flag == "NO_PRICE" or pd.isna(qty) or qty >= 100:
            route = "REVIEW"
        elif ext >= 1000:
            route = "BULK"
        elif ext < 50:
            route = "SMALL"
        else:
            route = "STANDARD"
        rows.append(dict(order_id=o["order_id"], sku_norm=sku, unit_price=price, route=route,
                         order_date=o["order_date"], ext_amount=ext))
    df = pd.DataFrame(rows)
    df["ext_amount"] = df["ext_amount"].astype(float)
    daily = (df.groupby(["route", "order_date"], as_index=False)
               .agg(order_count=("order_id", "size"), total_ext=("ext_amount", lambda s: float(s.sum(skipna=True)))))
    return {"order_enriched": df[["order_id", "sku_norm", "unit_price", "route"]],
            "route_daily": daily[["route", "order_date", "order_count", "total_ext"]]}
