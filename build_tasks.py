"""Builds the six remaining category-exemplar tasks. Run once from repo root."""
import json
import os
import textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))


def write_task(tid, meta, artifact_name, artifact, spec, reference, generator):
    d = os.path.join(ROOT, "tasks", tid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "task.json"), "w") as f:
        json.dump(meta, f, indent=2)
    with open(os.path.join(d, artifact_name), "w") as f:
        f.write(textwrap.dedent(artifact))
    with open(os.path.join(d, "spec.json"), "w") as f:
        json.dump(spec, f, indent=2)
    with open(os.path.join(d, "reference.py"), "w") as f:
        f.write(textwrap.dedent(reference))
    with open(os.path.join(d, "generator.py"), "w") as f:
        f.write(textwrap.dedent(generator))


# ============================ T2: procedural cursor loop ====================
write_task(
    "t2_cursor_balance",
    {"id": "t2_cursor_balance", "category": "T2", "tier": 2,
     "description": "Cursor loop computing running balances and overdraft flags",
     "legacy_artifact": "legacy_artifact.txt",
     "target": "pandas (PySpark in full benchmark)"},
    "legacy_artifact.txt",
    """\
    -- Legacy stored procedure SP_RUNNING_BALANCE (abstracted).
    -- Input:  TRANSACTIONS (account_id INT, txn_seq INT, txn_date DATE, amount FLOAT)
    -- Output: ACCT_BALANCE_FLAGS (account_id, txn_seq, txn_date, amount,
    --                             running_balance FLOAT, overdraft_flag SMALLINT)
    -- BODY (cursor semantics preserved):
    --   DECLARE CURSOR c FOR SELECT * FROM TRANSACTIONS
    --       ORDER BY account_id, txn_date, txn_seq;   -- txn_seq breaks date ties
    --   prev_acct := NULL; bal := 0;
    --   FOR EACH row r IN c:
    --     IF r.account_id <> prev_acct THEN bal := 0; prev_acct := r.account_id;
    --     bal := bal + COALESCE(r.amount, 0);          -- NULL amounts add zero
    --     flag := CASE WHEN bal < 0 THEN 1 ELSE 0 END;
    --     INSERT INTO ACCT_BALANCE_FLAGS VALUES (r.*, bal, flag);
    """,
    {"task_id": "t2_cursor_balance", "relations": [{
        "name": "acct_balance_flags",
        "key_columns": ["account_id", "txn_seq"], "ordered": False,
        "columns": [{"name": "running_balance", "kind": "float", "abs_tol": 1e-6},
                    {"name": "amount", "kind": "float", "abs_tol": 1e-9}]}]},
    """\
    import pandas as pd

    def run(inputs):
        df = inputs["transactions"].sort_values(
            ["account_id", "txn_date", "txn_seq"]).copy()
        df["running_balance"] = (df["amount"].fillna(0)
                                 .groupby(df["account_id"]).cumsum())
        df["overdraft_flag"] = (df["running_balance"] < 0).astype(int)
        return {"acct_balance_flags": df[["account_id", "txn_seq", "txn_date",
                                          "amount", "running_balance",
                                          "overdraft_flag"]]}
    """,
    """\
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import numpy as np, pandas as pd
    from etl_transbench.datagen import TableGen, ColumnGen, generate_corpus

    def corpus(seed):
        rng = np.random.default_rng(seed)
        n = 500
        df = pd.DataFrame({
            "account_id": rng.integers(1, 40, n),
            "txn_seq": np.arange(1, n + 1),
            "txn_date": pd.Timestamp("2025-01-01")
                        + pd.to_timedelta(rng.integers(0, 90, n), unit="D"),
            "amount": rng.uniform(-500, 500, n),
        })
        df.loc[rng.random(n) < 0.05, "amount"] = np.nan      # NULL adds zero probe
        # date-tie injection: same account, same date, differing txn_seq
        ties = df.head(12).copy()
        ties["txn_seq"] = ties["txn_seq"] + 10_000
        ties["amount"] = -ties["amount"].abs() - 1            # forces sign flips
        return {"transactions": pd.concat([df, ties], ignore_index=True)}
    """)

