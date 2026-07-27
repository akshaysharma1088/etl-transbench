"""Executable legacy oracle for t7b_multi_reason_collect.
Collect-all validation: every failing rule contributes its code, pipe-joined
in rule order. R3 is NULL-safe (skipped when amount or tax is NULL)."""
import pandas as pd

def run(inputs):
    df = inputs["invoices"].copy()
    def reasons(r):
        out = []
        if pd.isna(r["amount"]) or r["amount"] < 0:
            out.append("AMT_BAD")
        if pd.isna(r["tax"]) or r["tax"] < 0:
            out.append("TAX_BAD")
        if not pd.isna(r["amount"]) and not pd.isna(r["tax"]) and r["tax"] > r["amount"] * 0.5:
            out.append("TAX_EXCESS")
        if pd.isna(r["due_date"]):
            out.append("DUE_NULL")
        if pd.isna(r["customer_ref"]) or str(r["customer_ref"]).strip() == "":
            out.append("REF_EMPTY")
        return "|".join(out) if out else None
    df["reason_codes"] = df.apply(reasons, axis=1)
    clean = df[df["reason_codes"].isna()]
    rejects = df[df["reason_codes"].notna()]
    cols = ["invoice_id", "amount", "tax", "due_date", "customer_ref"]
    return {"invoices_clean": clean[cols],
            "invoices_rejects": rejects[cols + ["reason_codes"]]}
