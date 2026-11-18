"""Executable legacy oracle for t2g_payment_waterfall."""
import pandas as pd


def run(inputs):
    inv = inputs["invoices"].sort_values(["customer_id", "due_date", "invoice_id"]).to_dict("records")
    by_cust = {}
    for i in inv:
        i["open_amount"] = round(float(i["amount"]), 2)
        i["touched"] = False
        by_cust.setdefault(i["customer_id"], []).append(i)
    alloc, credit = [], {}
    for p in inputs["payments"].sort_values(["customer_id", "paid_ts", "payment_id"]).to_dict("records"):
        left = round(float(p["amount"]), 2)
        for i in by_cust.get(p["customer_id"], []):
            if left == 0:
                break
            if i["open_amount"] <= 0:
                continue
            pay = min(left, i["open_amount"])
            i["open_amount"] = round(i["open_amount"] - pay, 2)
            i["touched"] = True
            left = round(left - pay, 2)
            alloc.append(dict(payment_id=p["payment_id"], invoice_id=i["invoice_id"], applied_amount=pay))
        if left > 0:
            credit[p["customer_id"]] = round(credit.get(p["customer_id"], 0.0) + left, 2)
    status = [dict(invoice_id=i["invoice_id"], open_amount=i["open_amount"],
                   status="PAID" if i["open_amount"] == 0 else ("PARTIAL" if i["touched"] else "OPEN"))
              for i in inv]
    return {"invoice_status": pd.DataFrame(status, columns=["invoice_id", "open_amount", "status"]),
            "allocations": pd.DataFrame(alloc, columns=["payment_id", "invoice_id", "applied_amount"]),
            "customer_credit": pd.DataFrame([dict(customer_id=k, unapplied_amount=v) for k, v in credit.items()],
                                            columns=["customer_id", "unapplied_amount"])}