# ============================ T3: dataflow graph spec =======================
write_task(
    "t3_dataflow_orders",
    {"id": "t3_dataflow_orders", "category": "T3", "tier": 1,
     "description": "Abstracted graphical dataflow: filter -> lookup -> reformat",
     "legacy_artifact": "legacy_artifact.json",
     "target": "pandas (PySpark in full benchmark)"},
    "legacy_artifact.json",
    """\
    {
      "_comment": "Vendor-neutral export of a graphical ETL component graph.",
      "graph": [
        {"id": "src", "type": "source", "relation": "orders"},
        {"id": "flt", "type": "filter", "input": "src",
         "predicate": "status == 'SHIPPED'"},
        {"id": "lkp", "type": "lookup", "input": "flt",
         "lookup_relation": "customers", "on": "customer_id",
         "select": ["region"], "on_miss": {"region": "UNKNOWN"}},
        {"id": "rfm", "type": "reformat", "input": "lkp",
         "compute": {"net_amount": "qty * unit_price * (1 - discount)"},
         "note": "NULL discount treated as 0 by legacy reformat component"},
        {"id": "out", "type": "output", "input": "rfm",
         "relation": "shipped_orders_enriched",
         "columns": ["order_id","customer_id","region","qty","unit_price","net_amount"]}
      ]
    }
    """,
    {"task_id": "t3_dataflow_orders", "relations": [{
        "name": "shipped_orders_enriched",
        "key_columns": ["order_id"], "ordered": False,
        "columns": [{"name": "net_amount", "kind": "float", "abs_tol": 1e-6},
                    {"name": "unit_price", "kind": "float", "abs_tol": 1e-9},
                    {"name": "region", "kind": "string"}]}]},
    """\
    import pandas as pd

    def run(inputs):
        o = inputs["orders"]
        c = inputs["customers"][["customer_id", "region"]]
        f = o[o["status"] == "SHIPPED"].copy()
        m = f.merge(c, on="customer_id", how="left")
        m["region"] = m["region"].fillna("UNKNOWN")          # on_miss default
        m["net_amount"] = m["qty"] * m["unit_price"] * (1 - m["discount"].fillna(0))
        cols = ["order_id", "customer_id", "region", "qty", "unit_price", "net_amount"]
        return {"shipped_orders_enriched": m[cols]}
    """,
    """\
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import numpy as np, pandas as pd

    def corpus(seed):
        rng = np.random.default_rng(seed)
        n, nc = 300, 50
        orders = pd.DataFrame({
            "order_id": np.arange(1, n + 1),
            "customer_id": rng.integers(1, nc + 15, n),       # some miss the lookup
            "status": rng.choice(["SHIPPED", "OPEN", "CANCELLED"], n, p=[.5, .3, .2]),
            "qty": rng.integers(1, 20, n),
            "unit_price": rng.uniform(1, 500, n),
            "discount": rng.uniform(0, 0.4, n),
        })
        orders.loc[rng.random(n) < 0.08, "discount"] = np.nan  # NULL-discount probe
        customers = pd.DataFrame({
            "customer_id": np.arange(1, nc + 1),
            "region": rng.choice(["NA", "EMEA", "APAC", "LATAM"], nc),
        })
        return {"orders": orders, "customers": customers}
    """)

