# Canonical N=61 Reproducibility Audit

Date: 2026-06-07

Mode: READ ONLY / research audit

Verdict: `CANONICAL_N61_REPRODUCIBLE_WITH_RUNLESS_DEDUP_KEY`

## Objective

Prove that the ETH YES FC OS canonical opportunity count of `n = 61` can be reproduced deterministically from raw source data.

Primary source:

- `runtime/quant_data/trade_journal/*.jsonl`

Cross-check source:

- `runtime/research_exports/completed_trades_v1_2.csv`

No runtime code, strategy, risk, execution, configuration, replay, commit, or push was changed.

## Canonical Filter Contract

Raw source events are joined as:

```text
trade_open -> trade_close
join key = (run_id, paper_trade_replay_key)
```

The canonical ETH YES FC OS predicate is:

```text
event_type == trade_close
AND outcome truth exists
AND asset == ETH
AND side/outcome == YES
AND trade_open.lifecycle_phase contains OPENING_SCAN
AND hold_seconds > 15
```

`FIRST_CYCLE` is operationalized by `OPENING_SCAN` in the current evidence export path. The completed-trades export has no separate `FIRST_CYCLE` or `time_bucket` column, and the current command-center predicate defines this watchlist through `canonical_entry_lifecycle_phase contains OPENING_SCAN`.

Canonical duplicate removal uses the logical opportunity key:

```text
condition_id | epoch_start_ts | asset | side | candidate_id
```

`run_id` is intentionally excluded from the canonical opportunity key. Including `run_id` counts repeated runtime execution rows, not unique logical opportunities.

## Filter Chain

| Step | Count |
|---|---:|
| Raw `trade_close` rows | 1223 |
| Outcome-truth valid rows | 1223 |
| ETH rows with outcome truth | 360 |
| ETH YES rows with outcome truth | 148 |
| ETH YES with `OPENING_SCAN` entry lifecycle | 119 |
| ETH YES OPENING_SCAN with `hold_seconds > 15` | 62 |
| Duplicate logical opportunities removed | 1 |
| Canonical unique opportunities | 61 |

## Duplicate Removal

One duplicate runtime execution row is removed by the canonical runless logical opportunity key:

```text
0xb50b55a177d8aa82b1d52cfb4c37cb029bf3742ceccfeb1686ebff0ede26c0fd|1779967500|ETH|YES|candidate_b6eb567d95f1
```

Duplicate rows:

| run_id | close_ts | hold_seconds | result | pnl |
|---|---:|---:|---|---:|
| `20260528T112210Z_29912_e98efd38` | 2026-05-28T11:26:02 | 49 | TP | 0.005656799999999995 |
| `20260528T110330Z_21492_318145bc` | 2026-05-28T11:26:12 | 55 | TP | 0.01004399 |

Canonical treatment: retain one logical opportunity. The retained row choice does not change `n`; this audit displays the earliest close timestamp for the duplicate key.

## Exact Canonical Opportunity Keys

