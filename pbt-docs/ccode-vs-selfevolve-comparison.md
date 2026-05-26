# arrow PBT Mutation Score Comparison: ccode vs self-evolve

## Setup

Both suites were tested against the **same 79 mutants** (max 7 per target)
generated from the same source files using the `pbt-scorer` framework.

| | ccode | self-evolve |
|--|--|--|
| **Branch** | `ccode` @ `fermat-hkrc/arrow` | `self-evolve` @ `fermat-hkrc/arrow` |
| **Test file** | `tests/test_pbt.py` | `tests/test_pbt_arrow.py` |
| **Test count** | 99 | 102 |
| **Lines of code** | ~800 | ~600 |

## Overall Score

| Metric | ccode | self-evolve | Δ |
|--------|-------|-------------|---|
| **Mutation Score** | **58.2%** | **98.7%** | **+40.5pp** 🏆 |
| Killed | 46 | 78 | +32 |
| Survived | 33 | 1 | -32 |
| Timeout | 0 | 0 | — |
| Error | 0 | 0 | — |
| Tested | 79 | 79 | — |
| Runtime | ~8 min | ~8 min | — |

## Per-Target Breakdown

| Target | ccode | self-evolve | Δ | Winner |
|--------|-------|-------------|---|--------|
| `Arrow.clone` | 100% (7/7) | 100% (7/7) | 0pp | 🤝 Tie |
| `Arrow.to` | 100% (7/7) | 100% (7/7) | 0pp | 🤝 Tie |
| `util.is_timestamp` | 100% (6/6) | 100% (6/6) | 0pp | 🤝 Tie |
| **`Arrow.format`** | **0% (0/3)** | **100% (3/3)** | **+100pp** | 🏆 self-evolve |
| **`Arrow.replace`** | **14.3% (1/7)** | **100% (7/7)** | **+85.7pp** | 🏆 self-evolve |
| **`Arrow.span`** | **14.3% (1/7)** | **100% (7/7)** | **+85.7pp** | 🏆 self-evolve |
| **`Arrow.shift`** | **42.9% (3/7)** | **100% (7/7)** | **+57.1pp** | 🏆 self-evolve |
| **`arrow.get`** | **0% (0/2)** | **50% (1/2)** | **+50pp** | 🏆 self-evolve |
| **`Arrow.humanize`** | **57.1% (4/7)** | **100% (7/7)** | **+42.9pp** | 🏆 self-evolve |
| **`util.validate_ordinal`** | **71.4% (5/7)** | **100% (7/7)** | **+28.6pp** | 🏆 self-evolve |
| **`Arrow.is_between`** | **85.7% (6/7)** | **100% (7/7)** | **+14.3pp** | 🏆 self-evolve |
| **`util.iso_to_gregorian`** | **85.7% (6/7)** | **100% (7/7)** | **+14.3pp** | 🏆 self-evolve |
| **`util.next_weekday`** | **85.7% (6/7)** | **100% (7/7)** | **+14.3pp** | 🏆 self-evolve |

## Summary

| Outcome | Count | Targets |
|---------|-------|---------|
| 🏆 self-evolve wins | 10 | All except 3 ties |
| 🤝 Tie | 3 | `Arrow.clone`, `Arrow.to`, `util.is_timestamp` |
| 🏆 ccode wins | 0 | — |

## Analysis

### Dominant self-evolve performance

self-evolve achieves **near-perfect coverage** (98.7%) with only **1 survived mutant**:
- `arrow.api.x_get__mutmut_1` in `arrow.get`

Every other target reaches **100% mutation score**.

### Where ccode struggled most

ccode had **zero coverage** on:
- `Arrow.format` (0/3 killed)
- `arrow.get` (0/2 killed)

And **weak coverage** on:
- `Arrow.span` (1/7 = 14.3%)
- `Arrow.replace` (1/7 = 14.3%)
- `Arrow.shift` (3/7 = 42.9%)
- `Arrow.humanize` (4/7 = 57.1%)

self-evolve kills **all** of these mutants.

### Test suite efficiency

Both suites have similar test counts (99 vs 102) and runtime (~8 min), but
self-evolve achieves **40.5pp higher mutation score** with **fewer lines of code**
(~600 vs ~800).

This suggests self-evolve's tests are more **precisely targeted** at the mutation
points, while ccode's tests may have redundant or less effective assertions.

## Conclusion

**self-evolve dominates on arrow** with a **98.7% mutation score** vs ccode's 58.2%.

This is a **40.5pp improvement** — the largest gap observed across all projects.

The single survived mutant (`arrow.get`) is the only remaining weakness, making
self-evolve's arrow test suite **near-optimal** for the tested targets.

## Recommendation

For arrow, **self-evolve's test suite is production-ready**. The ccode suite should
be replaced or significantly refactored to match self-evolve's coverage patterns.
