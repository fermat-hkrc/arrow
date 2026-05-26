# Full Mutation Score Report

**Overall Score:** 60.1%

**Summary:**
- Total mutants: 752
- Killed: 452
- Survived: 300
- Timeout: 0
- Error: 0
- Tested: 752
- Runtime: 5481.14s (~91 min)

## Per-Target Breakdown

| Target | Score | Killed | Survived | Tested |
|--------|-------|--------|----------|--------|
| Arrow.clone | 100.0% | 1 | 0 | 1 |
| Arrow.is_between | 100.0% | 27 | 0 | 27 |
| Arrow.replace | 100.0% | 33 | 0 | 33 |
| Arrow.shift | 100.0% | 45 | 0 | 45 |
| Arrow.span | 100.0% | 92 | 0 | 92 |
| util.is_timestamp | 100.0% | 6 | 0 | 6 |
| Arrow.ceil | 75.0% | 3 | 1 | 4 |
| Arrow.floor | 75.0% | 3 | 1 | 4 |
| util.iso_to_gregorian | 79.1% | 34 | 9 | 43 |
| Arrow.to | 71.9% | 23 | 9 | 32 |
| util.validate_bounds | 73.3% | 11 | 4 | 15 |
| util.validate_ordinal | 62.5% | 5 | 3 | 8 |
| util.normalize_timestamp | 60.0% | 6 | 4 | 10 |
| util.next_weekday | 63.2% | 12 | 7 | 19 |
| Arrow.format | 41.7% | 5 | 7 | 12 |
| Arrow.humanize | 36.6% | 146 | 253 | 399 |
| arrow.get | 0.0% | 0 | 2 | 2 |

## Targets with Perfect Coverage (100%)

- `Arrow.clone` (1 mutant)
- `Arrow.is_between` (27 mutants)
- `Arrow.replace` (33 mutants)
- `Arrow.shift` (45 mutants)
- `Arrow.span` (92 mutants)
- `util.is_timestamp` (6 mutants)

## Weakest Targets (Highest Survivor Count)

1. **Arrow.humanize** — 36.6% (253 survivors out of 399)
2. **Arrow.format** — 41.7% (7 survivors out of 12)
3. **arrow.get** — 0.0% (2 survivors out of 2)
4. **util.iso_to_gregorian** — 79.1% (9 survivors out of 43)
5. **Arrow.to** — 71.9% (9 survivors out of 32)

## Notes

- Baseline suite verified clean before scoring (99 tests passed)
- Strategy overflow bugs fixed: `iso_week_date` and `arrow_objects` year capped at 9998
- Mutants generated for 17 out of 26 target functions
- 9 targets had zero or minimal mutants: `Arrow.fromordinal`, `Arrow.utcfromtimestamp`, `Arrow.fromdatetime`, `Arrow.fromdate`, `Arrow.strptime`, `Arrow.timestamp`, `Arrow.toordinal`, `Arrow.isocalendar`, `Arrow.utcoffset`