| # | canonical_key | retained_run_id | close_ts | hold_seconds | result | pnl | note |
|---:|---|---|---:|---:|---|---:|---|
| 1 | `0x081e13efad6a9a42e5b8662aa48a66872ba4abf923f356d62a95331ff952a9f1|1779343800|ETH|YES|candidate_250ccf1da544` | 20260521T044143Z_13704_948b4757 | 2026-05-21T06:11:06 | 35 | TP | 0.010494999999999997 |  |
| 2 | `0x0a795808d22d67539967798b0cf73bfa82717a2d630ead520067339a4433da07|1779339600|ETH|YES|candidate_1405a6066924` | 20260521T044143Z_13704_948b4757 | 2026-05-21T05:00:29 | 16 | SL | -0.00719684 |  |
| 3 | `0x131998f7bf2843adb2ff0b9327c957f37405cc21e26887c98f494b56bcb835c1|1779630300|ETH|YES|candidate_9fe06079fb62` | 20260524T134430Z_22940_add0ad1f | 2026-05-24T13:45:35 | 23 | SL | -0.01205952 |  |
| 4 | `0x166c4f5fa4ce04a81ef7ad6e87b212bc138e567c7b44d43ea49e0dd5defc40b2|1779714600|ETH|YES|candidate_eee7fdba5147` | 20260525T113528Z_21600_bca4f41e | 2026-05-25T13:10:38 | 32 | SL | -0.004933799999999999 |  |
| 5 | `0x185920a5428ad1bfa49d1ea2f46a393372885562fa07c1a84ec74efed8a61c25|1780120800|ETH|YES|candidate_9255f6a1d677` | 20260530T055938Z_23248_c29b456d | 2026-05-30T06:00:44 | 18 | SL | -0.012322830000000005 |  |
| 6 | `0x1bef39b05bdefd34ef2a1be7b66c69a034b49858303bd33efcc8b221cf67ea83|1779272400|ETH|YES|candidate_db6e78e5d1ac` | 20260520T090540Z_45508_dc23e716 | 2026-05-20T10:21:01 | 44 | TP | 0.016427609999999992 |  |
| 7 | `0x1ccabf0810d59460a52cdad468c252bc53cfd47997f70288e580cd493c8deec5|1780723200|ETH|YES|candidate_9ed8765c0bc1` | 20260606T041414Z_23488_8bde4b5d | 2026-06-06T05:20:47 | 23 | TP | 0.01160556 |  |
| 8 | `0x2d501c25d51db265e9302665ee5a1f2d063cf0228061014f430279be183e410b|1779604800|ETH|YES|candidate_8da2e3088d0a` | 20260524T052743Z_26444_0defea84 | 2026-05-24T06:41:28 | 74 | TP | 0.016430839999999995 |  |
| 9 | `0x314ee6c38b22828717e0dbf4f1e9725465b10280b99fcc1a1faaec24a8c75d1c|1779502800|ETH|YES|candidate_16a4ebf3e9cb` | 20260523T015426Z_16036_ac5d7312 | 2026-05-23T02:20:54 | 19 | SL | -0.009473400000000003 |  |
| 10 | `0x3475d387c94a4b043b17570fca9de3ac270095aca2d7cf05c49c16b6815b4eb7|1779338100|ETH|YES|candidate_15110d2097e9` | 20260521T042630Z_28120_45581845 | 2026-05-21T04:35:35 | 24 | SL | -0.004832700000000005 |  |
| 11 | `0x3585d13f2559aa7762b589834f2d19054fc708e7f5e2504fd89295cc03b7398b|1779184200|ETH|YES|candidate_29d1d4490d34` | 20260519T053224Z_28944_25443b98 | 2026-05-19T09:51:10 | 56 | TP | 0.008985399999999998 |  |
| 12 | `0x394ddcf9fcb8371ff23f595010d1904dbb833047ae1a0f2ac00ed508ead695c2|1779955500|ETH|YES|candidate_ab312fd98634` | 20260528T074009Z_38660_884a713e | 2026-05-28T08:05:43 | 18 | SL | -0.004191919999999998 |  |
| 13 | `0x3a2a9d5f4fd6c20008e7883b1aae0c9b31416629c0d2d36819f6a4404f91f456|1779198900|ETH|YES|candidate_570e6124615a` | 20260519T053224Z_28944_25443b98 | 2026-05-19T13:55:45 | 30 | SL | -0.010627319999999994 |  |
| 14 | `0x3c9c9686c3ba244129121832cdbbd0e28833ea2256c9ce6e26da55f591221149|1780135200|ETH|YES|candidate_a57180c84dd9` | 20260530T055938Z_23248_c29b456d | 2026-05-30T10:01:15 | 65 | TP | 0.005683799999999994 |  |
| 15 | `0x4a6c25e8b385c5b14500c475402a1c868990acb61d9470e2641eea2963bfebfc|1779332100|ETH|YES|candidate_6d4c375901cc` | 20260521T024408Z_14048_1b6a20bd | 2026-05-21T02:56:52 | 99 | SL | -0.004254849999999995 |  |
| 16 | `0x521ddc9489850ec14a350ad55ea1247f66db508ecf6c23d3cbb4f48138455e67|1780137000|ETH|YES|candidate_1fb337b92d9c` | 20260530T055938Z_23248_c29b456d | 2026-05-30T10:30:47 | 25 | TP | 0.008505299999999999 |  |
| 17 | `0x528466d867e7554f208535134528f962a51f0a3d892f51c19f7b2715b64e2cf9|1779471300|ETH|YES|candidate_c96dd9368b45` | 20260522T163940Z_15384_a58a5171 | 2026-05-22T17:35:56 | 30 | SL | -0.006707359999999996 |  |
| 18 | `0x53b8c79f5accc52f745bfabd8cc3d054b823c11235a9ac04f5998829aefd5b2f|1779201300|ETH|YES|candidate_20839048322a` | 20260519T053224Z_28944_25443b98 | 2026-05-19T14:35:39 | 32 | TP | 0.009249899999999998 |  |
| 19 | `0x53f83da4754c3b0b74295486190173ce4b35e57b057e10aaabfd7d389e39ac13|1779342600|ETH|YES|candidate_b755a4075d6b` | 20260521T044143Z_13704_948b4757 | 2026-05-21T05:50:49 | 36 | TP | 0.006184710000000006 |  |
| 20 | `0x56ebbdceb56458b40a9415bff3d3d244dddd87c39c8a4585c5d88bd14f3d6a07|1779289200|ETH|YES|candidate_1eeb567ae042` | 20260520T110715Z_30452_d6c09eac | 2026-05-20T15:00:44 | 24 | TP | 0.00672414 |  |
| 21 | `0x660ffe40cfb1b56b71212c48577d417e67f0125d0a32bd06b3bf50d62c1ebd64|1779344100|ETH|YES|candidate_bf9d104c8471` | 20260521T044143Z_13704_948b4757 | 2026-05-21T06:16:09 | 56 |  | -0.004582000000000004 |  |
| 22 | `0x668987b6614368d1abfee0ca9f3e8bf956d62d905eab425531944b16ade84036|1779377400|ETH|YES|candidate_304504be14bf` | 20260521T133858Z_45768_ed644582 | 2026-05-21T15:30:44 | 28 | SL | -0.005585580000000005 |  |
| 23 | `0x66bab9a0a44812516d39cbf4849ae224f5076e3842b3ef356aa10f394a84a9af|1779468600|ETH|YES|candidate_d86bc5144e87` | 20260522T163940Z_15384_a58a5171 | 2026-05-22T16:50:29 | 20 | TP | 0.007664940000000007 |  |
| 24 | `0x680fc162ab7e4c78bbc4ad3bd715a71441c1b46a7b3359859a3f149d8d56eb4a|1779692400|ETH|YES|candidate_b32be7994bcf` | 20260525T065423Z_53560_1b672958 | 2026-05-25T07:01:00 | 25 | TP | 0.0051291000000000045 |  |
| 25 | `0x6d6a3c5eb4a3ca405f01835c422aa994ec0fbebef02a5bf130517e39efa96f79|1779276900|ETH|YES|candidate_27407cb09991` | 20260520T110715Z_30452_d6c09eac | 2026-05-20T11:35:43 | 35 | TP | 0.01188837 |  |
| 26 | `0x6efdb242b408a7c38a809b4818da8c4164a2a93d184afa312ae27a2e73be6b62|1780229400|ETH|YES|candidate_6760ec8ebd65` | 20260531T110056Z_28744_80855716 | 2026-05-31T12:10:35 | 23 | TP | 0.01307124 |  |
| 27 | `0x721236979dae57d6361e208b3516e44347c3afdc87384e97e7c689d45677e2a6|1779600000|ETH|YES|candidate_732928108a52` | 20260524T045213Z_24036_f64d2821 | 2026-05-24T05:20:32 | 22 | TP | 0.005958890000000005 |  |
| 28 | `0x774fd0aa28329052b808057a99e940b682237d86da1b7749395c42df6e529eb4|1780095300|ETH|YES|candidate_a6881184290d` | 20260529T182158Z_18828_54ecfed9 | 2026-05-29T22:55:47 | 42 | TP | 0.008690700000000008 |  |
| 29 | `0x7cd3ce5f24b825dffa52af6450384be36f095a3b6e5522854defd5cddb2ff1a8|1780096800|ETH|YES|candidate_c8e467526063` | 20260529T182158Z_18828_54ecfed9 | 2026-05-29T23:20:38 | 23 | TP | 0.0058831500000000045 |  |
| 30 | `0x82d0965d26f8f6840a472f728956d69ead03ef174554f0a4e2922adb0bb4152d|1779282300|ETH|YES|candidate_53018ad58611` | 20260520T110715Z_30452_d6c09eac | 2026-05-20T13:05:26 | 20 | TP | 0.007904799999999995 |  |
| 31 | `0x82e6a779851677cb3deedced67126a2243b733720e23a0e7c078f2a4f01fcdd5|1779536700|ETH|YES|candidate_7713773a4dc0` | 20260523T114026Z_28096_d5341765 | 2026-05-23T11:45:26 | 18 | SL | -0.00703472 |  |
| 32 | `0x8ad4972066e826a8ae1d1ef1553cbfd948b5f3a8a07c54daa5fd0894221b6712|1779763200|ETH|YES|candidate_1abd396f6c25` | 20260526T023631Z_8772_d867429c | 2026-05-26T02:40:36 | 28 | TP | 0.016427269999999994 |  |
| 33 | `0x8da24244ba50789e2794e75ab6abf926d4a714671ac1f1fa36824a4034428b68|1779277500|ETH|YES|candidate_896bca7d165f` | 20260520T110715Z_30452_d6c09eac | 2026-05-20T11:45:33 | 17 | SL | -0.00592116 |  |
| 34 | `0x91561e27bc26b611370d47df887f8feb00d0f6b8285ce9fa9a26510e57175a0f|1779598200|ETH|YES|candidate_43d3ca758a91` | 20260524T043315Z_29264_52c95bee | 2026-05-24T04:51:29 | 77 | TP | 0.027139860000000002 |  |
| 35 | `0x92ee216d2a1bcd4075efbc687f231073a223accce320767ea4b4a93216aa9afa|1779428700|ETH|YES|candidate_a6b002e14975` | 20260522T052610Z_31032_cfe7068f | 2026-05-22T05:46:23 | 78 | TP | 0.008551709999999997 |  |
| 36 | `0x95c24472dc537c430287d2e511612e943e7aeb11d30704519cb8fce2152829dc|1779439500|ETH|YES|candidate_94954c79a1de` | 20260522T075658Z_26740_b69f35b9 | 2026-05-22T08:45:41 | 23 | TP | 0.007187679999999996 |  |
| 37 | `0x9dcf7eebb96a5472aa41ff104863eca3f399f4cc7b3eafdaecb1ec522cc1e79e|1779421200|ETH|YES|candidate_c53d489c0ff4` | 20260521T133858Z_45768_ed644582 | 2026-05-22T03:40:32 | 16 | SL | -0.008224020000000002 |  |
| 38 | `0xa0282bcc24cd5b8aaa739a0de53cd915d01ab15c7b9682246219bb79ea4b699b|1779966600|ETH|YES|candidate_1fafd590b5a7` | 20260528T110330Z_21492_318145bc | 2026-05-28T11:10:32 | 18 | SL | -0.01105456 |  |
| 39 | `0xa4b26dd5ccf2822b4d3386c1accbc70472dfdbe3181a7ae553f9bd8af4567d23|1779713700|ETH|YES|candidate_4ebae0c662a7` | 20260525T113528Z_21600_bca4f41e | 2026-05-25T12:55:44 | 24 | TP | 0.007452719999999997 |  |
| 40 | `0xa939023f8d7b52ef28b75d1e49fd59a2daac8dc45129b7640c763d3b812d876e|1779435300|ETH|YES|candidate_d7ef4285371a` | 20260522T055830Z_13912_ef8361bc | 2026-05-22T07:35:39 | 19 | SL | -0.006767670000000001 |  |
| 41 | `0xab0ff7bb0291f3981b168ca5a55f24bad5218b2a0cfa50c5841946ed37e0a53c|1779995100|ETH|YES|candidate_f0b1b999544a` | 20260528T110330Z_21492_318145bc | 2026-05-28T19:05:56 | 37 | TP | 0.008387799999999997 |  |
| 42 | `0xab2200c20abe4757bf7b5360142f5548b06146152acc1d9709e55ce5f5c4938a|1779289800|ETH|YES|candidate_943adacaec91` | 20260520T110715Z_30452_d6c09eac | 2026-05-20T15:10:35 | 24 | SL | -0.018794420000000003 |  |
| 43 | `0xb50b55a177d8aa82b1d52cfb4c37cb029bf3742ceccfeb1686ebff0ede26c0fd|1779967500|ETH|YES|candidate_b6eb567d95f1` | 20260528T112210Z_29912_e98efd38 | 2026-05-28T11:26:02 | 49 | TP | 0.005656799999999995 | duplicate_removed |
| 44 | `0xb8a80673b7d73505934555a1629eb0251e20a39f71f7883c4873ec4ef9d8bbf1|1779601200|ETH|YES|candidate_075b777c0c32` | 20260524T052743Z_26444_0defea84 | 2026-05-24T05:40:33 | 24 | SL | -0.008377290000000003 |  |
| 45 | `0xb8f2340f3e2ca9e3fa55cbc8c23e2ad92178680581390c1d61dfb5cfa603e3b0|1779371400|ETH|YES|candidate_c7de2b5044b1` | 20260521T133858Z_45768_ed644582 | 2026-05-21T13:50:45 | 31 | TP | 0.020471439999999997 |  |
| 46 | `0xb9b22bea58b8c47e31df4bda4ed8d5479cc1c41edbb675e3a3c31549e8189503|1779348000|ETH|YES|candidate_ec88390f2668` | 20260521T044143Z_13704_948b4757 | 2026-05-21T07:20:58 | 36 | SL | -0.0056047800000000045 |  |
| 47 | `0xc70faa13207d540d052102fe6812942ca585f5370f0c032fa6d937ac34b71c08|1779339300|ETH|YES|candidate_162645be5929` | 20260521T044143Z_13704_948b4757 | 2026-05-21T04:55:33 | 21 | TP | 0.028838679999999995 |  |
| 48 | `0xc74376ce6c1010270df94ba2a87dbc48aada1bda3c80969e03e04852a69bfbbf|1779437400|ETH|YES|candidate_02bfffe29249` | 20260522T075658Z_26740_b69f35b9 | 2026-05-22T08:10:36 | 22 | TP | 0.008203759999999996 |  |
| 49 | `0xc8428694d26d5a6660b8436a2a05712b1a940285412fb3e79fce6bb21853df11|1779443700|ETH|YES|candidate_8a84a927bd0b` | 20260522T094222Z_46088_040fac20 | 2026-05-22T09:55:54 | 38 | TP | 0.005477099999999995 |  |
| 50 | `0xd166f4fb7daa2125e95dfdcaaa1e0a3afb9150969db4990c102b82b4d5093358|1779720900|ETH|YES|candidate_db1647c6ab17` | 20260525T145417Z_52872_1761df0e | 2026-05-25T14:55:34 | 16 | SL | -0.009212169999999999 |  |
| 51 | `0xd296c53ea7083f835c09ceacfc536e2b6d5d1992913fd8d71a61b5603cbd5fc1|1780080600|ETH|YES|candidate_a0aab076783c` | 20260529T182158Z_18828_54ecfed9 | 2026-05-29T18:50:33 | 19 | TP | 0.0075959199999999965 |  |
| 52 | `0xd484eca17725eb5e6518e14ea5a23dcd093e07a9122d3f969cac95891cc1a068|1779605700|ETH|YES|candidate_a7c64bef5830` | 20260524T052743Z_26444_0defea84 | 2026-05-24T06:55:49 | 37 | SL | -0.004473600000000004 |  |
| 53 | `0xdb74793a0046886fb8b5c5ad685ca92690e1f9871b5c6d414e31785cfea70edd|1779688800|ETH|YES|candidate_f9735cb2bd1c` | 20260525T053039Z_48048_63481f2f | 2026-05-25T06:00:52 | 35 | TP | 0.012124280000000001 |  |
| 54 | `0xde1da56fb06926ffb4b9f89601a1230c498f9cf39089285f738fd65f50edd19d|1779710100|ETH|YES|candidate_c576c03e8735` | 20260525T113528Z_21600_bca4f41e | 2026-05-25T11:56:05 | 48 | TP | 0.009309399999999997 |  |
| 55 | `0xe2b455550d8dcab9ce66b4891f31a06382a563854e0608f8886fa1d48edb4c52|1779601800|ETH|YES|candidate_efccc77cdfb0` | 20260524T052743Z_26444_0defea84 | 2026-05-24T05:50:36 | 24 | SL | -0.005200559999999996 |  |
| 56 | `0xe62c510c6713ce0b286f1d5175d0652ad32a1d8b5716df14144da48faea3b89a|1779279900|ETH|YES|candidate_1e58f8b415b3` | 20260520T110715Z_30452_d6c09eac | 2026-05-20T12:25:35 | 22 | TP | 0.02132 |  |
| 57 | `0xf65ecef83c47b5d01f61f50c8f4e16f1d970af0237d588b146dd284d2048be8b|1779078900|ETH|YES|candidate_d65f3cb121e9` | 20260518T041552Z_12476_ae4fa786 | 2026-05-18T04:35:25 | 17 | TP | 0.006643559999999995 |  |
| 58 | `0xf7d54af4679c909133ed0c52db973fb6a6a392cbbfc20e4238b8244dfd7f5edc|1779797400|ETH|YES|candidate_8fab8d9c37cf` | 20260526T120255Z_19460_52b2e66e | 2026-05-26T12:11:08 | 53 | TP | 0.021201619999999997 |  |
| 59 | `0xf7f52e55bc392d7a56e8af99211010c797c2f3fc0f92a1951efc350a3bba8d49|1780225500|ETH|YES|candidate_fb9ca03441f2` | 20260531T110056Z_28744_80855716 | 2026-05-31T11:05:48 | 31 | SL | -0.004101879999999998 |  |
| 60 | `0xfafdc30531a1da19f631335393ecfc1087f7e0f5e7b9b6a593056a92eb94457d|1779763500|ETH|YES|candidate_4b3cd53801bf` | 20260526T023631Z_8772_d867429c | 2026-05-26T02:45:31 | 25 | SL | -0.004926749999999999 |  |
| 61 | `0xfdea93a7bb7e60746540efbf55ab85a3abfe6e7b2da3426a4ef6a6c2c2662eb6|1779190800|ETH|YES|candidate_2f42e066b00b` | 20260519T053224Z_28944_25443b98 | 2026-05-19T11:40:46 | 30 | SL | -0.004846650000000004 |  |

