# Generator coverage of each oracle

How much of each task's reference implementation (`reference.py`) the generated corpora execute.
Measured with coverage.py (statement and branch) by `experiments/oracle_coverage.py`, over the three
development corpora (seeds 11, 23, 47) and, separately, the five held-out corpora (seeds 101, 211, 307, 401, 503).
Rows is the mean number of input rows per corpus, summed over the task's input relations.

Branch coverage of vectorised dataframe code understates the cases that matter: one expression can hide
several. The planted-defect probes in `tests/` are the stronger check.

| Task | Category | Set | Statements | Statement cov. (dev) | Branches | Branch cov. (dev) | Statement cov. (held-out) | Branch cov. (held-out) | Rows |
|---|---|---|---|---|---|---|---|---|---|
| t1_dialect_qualify | T1 | core | 9 | 100% | 0 | 100% | 100% | 100% | 655 |
| t1b_oracle_decode_nvl | T1 | core | 15 | 100% | 4 | 100% | 100% | 100% | 540 |
| t1c_teradata_intdiv | T1 | core | 9 | 100% | 0 | 100% | 100% | 100% | 425 |
| t1d_tsql_top_ties | T1 | core | 13 | 100% | 2 | 100% | 100% | 100% | 209 |
| t2_cursor_balance | T2 | core | 6 | 100% | 0 | 100% | 100% | 100% | 512 |
| t2b_stmt_cycle_reset | T2 | core | 7 | 100% | 0 | 100% | 100% | 100% | 411 |
| t2c_locf_carry_forward | T2 | core | 7 | 100% | 0 | 100% | 100% | 100% | 430 |
| t2d_reject_skip_accum | T2 | core | 11 | 100% | 0 | 100% | 100% | 100% | 455 |
| t2e_overdraft_fee_cursor | T2 | confirmation | 19 | 100% | 8 | 100% | 100% | 100% | 412 |
| t2f_fifo_lot_matching | T2 | confirmation | 21 | 100% | 10 | 100% | 100% | 100% | 231 |
| t2g_payment_waterfall | T2 | confirmation | 25 | 100% | 12 | 100% | 100% | 100% | 171 |
| t3_dataflow_orders | T3 | core | 10 | 100% | 0 | 100% | 100% | 100% | 350 |
| t3b_dup_lookup_first | T3 | core | 11 | 100% | 0 | 100% | 100% | 100% | 412 |
| t3c_router_first_match | T3 | core | 10 | 100% | 0 | 100% | 100% | 100% | 284 |
| t3d_dedup_null_group | T3 | core | 6 | 100% | 0 | 100% | 100% | 100% | 410 |
| t3e_effective_lookup_route | T3 | extension | 30 | 100% | 12 | 100% | 100% | 100% | 468 |
| t4_multistep_sales | T4 | core | 8 | 100% | 0 | 100% | 100% | 100% | 830 |
| t4b_delete_reinsert | T4 | core | 9 | 100% | 0 | 100% | 100% | 100% | 775 |
| t4c_stale_snapshot | T4 | core | 8 | 100% | 0 | 100% | 100% | 100% | 277 |
| t4d_union_dedup_precedence | T4 | core | 8 | 100% | 0 | 100% | 100% | 100% | 190 |
| t5_scd2_customer | T5 | core | 24 | 96% | 10 | 90% | 96% | 90% | 163 |
| t5b_scd2_multi_batch | T5 | core | 23 | 100% | 10 | 100% | 100% | 100% | 157 |
| t5c_scd1_scd2_mixed | T5 | core | 28 | 100% | 16 | 100% | 100% | 100% | 166 |
| t5d_asof_reconstruction | T5 | core | 8 | 100% | 0 | 100% | 100% | 100% | 268 |
| t5e_scd2_late_arriving | T5 | extension | 28 | 100% | 12 | 100% | 100% | 100% | 217 |
| t5f_scd2_hash_detect | T5 | extension | 18 | 100% | 6 | 100% | 100% | 100% | 244 |
| t5g_scd2_snapshot_close | T5 | extension | 27 | 100% | 12 | 100% | 100% | 100% | 200 |
| t5h_scd2_surrogate_pit | T5 | extension | 32 | 100% | 16 | 100% | 100% | 100% | 381 |
| t5i_scd2_future_dated | T5 | confirmation | 21 | 100% | 10 | 100% | 100% | 100% | 243 |
| t6_sessionize_events | T6 | core | 8 | 100% | 0 | 100% | 100% | 100% | 435 |
| t6b_capped_session | T6 | core | 21 | 100% | 6 | 100% | 100% | 100% | 1035 |
| t6c_midnight_split | T6 | core | 10 | 100% | 0 | 100% | 100% | 100% | 464 |
| t6d_channel_interleave | T6 | core | 8 | 100% | 0 | 100% | 100% | 100% | 704 |
| t6e_session_heartbeat_logout | T6 | extension | 23 | 100% | 12 | 100% | 100% | 100% | 610 |
| t6f_cross_device_session_merge | T6 | confirmation | 19 | 100% | 8 | 100% | 100% | 100% | 403 |
| t7_reject_validation | T7 | core | 19 | 100% | 8 | 100% | 100% | 100% | 408 |
| t7b_multi_reason_collect | T7 | core | 21 | 100% | 10 | 100% | 100% | 100% | 417 |
| t7c_crossfield_reference | T7 | core | 26 | 100% | 12 | 100% | 100% | 100% | 498 |
| t7d_quarantine_threshold | T7 | core | 12 | 100% | 0 | 100% | 100% | 100% | 390 |
| t7e_shortcircuit_parse_dedupe | T7 | extension | 31 | 100% | 16 | 100% | 100% | 100% | 320 |
| t7f_running_limit_validation | T7 | confirmation | 22 | 100% | 12 | 100% | 100% | 100% | 440 |
| t8_cdc_merge | T8 | core | 16 | 100% | 6 | 83% | 100% | 83% | 218 |
| t8b_delete_reinsert_cdc | T8 | core | 18 | 94% | 8 | 88% | 94% | 88% | 96 |
| t8c_out_of_order_late | T8 | core | 12 | 100% | 2 | 100% | 100% | 100% | 166 |
| t8d_soft_delete_tombstone | T8 | core | 19 | 100% | 10 | 90% | 100% | 90% | 92 |
| t8e_cdc_ops_replay | T8 | extension | 27 | 100% | 12 | 100% | 100% | 100% | 348 |
| t8f_positions_versioned_cdc | T8 | confirmation | 28 | 100% | 12 | 100% | 100% | 100% | 249 |
| t8g_partial_update_sentinel | T8 | confirmation | 33 | 100% | 16 | 100% | 100% | 100% | 305 |
| t8h_inventory_movements | T8 | confirmation | 18 | 100% | 6 | 100% | 100% | 100% | 203 |
| t8i_snapshot_diff_changelog | T8 | confirmation | 21 | 100% | 12 | 100% | 100% | 100% | 341 |
