"""Executable legacy oracle for t4d_union_dedup_precedence.
Golden-record selection: source precedence FIRST (CRM beats web regardless of
recency), then updated_at DESC within source, then email ASC on exact ties."""
import pandas as pd

def run(inputs):
    crm = inputs["crm_feed"].copy(); crm["src_rank"] = 1
    web = inputs["web_feed"].copy(); web["src_rank"] = 2
    both = pd.concat([crm, web], ignore_index=True)
    both = both.sort_values(["customer_id", "src_rank", "updated_at", "email"],
                            ascending=[True, True, False, True])
    golden = both.drop_duplicates("customer_id", keep="first")
    return {"golden": golden[["customer_id", "email", "updated_at"]]}