## CSV Cross-Check

`runtime/research_exports/completed_trades_v1_2.csv` reproduces the same visible watchlist row count when filtered by:

```text
asset == ETH
AND side == YES
AND canonical_entry_lifecycle_phase contains OPENING_SCAN
AND hold_seconds > 15
```

CSV result:

| Check | Count |
|---|---:|
| Filtered CSV rows | 61 |
| Unique CSV replay/token keys | 60 |

The CSV is useful as a compact cross-check, but raw JSONL is the authoritative reproducibility source because it carries `candidate_id` for the canonical opportunity key and exposes the duplicate runtime execution row explicitly.

## Reproducibility Caveats

The count changes if a different key contract is used:

| Key contract | Interpretation | Result |
|---|---|---:|
| `(run_id, condition_id, epoch_start_ts, asset, side, candidate_id)` | Raw execution rows across runtime runs | 62 |
| `(condition_id, epoch_start_ts, asset, side, candidate_id)` | Canonical logical opportunities | 61 |
| CSV replay/token key only | Compact export de-dupe; lacks `candidate_id` | 60 |

The canonical governance count must therefore use the runless logical opportunity key:

```text
condition_id | epoch_start_ts | asset | side | candidate_id
```

## Governor Verdict

Canonical `n = 61` is reproducible from raw source data.

The evidence chain is deterministic:

```text
1223 raw trade_close rows
-> 1223 outcome-truth valid rows
-> 360 ETH rows
-> 148 ETH YES rows
-> 119 ETH YES OPENING_SCAN rows
-> 62 ETH YES OPENING_SCAN rows with hold_seconds > 15
-> 61 canonical logical opportunities after one duplicate removal
```

No code changes, commits, runtime mutations, strategy changes, risk changes, or execution changes were made.
