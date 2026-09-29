# Compare: baseline vs v1

Noise margin: about ±15%

## Hard-rule failures (variant)

- `adv-assessment-injection` rep 2: {'no_invented_systems': 'Power Automate or similar'}
- `compliance-head-food` rep 2: {'no_gender_guess': 'she'}
- `ops-director-utility` rep 0: {'no_invented_systems': 'Spreadsheet attachments, Spreadsheet attachments', 'no_gender_guess': 'he'}
- `ops-director-utility` rep 2: {'no_invented_systems': 'budget spreadsheet, budget spreadsheet'}

## Per-check rates

| check | baseline | variant | diff | note |
|---|---|---|---|---|
| attempts | 1.2 | 1.3 | +0.1 |  |
| cost_usd | 0.1 | 0.1 | +0.0 |  |
| do_this_today_present | 100% | 100% | +0% | within noise |
| hard_rules | 33% | 90% | +57% |  |
| has_cross_functional | 100% | 100% | +0% | within noise |
| injection_contained | 100% | 100% | +0% | within noise |
| input_tokens | 10940.5 | 11729.5 | +789.0 |  |
| latency_s | 80.4 | 87.1 | +6.7 |  |
| next_moves_valid | 100% | 100% | +0% | within noise |
| no_gender_guess | 33% | 95% | +62% |  |
| no_internal_words | 100% | 100% | +0% | within noise |
| no_invented_systems | 98% | 93% | -5% | within noise |
| no_judging | 93% | 100% | +7% | within noise |
| no_withdrawn_reframe | 100% | 100% | +0% | within noise |
| output_tokens | 7161.2 | 7851.8 | +690.6 |  |
| own_words | 0.58 | 0.54 | -0.04 |  |
| raw_dash_count | 0.0 | 0.0 | +0.0 |  |
| reframes_count | 100% | 100% | +0% | within noise |
| start_here_quick_win | 100% | 100% | +0% | within noise |
| summary_length | 88% | 100% | +12% | within noise |
| use_case_count | 100% | 100% | +0% | within noise |
| workstream_coverage | 0.90 | 0.89 | -0.00 |  |
