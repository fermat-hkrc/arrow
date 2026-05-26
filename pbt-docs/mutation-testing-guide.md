# Mutation Testing Guide

## What is Mutation Testing?

Mutation testing evaluates test quality by introducing bugs (mutants) into your code and checking if your tests catch them.

**Key principle:** If you break the code and tests still pass, you have a gap in test coverage.

## How Mutants Are Generated

### 1. Source Code Parsing

mutmut parses Python source files into an Abstract Syntax Tree (AST) and identifies mutation points:

```python
def shift(self, check_imaginary: bool = True, **kwargs):
    if not kwargs:
        return self.clone()
    relative_kwargs = {}
    for key, value in kwargs.items():
        if key in ["weeks", "quarters"]:
            relative_kwargs[key + "s"] = value
```

### 2. Mutation Operators Applied

mutmut applies systematic transformations to create mutants:

| Operator | Original | Mutant | Example |
|----------|----------|--------|---------|
| **Boolean flip** | `True` | `False` | `check_imaginary: bool = True` → `False` |
| **Number change** | `1` | `0`, `2` | `value + 1` → `value + 0` |
| **Comparison flip** | `==` | `!=`, `<`, `>` | `if x == 5` → `if x != 5` |
| **Logical flip** | `and` | `or` | `if a and b` → `if a or b` |
| **Return value** | `return x` | `return None` | `return self.clone()` → `return None` |
| **String change** | `"weeks"` | `"XXweeksXX"` | `key in ["weeks"]` → `key in ["XXweeksXX"]` |
| **Remove statement** | `x = 1` | `pass` | Remove assignments |
| **Arithmetic flip** | `+` | `-`, `*`, `/` | `value + 1` → `value - 1` |
| **Condition flip** | `if not x:` | `if x:` | Negate conditions |

### 3. Generation Process

```bash
# Generate all possible mutants for target functions
python3 run_mutmut_bruteforce.py generate
```

This command:
1. Identifies target files (`arrow/api.py`, `arrow/arrow.py`, `arrow/util.py`)
2. Runs mutmut to create mutants for every mutation point
3. Filters to only keep mutants in target functions (defined in `TARGET_IDS`)
4. Stores mutants in `mutants/` directory with metadata

**Example output:**
```
arrow/arrow.py
arrow/util.py
arrow/api.py
generated mutants
```

### 4. Target Function Filtering

We only generate mutants for specific functions defined in `TARGET_IDS`:

```python
TARGET_IDS = {
    "Arrow.shift",
    "Arrow.replace",
    "Arrow.is_between",
    "util.is_timestamp",
    "util.iso_to_gregorian",
    # ... etc (26 targets total)
}
```

**Generate for a single target:**
```bash
python3 run_mutmut_bruteforce.py generate --target Arrow.shift
```

**Generate with limits:**
```bash
# Limit total mutants
python3 run_mutmut_bruteforce.py generate --max-mutants 100

# Limit mutants per target
python3 run_mutmut_bruteforce.py generate --max-mutants-per-target 10
```

### 5. Example Mutants for Arrow.shift

For `Arrow.shift` with 45 mutants generated, examples include:

**Mutant 1: Boolean default flip**
```python
# Original
def shift(self, check_imaginary: bool = True, **kwargs):

# Mutant
def shift(self, check_imaginary: bool = False, **kwargs):
```

**Mutant 2: Condition negation**
```python
# Original
if not kwargs:
    return self.clone()

# Mutant
if kwargs:
    return self.clone()
```

**Mutant 3: Return value change**
```python
# Original
return self.clone()

# Mutant
return None
```

**Mutant 4: Arithmetic operator**
```python
# Original
value + 1

# Mutant
value - 1
```

**Mutant 5: String mutation**
```python
# Original
if key in ["weeks", "quarters"]:

# Mutant
if key in ["XXweeksXX", "quarters"]:
```

## Scoring Mutants