# ============================ T4: multi-step pipeline =======================
write_task(
    "t4_multistep_sales",
    {"id": "t4_multistep_sales", "category": "T4", "tier": 2,
     "description": "Multi-step pipeline with intermediate staging and two outputs",
     "legacy_artifact": "legacy_artifact.sql",
     "target": "pandas (PySpark in full benchmark)"},
    "legacy_artifact.sql",
    """\
    -- Legacy multi-step batch job (steps share an intermediate staging table).
    -- Step 1: CREATE STG_DAILY AS
    --   SELECT store_id, sale_date, SUM(amount) AS gross, COUNT(*) AS txn_cnt
    --   FROM sales WHERE amount IS NOT NULL GROUP BY store_id, sale_date;
    -- Step 2: CREATE store_daily AS
    --   SELECT s.store_id, s.sale_date, s.gross, s.txn_cnt, d.region
    --   FROM STG_DAILY s JOIN store_dim d ON s.store_id = d.store_id;  -- INNER
    -- Step 3: CREATE region_daily AS
    --   SELECT region, sale_date, SUM(gross) AS region_gross,
    --          SUM(txn_cnt) AS region_txn_cnt
    --   FROM store_daily GROUP BY region, sale_date;
    -- Outputs: store_daily, region_daily. Stores absent from store_dim are
    -- dropped in Step 2 and therefore absent from BOTH outputs.
    """,
    {"task_id": "t4_multistep_sales", "relations": [
        {"name": "store_daily", "key_columns": ["store_id", "sale_date"],
         "columns": [{"name": "gross", "kind": "float", "abs_tol": 1e-6},
                     {"name": "sale_date", "kind": "timestamp"}]},
        {"name": "region_daily", "key_columns": ["region", "sale_date"],
         "columns": [{"name": "region_gross", "kind": "float", "abs_tol": 1e-6},
                     {"name": "sale_date", "kind": "timestamp"}]}]},
    """\
    import pandas as pd

    def run(inputs):
        s = inputs["sales"]
        d = inputs["store_dim"]
        stg = (s[s["amount"].notna()]
               .groupby(["store_id", "sale_date"], as_index=False)
               .agg(gross=("amount", "sum"), txn_cnt=("amount", "size")))
        store_daily = stg.merge(d[["store_id", "region"]], on="store_id", how="inner")
        region_daily = (store_daily
                        .groupby(["region", "sale_date"], as_index=False)
                        .agg(region_gross=("gross", "sum"),
                             region_txn_cnt=("txn_cnt", "sum")))
        return {"store_daily": store_daily[["store_id", "sale_date", "gross",
                                            "txn_cnt", "region"]],
                "region_daily": region_daily}
    """,
    """\
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import numpy as np, pandas as pd

    def corpus(seed):
        rng = np.random.default_rng(seed)
        n, ns = 800, 30
        sales = pd.DataFrame({
            "store_id": rng.integers(1, ns + 8, n),           # some stores not in dim
            "sale_date": pd.Timestamp("2025-03-01")
                         + pd.to_timedelta(rng.integers(0, 14, n), unit="D"),
            "amount": rng.uniform(5, 300, n),
        })
        sales.loc[rng.random(n) < 0.06, "amount"] = np.nan    # excluded by Step 1
        dim = pd.DataFrame({"store_id": np.arange(1, ns + 1),
                            "region": rng.choice(["NORTH","SOUTH","EAST","WEST"], ns)})
        return {"sales": sales, "store_dim": dim}
    """)

# ============================ T6: sessionization windows ====================
write_task(
    "t6_sessionize_events",
    {"id": "t6_sessionize_events", "category": "T6", "tier": 2,
     "description": "Sessionization: 30-minute inactivity gap window semantics",
     "legacy_artifact": "legacy_artifact.sql",
     "target": "pandas (PySpark in full benchmark)"},
    "legacy_artifact.sql",
    """\
    -- Legacy analytical SQL: sessionize user events.
    -- A new session starts when the gap from the previous event of the SAME
    -- user is STRICTLY GREATER than 30 minutes (gap == 30:00 stays in-session).
    -- Within a user, events are ordered by event_ts, then event_id (tiebreak).
    -- Output user_sessions: user_id, session_num (1-based per user),
    --   session_start, session_end, event_count.
    SELECT user_id,
           SUM(new_sess) OVER (PARTITION BY user_id ORDER BY event_ts, event_id
                               ROWS UNBOUNDED PRECEDING) AS session_num, ...
    FROM ( SELECT *, CASE WHEN event_ts - LAG(event_ts) OVER
                 (PARTITION BY user_id ORDER BY event_ts, event_id)
                 > INTERVAL '30' MINUTE OR LAG(event_ts) ... IS NULL
                 THEN 1 ELSE 0 END AS new_sess FROM events ) t
    GROUP BY user_id, session_num;
    """,
    {"task_id": "t6_sessionize_events", "relations": [{
        "name": "user_sessions",
        "key_columns": ["user_id", "session_num"],
        "columns": [{"name": "session_start", "kind": "timestamp"},
                    {"name": "session_end", "kind": "timestamp"}]}]},
    """\
    import pandas as pd

    def run(inputs):
        e = inputs["events"].sort_values(["user_id", "event_ts", "event_id"]).copy()
        gap = e.groupby("user_id")["event_ts"].diff()
        new_sess = gap.isna() | (gap > pd.Timedelta(minutes=30))   # STRICT >
        e["session_num"] = new_sess.groupby(e["user_id"]).cumsum().astype(int)
        out = (e.groupby(["user_id", "session_num"], as_index=False)
                 .agg(session_start=("event_ts", "min"),
                      session_end=("event_ts", "max"),
                      event_count=("event_id", "size")))
        return {"user_sessions": out}
    """,
    """\
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import numpy as np, pandas as pd

    def corpus(seed):
        rng = np.random.default_rng(seed)
        rows, eid = [], 1
        for uid in range(1, 31):
            t = pd.Timestamp("2025-05-01 08:00:00")
            for _ in range(int(rng.integers(5, 25))):
                # adversarial gaps clustered around the 30-minute boundary:
                gap_min = float(rng.choice([1, 5, 29, 30, 30, 31, 90, 240],
                                           p=[.2,.2,.1,.15,.05,.1,.1,.1]))
                t = t + pd.Timedelta(minutes=gap_min)
                rows.append(dict(user_id=uid, event_id=eid, event_ts=t))
                eid += 1
        return {"events": pd.DataFrame(rows)}
    """)

