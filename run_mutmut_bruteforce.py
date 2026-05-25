from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


TARGET_IDS = {
    "util.is_timestamp",
    "util.validate_ordinal",
    "util.normalize_timestamp",
    "util.validate_bounds",
    "util.next_weekday",
    "util.iso_to_gregorian",
    "arrow.get",
    "Arrow.fromordinal",
    "Arrow.utcfromtimestamp",
    "Arrow.fromdatetime",
    "Arrow.fromdate",
    "Arrow.strptime",
    "Arrow.clone",
    "Arrow.shift",
    "Arrow.replace",
    "Arrow.floor",
    "Arrow.ceil",
    "Arrow.span",
    "Arrow.is_between",
    "Arrow.to",
    "Arrow.timestamp",
    "Arrow.toordinal",
    "Arrow.format",
    "Arrow.humanize",
    "Arrow.isocalendar",
    "Arrow.utcoffset",
}

MUTANTS_DIR = Path("mutants")
RESULTS_JSON = Path("pbt-docs/mutmut-pbt-mutation-results.json")
REPORT_MD = Path("pbt-docs/mutmut-pbt-mutation-score.md")
TEST_FILE = Path("tests/test_pbt.py")


@dataclass(frozen=True)
class Mutant:
    name: str
    source_path: Path


@dataclass(frozen=True)
class MutationResult:
    name: str
    source_path: Path
    status: str
    seconds: float
    detail: str = ""


@dataclass(frozen=True)
class MutationSummary:
    total: int
    killed: int
    survived: int
    timeout: int
    error: int
    tested: int
    mutation_score: float


def source_files_for_targets() -> list[Path]:
    return [Path("arrow/api.py"), Path("arrow/arrow.py"), Path("arrow/util.py")]


def mutant_function_key(mutant_name: str) -> str:
    key = mutant_name.rsplit("__mutmut_", 1)[0]
    key = key.rsplit(".", 1)[-1]
    if key.startswith("x_"):
        key = key[2:]
    if "ǁ" in key:
        key = key.split("ǁ")[-1]
    return key.strip("_")


def normalize_target_id(source_path: Path, function_key: str) -> str | None:
    if source_path == Path("arrow/util.py"):
        return f"util.{function_key}"
    if source_path == Path("arrow/arrow.py"):
        return f"Arrow.{function_key}"
    if source_path == Path("arrow/api.py") and function_key == "get":
        return "arrow.get"
    return None


def filter_mutants_to_targets(mutants: list[Mutant]) -> tuple[list[Mutant], list[Mutant]]:
    kept: list[Mutant] = []
    skipped: list[Mutant] = []
    for mutant in mutants:
        normalized = normalize_target_id(mutant.source_path, mutant_function_key(mutant.name))
        if normalized in TARGET_IDS:
            kept.append(mutant)
        else:
            skipped.append(mutant)
    return kept, skipped


def discover_mutants(mutants_dir: Path) -> list[Mutant]:
    mutants: list[Mutant] = []
    for meta_path in sorted(mutants_dir.rglob("*.py.meta")):
        data = json.loads(meta_path.read_text())
        source_path = meta_path.relative_to(mutants_dir).with_suffix("")
        for name in sorted(data.get("exit_code_by_key", {}).keys()):
            mutants.append(Mutant(name=name, source_path=source_path))
    return mutants


def _mutmut_main():
    import mutmut.__main__ as mm

    return mm


def generate_mutants(mutants_dir: Path = MUTANTS_DIR) -> None:
    mm = _mutmut_main()
    original_load_config = mm.load_config
    source_files = source_files_for_targets()

    def patched_load_config():
        cfg = original_load_config()
        cfg.paths_to_mutate = source_files
        cfg.also_copy = []
        return cfg

    mm.load_config = patched_load_config
    mm.ensure_config_loaded()
    mutants_dir.mkdir(parents=True, exist_ok=True)
    mm.copy_src_dir()
    mm.create_mutants(1)