### 6. Testing Each Mutant

```bash
# Test all mutants with 120s timeout per mutant
python3 run_mutmut_bruteforce.py score --timeout 120
```

For each mutant:
1. **Apply mutant** to source file (e.g., `arrow/arrow.py`)
2. **Run test suite** (`pytest tests/test_pbt.py -q -x -o addopts=`)
3. **Check result:**
   - Exit code 0 → **survived** (bug not caught ❌)
   - Exit code ≠ 0 → **killed** (test failed, bug caught ✅)
   - Timeout → **timeout** (infinite loop)
   - Exception → **error** (test infrastructure issue)
4. **Restore original** source file
5. Repeat for next mutant

### 7. Example Mutant Lifecycle

**Original code:**
```python
def shift(self, check_imaginary: bool = True, **kwargs):
    if not kwargs:
        return self.clone()
```

**Mutant 1:** `check_imaginary = False`
```python
def shift(self, check_imaginary: bool = False, **kwargs):  # ← mutated
    if not kwargs:
        return self.clone()
```
- Run tests → `test_shift_imaginary_time_raises` fails
- Result: **killed** ✅

**Mutant 2:** `if kwargs:` (flipped condition)
```python
def shift(self, check_imaginary: bool = True, **kwargs):
    if kwargs:  # ← mutated (was "if not kwargs")
        return self.clone()
```
- Run tests → `test_shift_zero_seconds_is_identity` fails
- Result: **killed** ✅

**Mutant 3:** `return None`
```python
def shift(self, check_imaginary: bool = True, **kwargs):
    if not kwargs:
        return None  # ← mutated (was "return self.clone()")
```
- Run tests → all pass (no test checks return value!)
- Result: **survived** ❌ (gap in tests!)

### 8. Understanding Results

**Mutation Score Formula:**
```
Mutation Score = (Killed Mutants / Tested Mutants) × 100%

where Tested = Killed + Survived + Timeout
(Errors are excluded from denominator)
```

**Example results:**

| Target | Killed | Survived | Tested | Score |
|--------|--------|----------|--------|-------|
| Arrow.shift | 45 | 0 | 45 | 100% ✅ |
| Arrow.replace | 33 | 0 | 33 | 100% ✅ |
| Arrow.humanize | 146 | 253 | 399 | 36.6% ⚠️ |
| arrow.get | 0 | 2 | 2 | 0% ❌ |

### 9. What Survived Mutants Mean

A **survived mutant** indicates a gap in test coverage:

**Example:** If this mutant survives:
```python
# Mutant: return None instead of return self.clone()
def shift(self, check_imaginary: bool = True, **kwargs):
    if not kwargs:
        return None  # ← Bug introduced
```

It means **no test verifies:**
```python
result = arrow.shift()  # with no args
assert result is not None  # ← Missing assertion
assert isinstance(result, Arrow)  # ← Missing assertion
assert result == arrow  # ← Missing assertion
```

**To kill this mutant, add a test:**
```python
@given(arrow_objects())
def test_shift_no_args_returns_clone(arw):
    """shift() with no arguments returns a clone."""
    result = arw.shift()
    assert result is not None
    assert isinstance(result, Arrow)
    assert result == arw
    assert result is not arw  # different object
```

## Interpreting Mutation Scores

### High Score (>80%)
- Strong test coverage
- Tests catch most bugs
- Example: `Arrow.shift` at 100%

### Medium Score (50-80%)
- Decent coverage with gaps
- Some edge cases missed
- Example: `util.iso_to_gregorian` at 79.1%

### Low Score (<50%)
- Significant gaps in testing
- Many bugs would go undetected
- Example: `Arrow.humanize` at 36.6%

### Zero Score (0%)
- Critical gap: no effective tests
- All mutants survive
- Example: `arrow.get` at 0%

## Best Practices

### 1. Start with Baseline Check
Always verify tests pass before scoring:
```bash
pytest tests/test_pbt.py -q -o addopts=
```