# ============================ T7: reject / error flows ======================
write_task(
    "t7_reject_validation",
    {"id": "t7_reject_validation", "category": "T7", "tier": 1,
     "description": "Validation with reject port; rule ORDER determines reason code",
     "legacy_artifact": "legacy_artifact.txt",
     "target": "pandas (PySpark in full benchmark)"},
    "legacy_artifact.txt",
    """\
    -- Legacy validate component with reject port (abstracted).
    -- Input: payments (payment_id, amount, currency, country)
    -- Rules are evaluated IN ORDER; the FIRST failing rule assigns reason_code
    -- and routes the record to the reject port (later rules are not evaluated):
    --   R1: amount IS NULL                  -> reason_code 'AMT_NULL'
    --   R2: amount <= 0                     -> reason_code 'AMT_NONPOS'
    --   R3: currency NOT IN ('USD','EUR','GBP') -> reason_code 'CCY_INVALID'
    --   R4: country IS NULL                 -> reason_code 'CTRY_NULL'
    -- Passing records flow to payments_clean with amount ROUND(amount, 2).
    -- Rejected records flow to payments_rejects with original amount + reason_code.
    """,
    {"task_id": "t7_reject_validation", "relations": [
        {"name": "payments_clean", "key_columns": ["payment_id"],
         "columns": [{"name": "amount", "kind": "float", "abs_tol": 1e-9},
                     {"name": "currency", "kind": "string"}]},
        {"name": "payments_rejects", "key_columns": ["payment_id"],
         "columns": [{"name": "amount", "kind": "float", "abs_tol": 1e-9},
                     {"name": "reason_code", "kind": "string"}]}]},
    """\
    import pandas as pd

    def run(inputs):
        p = inputs["payments"].copy()
        valid_ccy = {"USD", "EUR", "GBP"}

        def reason(r):
            if pd.isna(r["amount"]):
                return "AMT_NULL"
            if r["amount"] <= 0:
                return "AMT_NONPOS"
            if r["currency"] not in valid_ccy:
                return "CCY_INVALID"
            if pd.isna(r["country"]):
                return "CTRY_NULL"
            return None

        p["reason_code"] = p.apply(reason, axis=1)
        clean = p[p["reason_code"].isna()].copy()
        clean["amount"] = clean["amount"].round(2)
        rejects = p[p["reason_code"].notna()].copy()
        return {"payments_clean": clean[["payment_id","amount","currency","country"]],
                "payments_rejects": rejects[["payment_id","amount","currency",
                                             "country","reason_code"]]}
    """,
    """\
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import numpy as np, pandas as pd

    def corpus(seed):
        rng = np.random.default_rng(seed)
        n = 400
        p = pd.DataFrame({
            "payment_id": np.arange(1, n + 1),
            "amount": rng.uniform(-50, 500, n).round(4),
            "currency": rng.choice(["USD","EUR","GBP","JPY","XXX"], n,
                                   p=[.4,.2,.15,.15,.1]),
            "country": rng.choice(["US","DE","GB", None], n, p=[.4,.25,.25,.1]),
        })
        p.loc[rng.random(n) < 0.08, "amount"] = np.nan
        # adversarial: records failing MULTIPLE rules (probe rule precedence)
        multi = pd.DataFrame({
            "payment_id": np.arange(n + 1, n + 9),
            "amount": [np.nan, np.nan, -5.0, -1.0, 10.0, 10.0, np.nan, -2.0],
            "currency": ["XXX","USD","JPY","USD","JPY","XXX","JPY","JPY"],
            "country": [None,"US",None,"US",None,None,None,None],
        })
        return {"payments": pd.concat([p, multi], ignore_index=True)}
    """)

