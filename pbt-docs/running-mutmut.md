# Running Mutmut Against Arrow PBT

## Generate mutants

```bash
python3 run_mutmut_bruteforce.py generate
python3 run_mutmut_bruteforce.py generate --max-mutants 10
```

## Score mutants

```bash
python3 run_mutmut_bruteforce.py score
python3 run_mutmut_bruteforce.py score --limit 10
python3 run_mutmut_bruteforce.py score --timeout 120
python3 run_mutmut_bruteforce.py score --limit 5 --timeout 120
```

Artifacts:
- `pbt-docs/mutmut-pbt-mutation-results.json`
- `pbt-docs/mutmut-pbt-mutation-score.md`