def summarize_results(results: list[MutationResult]) -> MutationSummary:
    killed = sum(r.status == "killed" for r in results)
    survived = sum(r.status == "survived" for r in results)
    timeout = sum(r.status == "timeout" for r in results)
    error = sum(r.status == "error" for r in results)
    tested = killed + survived + timeout
    mutation_score = (100.0 * killed / tested) if tested else 0.0
    return MutationSummary(
        total=len(results),
        killed=killed,
        survived=survived,
        timeout=timeout,
        error=error,
        tested=tested,
        mutation_score=mutation_score,
    )


def pytest_command() -> list[str]:
    return [sys.executable, "-m", "pytest", str(TEST_FILE), "-q", "-x", "-o", "addopts="]


def run_pytest_suite(timeout_seconds: int) -> tuple[str, float, str]:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            pytest_command(),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        elapsed = time.perf_counter() - start
        detail = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
        status = "survived" if proc.returncode == 0 else "killed"
        return status, elapsed, detail
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start
        detail = ((exc.stdout or "") + "\n" + (exc.stderr or "")).strip()
        return "timeout", elapsed, detail


def apply_mutant(mutant_name: str) -> None:
    subprocess.run([sys.executable, "-m", "mutmut", "apply", mutant_name], check=True)


def score_mutants(
    mutants_dir: Path = MUTANTS_DIR,
    timeout_seconds: int = 300,
    limit: int | None = None,
    project_root: Path = Path("."),
) -> tuple[list[MutationResult], MutationSummary]:
    all_mutants = discover_mutants(mutants_dir)
    retained, _ = filter_mutants_to_targets(all_mutants)
    if limit is not None:
        retained = retained[:limit]

    results: list[MutationResult] = []
    for mutant in retained:
        source = project_root / mutant.source_path
        original = source.read_text()
        try:
            start = time.perf_counter()
            apply_mutant(mutant.name)
            status, _, detail = run_pytest_suite(timeout_seconds)
            seconds = time.perf_counter() - start
            results.append(
                MutationResult(
                    name=mutant.name,
                    source_path=mutant.source_path,
                    status=status,
                    seconds=seconds,
                    detail=detail,
                )
            )
        except Exception as exc:
            results.append(
                MutationResult(
                    name=mutant.name,
                    source_path=mutant.source_path,
                    status="error",
                    seconds=0.0,
                    detail=str(exc),
                )
            )
        finally:
            source.write_text(original)

    return results, summarize_results(results)


def write_results(results: list[MutationResult], summary: MutationSummary, output_dir: Path = Path("pbt-docs")) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / RESULTS_JSON.name).write_text(
        json.dumps(
            {
                "results": [
                    {**asdict(result), "source_path": str(result.source_path)} for result in results
                ],
                "summary": asdict(summary),
            },
            indent=2,
        )
    )

    lines = [
        "# Mutmut PBT Mutation Score",
        "",
        f"- total: {summary.total}",
        f"- killed: {summary.killed}",
        f"- survived: {summary.survived}",
        f"- timeout: {summary.timeout}",
        f"- error: {summary.error}",
        f"- tested: {summary.tested}",
        f"- mutation score: {summary.mutation_score:.2f}%",
        "",
        "## Targets",
    ]
    target_counts: dict[str, int] = {}
    for result in results:
        normalized = normalize_target_id(result.source_path, mutant_function_key(result.name))
        if normalized in TARGET_IDS:
            target_counts[normalized] = target_counts.get(normalized, 0) + 1
    for target in sorted(target_counts):
        lines.append(f"- {target}: {target_counts[target]} mutant(s)")
    lines.append("")
    lines.append("## Survivors")
    survivors = [r for r in results if r.status == "survived"]
    if survivors:
        for result in survivors:
            lines.append(f"- `{result.name}` — `{result.source_path}`")
    else:
        lines.append("- none")
    (output_dir / REPORT_MD.name).write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("generate")
    score = sub.add_parser("score")
    score.add_argument("--timeout", type=int, default=300)
    score.add_argument("--limit", type=int)
    args = parser.parse_args()

    if args.command == "generate":
        generate_mutants()
        print("generated mutants")
        return

    results, summary = score_mutants(timeout_seconds=args.timeout, limit=args.limit)
    write_results(results, summary)
    print(f"score={summary.mutation_score:.2f}% tested={summary.tested} killed={summary.killed} survived={summary.survived} timeout={summary.timeout} error={summary.error}")


if __name__ == "__main__":
    main()