# ============================ T8: incremental CDC merge =====================
write_task(
    "t8_cdc_merge",
    {"id": "t8_cdc_merge", "category": "T8", "tier": 3,
     "description": "Watermarked CDC merge: latest-wins, deletes, idempotent replay",
     "legacy_artifact": "legacy_artifact.txt",
     "target": "pandas (PySpark in full benchmark)"},
    "legacy_artifact.txt",
    """\
    -- Legacy incremental loader (abstracted MERGE job).
    -- Inputs:
    --   target_snapshot (product_id, name, price, last_event_ts)
    --   cdc_events     (event_seq, event_ts, op IN ('I','U','D'),
    --                   product_id, name, price)
    --   watermark      (single row: high_ts)  -- events with event_ts <= high_ts
    --                                            were already applied: SKIP them.
    -- Semantics:
    --   1. Keep only events with event_ts > watermark.high_ts.
    --   2. Per product_id, apply the LATEST event by (event_ts, event_seq).
    --      (event_seq breaks event_ts ties deterministically.)
    --   3. op 'D' deletes the product from the snapshot; 'I'/'U' upsert
    --      name/price and set last_event_ts = event_ts.
    --   4. Products without surviving events are carried over unchanged.
    --   Output: new_snapshot (same schema as target_snapshot).
    """,
    {"task_id": "t8_cdc_merge", "relations": [{
        "name": "new_snapshot",
        "key_columns": ["product_id"],
        "columns": [{"name": "price", "kind": "float", "abs_tol": 1e-9},
                    {"name": "name", "kind": "string"},
                    {"name": "last_event_ts", "kind": "timestamp"}]}]},
    """\
    import pandas as pd

    def run(inputs):
        snap = inputs["target_snapshot"].copy()
        ev = inputs["cdc_events"].copy()
        wm = inputs["watermark"]["high_ts"].iloc[0]

        ev = ev[ev["event_ts"] > wm]                               # watermark
        ev = (ev.sort_values(["product_id", "event_ts", "event_seq"])
                .groupby("product_id", as_index=False).tail(1))    # latest wins

        snap = snap.set_index("product_id")
        for e in ev.to_dict("records"):
            pid = e["product_id"]
            if e["op"] == "D":
                if pid in snap.index:
                    snap = snap.drop(pid)
            else:
                snap.loc[pid, ["name", "price", "last_event_ts"]] = (
                    e["name"], e["price"], e["event_ts"])
        out = snap.reset_index()[["product_id", "name", "price", "last_event_ts"]]
        return {"new_snapshot": out}
    """,
    """\
    import os, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    import numpy as np, pandas as pd

    def corpus(seed):
        rng = np.random.default_rng(seed)
        np_, ne = 60, 150
        wm = pd.Timestamp("2025-04-15 00:00:00")
        snap = pd.DataFrame({
            "product_id": np.arange(1, np_ + 1),
            "name": [f"PROD_{i:03d}" for i in range(1, np_ + 1)],
            "price": rng.uniform(1, 100, np_).round(2),
            "last_event_ts": wm - pd.Timedelta(days=10),
        })
        ev = pd.DataFrame({
            "event_seq": np.arange(1, ne + 1),
            "event_ts": wm + pd.to_timedelta(rng.integers(-3*86400, 5*86400, ne),
                                             unit="s"),    # some BEFORE watermark
            "op": rng.choice(["I", "U", "D"], ne, p=[.2, .6, .2]),
            "product_id": rng.integers(1, np_ + 15, ne),    # some brand-new ids
            "name": [f"PROD_{i:03d}_NEW" for i in rng.integers(1, 999, ne)],
            "price": rng.uniform(1, 100, ne).round(2),
        })
        # adversarial: same product, IDENTICAL event_ts, differing event_seq/op
        tie_ts = wm + pd.Timedelta(days=1)
        ties = pd.DataFrame({
            "event_seq": [9001, 9002, 9003, 9004],
            "event_ts": [tie_ts] * 4,
            "op": ["U", "D", "D", "U"],
            "product_id": [1, 1, 2, 2],
            "name": ["TIE_A", "TIE_B", "TIE_C", "TIE_D"],
            "price": [11.0, 12.0, 13.0, 14.0],
        })
        return {"target_snapshot": snap,
                "cdc_events": pd.concat([ev, ties], ignore_index=True),
                "watermark": pd.DataFrame({"high_ts": [wm]})}
    """)

print("six tasks written")
