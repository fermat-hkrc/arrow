# PBT Test Suite Comparison

## Overview

Comparing two PBT test suites for the Arrow project:
- **ccode branch** (current): `tests/test_pbt.py`
- **self-evolve branch** (new): `tests/test_pbt_arrow.py`

## Basic Metrics

| Metric | ccode (current) | self-evolve (new) | Difference |
|--------|-----------------|-------------------|------------|
| File | `test_pbt.py` | `test_pbt_arrow.py` | - |
| Lines of code | 853 | 1,277 | +424 (+49.7%) |
| Test count | 99 | 144 | +45 (+45.5%) |
| Runtime | 3.76s | 7.85s | +4.09s (+108.8%) |
| Status | ✅ 99 passed | ✅ 144 passed | - |

## Mutation Score Comparison

### ccode branch (current)
- **Overall Score:** 60.1%
- **Mutants:** 752 total (452 killed, 300 survived)
- **Runtime:** ~91 min

### self-evolve branch (new)
- **Overall Score:** TBD
- **Mutants:** TBD
- **Runtime:** TBD

## Analysis

The self-evolve suite is significantly larger:
- 45% more tests
- 50% more code
- 2x longer runtime

Next step: Run mutation scoring on self-evolve suite to measure actual effectiveness improvement.
