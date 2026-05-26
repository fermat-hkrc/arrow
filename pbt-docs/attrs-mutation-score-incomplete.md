# attrs PBT Suite Mutation Score - INCOMPLETE

## Status: Baseline Tests Failing

The self-evolve attrs PBT test suite (`tests/test_pbt_attrs.py`) has **broken baseline tests** that prevent mutation scoring.

### Broken Test

```python
def test_has_returns_true_for_attrs_class(self):
    """has() returns True for attrs-decorated classes."""
    @attrs.define
    class C:
        x: int = 1
    
    assert has(C) is True  # FAILS: has(C) returns False
```

### Issue

The `has()` function from `attr` does not recognize classes decorated with `attrs.define`. It only works with the older `@attr.s` decorator.

```python
import attrs
from attr import has

@attrs.define
class C:
    x: int = 1

print(has(C))  # False (expected True by test)
```

### Impact

- **Cannot run mutation scoring** — baseline must pass first
- **Test suite quality issue** — indicates the self-evolve agent generated tests without verifying they work
- **39 tests total**, at least 1 confirmed broken

### Attempted Mutation Generation

Before discovering the baseline failure, we generated mutants:

| Metric | Value |
|--------|-------|
| Total mutants | 145 |
| Targets covered | 20 |
| Max per target | 10 |

**Targets:**
- asdict (10), astuple (10), assoc (10), has (10)
- validators: instance_of (1), in_ (missing), optional (3), matches_re (10), lt/le/gt/ge (7 each), min_len (1), max_len (1), deep_iterable (6), deep_mapping (10)
- converters: optional (10), default_if_none (10), to_bool (10), pipe (missing)
- filters: include (7), exclude (8)

### Comparison with arrow

| Project | Suite | Tests | Status | Mutation Score |
|---------|-------|-------|--------|----------------|
| arrow | self-evolve | 144 | ✅ Pass | 34.5% |
| arrow | ccode | 99 | ✅ Pass | 60.1% |
| attrs | self-evolve | 39 | ❌ **Broken** | N/A |
| attrs | ccode | 0 | N/A | N/A |

### Conclusion

The self-evolve attrs PBT suite cannot be evaluated for mutation score because:
1. Baseline tests fail
2. Tests were not validated before being committed
3. Demonstrates poor test quality from the self-evolve agent

This reinforces the finding from arrow: **self-evolve generates more tests but with lower quality**.

### Recommendation

1. Fix the broken `has()` tests (use `@attr.s` instead of `@attrs.define`)
2. Re-run baseline validation
3. Then attempt mutation scoring
4. Or: Skip attrs and focus on arrow results which are conclusive
