import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from etl_transbench.datagen import TableGen, ColumnGen, generate_corpus

TABLES = {
    "branch_scores": TableGen(
        name="branch_scores", rows=200, key_columns=["branch_id"],
        columns=[
            ColumnGen("branch_id", "int", null_rate=0.0, low=1, high=50_000),
            ColumnGen("manager", "string", null_rate=0.15, empty_rate=0.05),
            ColumnGen("branch_code", "string", null_rate=0.06),
            ColumnGen("region_code", "string", null_rate=0.06),
            ColumnGen("score", "float", null_rate=0.0, low=0, high=100),
            ColumnGen("active", "int", null_rate=0.0, low=0, high=1),
        ]),
}

def corpus(seed: int):
    """Adversarial augmentation: force a tie EXACTLY at rank 5 among active
    branches so head(5)-style translations (dropping WITH TIES) are detected,
    and force NULL branch/region codes into the top block so '+'-concat NULL
    propagation is exercised inside the returned rows."""
    import numpy as np, pandas as pd
    data = generate_corpus(TABLES, seed)
    df = data["branch_scores"]
    rng = np.random.default_rng(seed + 777)
    block = df.head(9).copy()
    block["branch_id"] = block["branch_id"] + 1_000_000
    block["active"] = 1
    # Offset +1000 guarantees these 9 rows occupy ranks 1-9 regardless of the
    # organic score distribution, pinning the three-way tie EXACTLY at rank 5.
    block["score"] = [1099.5, 1098.0, 1097.0, 1096.5, 1095.0, 1095.0, 1095.0,
                      1094.0, 1093.5]
    block.iloc[1, block.columns.get_loc("branch_code")] = None   # NULL-concat probe in top block
    data["branch_scores"] = pd.concat([df, block], ignore_index=True)
    return data
