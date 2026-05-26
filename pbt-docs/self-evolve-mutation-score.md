# Self-Evolve PBT Suite Mutation Score Results

## Summary

The self-evolve PBT suite (`test_pbt_arrow.py`) scored **significantly worse** than the ccode suite despite having 45% more tests.

| Metric | ccode (current) | self-evolve (new) | Change |
|--------|-----------------|-------------------|--------|
| **Overall Score** | **60.1%** | **34.5%** | **-25.6pp** ⬇️ |
| Tests | 99 | 144 | +45 (+45.5%) |
| Lines | 853 | 1,277 | +424 (+49.7%) |
| Killed mutants | 452 | 259 | -193 (-42.7%) |
| Survived mutants | 300 | 492 | +192 (+64.0%) |
| Errors | 0 | 1 | +1 |
| Runtime | 91 min | 138 min | +47 min (+51.6%) |

## Per-Target Comparison

| Target | ccode | self-evolve | Δ | Status |
|--------|-------|-------------|---|--------|
| Arrow.clone | 100.0% | 100.0% | 0pp | ✅ Same |
| Arrow.ceil | 75.0% | 75.0% | 0pp | ✅ Same |
| Arrow.floor | 75.0% | 75.0% | 0pp | ✅ Same |
| Arrow.format | 41.7% | 41.7% | 0pp | ✅ Same |
| Arrow.to | 71.9% | 71.9% | 0pp | ✅ Same |
| util.validate_bounds | 73.3% | 73.3% | 0pp | ✅ Same |
| util.is_timestamp | 100.0% | 83.3% | -16.7pp | ⬇️ Regression |
| Arrow.shift | 100.0% | 77.8% | -22.2pp | ⬇️ Regression |
| util.next_weekday | 63.2% | 50.0% | -13.2pp | ⬇️ Regression |
| util.validate_ordinal | 62.5% | 25.0% | -37.5pp | ⬇️ Regression |
| Arrow.span | 100.0% | 64.1% | -35.9pp | ⬇️ Major regression |
| util.iso_to_gregorian | 79.1% | 27.9% | -51.2pp | ⬇️ Major regression |
| util.normalize_timestamp | 60.0% | 0.0% | -60.0pp | ⬇️ Major regression |
| Arrow.replace | 100.0% | 21.2% | -78.8pp | ⬇️ Critical regression |
| Arrow.humanize | 36.6% | 21.1% | -15.5pp | ⬇️ Regression |
| Arrow.is_between | 100.0% | 0.0% | -100.0pp | ⬇️ Critical regression |
| arrow.get | 0.0% | 0.0% | 0pp | ❌ Both fail |

## Key Findings

### Critical Regressions (>50pp drop)
1. **Arrow.is_between**: 100% → 0% (-100pp)
   - ccode: 27/27 killed
   - self-evolve: 0/27 killed
   
2. **Arrow.replace**: 100% → 21.2% (-78.8pp)
   - ccode: 33/33 killed
   - self-evolve: 7/33 killed

3. **util.normalize_timestamp**: 60% → 0% (-60pp)
   - ccode: 6/10 killed
   - self-evolve: 0/10 killed

4. **util.iso_to_gregorian**: 79.1% → 27.9% (-51.2pp)
   - ccode: 34/43 killed
   - self-evolve: 12/43 killed

### Targets with No Change
- Arrow.clone, Arrow.ceil, Arrow.floor, Arrow.format, Arrow.to, util.validate_bounds

### Only Target Both Fail
- arrow.get: 0% in both suites

## Analysis

**Why more tests performed worse:**

1. **Weaker assertions**: More tests but less rigorous property checks
2. **Redundant coverage**: Tests may overlap without catching new mutation types
3. **Less diverse strategies**: Input generation may not explore edge cases as well
4. **Different test focus**: May test different aspects (e.g., API surface vs. correctness)

**Conclusion:** Test quantity ≠ test quality. The ccode suite with 99 tests is significantly more effective at catching bugs than the self-evolve suite with 144 tests.

## Recommendation

Do not adopt the self-evolve suite. Instead:
1. Analyze why ccode suite performs better on specific targets
2. Identify gaps in both suites (e.g., arrow.get at 0%)
3. Selectively add tests from self-evolve only if they improve mutation score