Our runner does this automatically via `check_baseline()`.

### 2. Generate Incrementally
Don't generate all mutants at once for large codebases:
```bash
# Test one target first
python3 run_mutmut_bruteforce.py generate --target Arrow.shift
python3 run_mutmut_bruteforce.py score --timeout 120

# Then expand
python3 run_mutmut_bruteforce.py generate --max-mutants-per-target 10
```

### 3. Analyze Survivors
Focus on survived mutants to improve tests:
```bash
# Show a specific mutant
python3 -m mutmut show arrow.arrow.xǁArrowǁshift__mutmut_3

# Apply it manually to debug
python3 -m mutmut apply arrow.arrow.xǁArrowǁshift__mutmut_3
pytest tests/test_pbt.py -v
git checkout arrow/arrow.py  # restore
```

### 4. Set Reasonable Timeouts
- Fast functions: 30-60s
- Complex functions: 120-300s
- Avoid infinite loops eating resources

### 5. Track Progress
Store results in version control:
```bash
git add pbt-docs/mutmut-pbt-mutation-results.json
git add pbt-docs/mutmut-pbt-mutation-score.md
git commit -m "docs: mutation score 60.1%"
```

## Common Pitfalls

### 1. Broken Baseline
If baseline tests fail, every mutant looks "killed":
```
Baseline suite failed — fix tests before scoring.
```
**Fix:** Ensure `pytest tests/test_pbt.py` passes first.

### 2. Equivalent Mutants
Some mutants are semantically equivalent to the original:
```python
# Original
if x > 0:
    return True
return False

# Mutant (equivalent)
if x >= 1:  # Same for integers
    return True
return False
```
These will survive but aren't real gaps. Manual review needed.

### 3. Timeout vs. Killed
A timeout means the mutant caused an infinite loop, which is good (bug caught), but it's expensive. Consider it "killed" for practical purposes.

### 4. Over-optimization
Don't aim for 100% on every target. Some mutants are:
- Equivalent mutants
- Defensive code that's hard to trigger
- Edge cases with diminishing returns

Aim for 70-80% as a practical target.

## Our Results

### Full Project Score
- **Overall:** 60.1% (452/752 killed)
- **Runtime:** ~91 minutes
- **Targets tested:** 17/26

### Best Performers (100%)
- Arrow.clone (1/1)
- Arrow.is_between (27/27)
- Arrow.replace (33/33)
- Arrow.shift (45/45)
- Arrow.span (92/92)
- util.is_timestamp (6/6)

### Weakest Performers
- arrow.get: 0% (0/2)
- Arrow.humanize: 36.6% (146/399)
- Arrow.format: 41.7% (5/12)

## Tools and Commands Reference

### Generate Mutants
```bash
# All targets
python3 run_mutmut_bruteforce.py generate

# Single target
python3 run_mutmut_bruteforce.py generate --target Arrow.shift

# With limits
python3 run_mutmut_bruteforce.py generate --max-mutants 100
python3 run_mutmut_bruteforce.py generate --max-mutants-per-target 10
```

### Score Mutants
```bash
# Score all
python3 run_mutmut_bruteforce.py score --timeout 120

# Score with limit
python3 run_mutmut_bruteforce.py score --timeout 120 --limit 50
```

### Inspect Mutants
```bash
# Show mutant diff
python3 -m mutmut show <mutant_name>

# Apply mutant
python3 -m mutmut apply <mutant_name>

# Restore original
git checkout <file>
```

### Check Results
```bash
# View summary
cat pbt-docs/mutmut-pbt-mutation-score.md

# View full results
cat pbt-docs/mutmut-pbt-mutation-results.json
```

## Further Reading

- [mutmut documentation](https://mutmut.readthedocs.io/)
- [Mutation Testing Wikipedia](https://en.wikipedia.org/wiki/Mutation_testing)
- Our results: `pbt-docs/mutation-score-full.md`
