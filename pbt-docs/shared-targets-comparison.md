# Fair Comparison: Shared Targets Only

## Overview

Both PBT suites tested on the **11 targets they have in common**.

## Overall Score (Shared Targets Only)

| Suite | Score | Killed | Tested | Mutants |
|-------|-------|--------|--------|---------|
| **ccode** | **51.6%** | 309 | 599 | 599 |
| **self-evolve** | **30.4%** | 182 | 598 | 598 |
| **Difference** | **+21.2pp** | +127 | +1 | +1 |

**ccode is 70% more effective** at killing mutants on shared targets (51.6% vs 30.4%).

## Per-Target Comparison (Shared Targets)

| Target | ccode | self-evolve | Δ | Winner |
|--------|-------|-------------|---|--------|
| **Arrow.replace** | 100.0% (33/33) | 21.2% (7/33) | **+78.8pp** | 🏆 ccode |
| **Arrow.shift** | 100.0% (45/45) | 77.8% (35/45) | **+22.2pp** | 🏆 ccode |
| **util.is_timestamp** | 100.0% (6/6) | 83.3% (5/6) | **+16.7pp** | 🏆 ccode |
| **util.iso_to_gregorian** | 79.1% (34/43) | 27.9% (12/43) | **+51.2pp** | 🏆 ccode |
| **util.next_weekday** | 63.2% (12/19) | 50.0% (9/18) | **+13.2pp** | 🏆 ccode |
| **util.validate_ordinal** | 62.5% (5/8) | 25.0% (2/8) | **+37.5pp** | 🏆 ccode |
| **Arrow.humanize** | 36.6% (146/399) | 21.1% (84/399) | **+15.5pp** | 🏆 ccode |
| **Arrow.format** | 41.7% (5/12) | 41.7% (5/12) | **0pp** | 🤝 Tie |
| **Arrow.to** | 71.9% (23/32) | 71.9% (23/32) | **0pp** | 🤝 Tie |
| **arrow.get** | 0.0% (0/2) | 0.0% (0/2) | **0pp** | ❌ Both fail |
| **Arrow.fromdatetime** | N/A | N/A | - | (no mutants generated) |

## Summary

- **ccode wins on 7/10 targets** (excluding Arrow.fromdatetime with no mutants)
- **Tie on 2/10 targets** (Arrow.format, Arrow.to)
- **Both fail on 1/10 targets** (arrow.get)
- **Average improvement: +21.2pp** overall

## Key Insights

### Biggest ccode advantages:
1. **Arrow.replace**: +78.8pp (100% vs 21.2%)
2. **util.iso_to_gregorian**: +51.2pp (79.1% vs 27.9%)
3. **util.validate_ordinal**: +37.5pp (62.5% vs 25.0%)

### Where they're equal:
- **Arrow.format**: Both at 41.7%
- **Arrow.to**: Both at 71.9%

### Where both struggle:
- **arrow.get**: Both at 0% (2 mutants survived in both)
- **Arrow.humanize**: Both weak (36.6% vs 21.1%), but ccode still better

## Conclusion

Even when testing the **exact same functions**, ccode's PBT tests are significantly more effective at catching bugs. The 45% more tests in self-evolve don't translate to better mutation coverage — in fact, they perform worse on nearly every shared target.

**Recommendation:** Stick with ccode suite. Self-evolve offers no advantage even on targets it does test.
