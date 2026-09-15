# Team Delivery Metrics Ground Truth

Generated from the deterministic synthetic dataset using seed `42`.

| Team | Work items | Blocked items | Blocked % | Avg effort ratio | Late completed | Completed |
|---|---:|---:|---:|---:|---:|---:|
| AI | 120 | 18 | 15.0 | 1.16 | 32 | 80 |
| Data | 139 | 29 | 20.9 | 1.15 | 34 | 94 |
| Platform | 105 | 12 | 11.4 | 1.10 | 21 | 73 |
| Product | 136 | 20 | 14.7 | 1.12 | 28 | 83 |

## Known-answer checks

- Highest blocker rate: Data, 20.9%
- Lowest blocker rate: Platform, 11.4%
- Highest average effort overrun: AI, 1.16x planned hours
- Lowest average effort ratio: Platform, 1.10x planned hours

These values are ground truth for agent evaluation and should not be supplied to the agent during a test run.
