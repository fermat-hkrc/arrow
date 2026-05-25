from pathlib import Path
import json
import subprocess
import sys

import pytest

from run_mutmut_bruteforce import TARGET_IDS, Mutant, MutationResult, MutationSummary, check_baseline, discover_mutants, filter_mutants_to_targets, generate_mutants, limit_mutants_in_metadata, limit_mutants_per_target_in_metadata, limit_mutants_to_target_in_metadata, mutant_function_key, normalize_target_id, pytest_command, run_pytest_suite, score_mutants, source_files_for_targets, summarize_results, write_results


def test_target_allowlist_contains_expected_top_level_ids():
    assert "util.is_timestamp" in TARGET_IDS
    assert "Arrow.shift" in TARGET_IDS
    assert "arrow.get" in TARGET_IDS
    assert "Arrow.week" not in TARGET_IDS


def test_source_files_for_targets_returns_only_expected_modules():
    assert source_files_for_targets() == [
        Path("arrow/api.py"),
        Path("arrow/arrow.py"),
        Path("arrow/util.py"),
    ]


def test_normalize_target_id_uses_source_path_context():
    assert normalize_target_id(Path("arrow/util.py"), "is_timestamp") == "util.is_timestamp"
    assert normalize_target_id(Path("arrow/arrow.py"), "shift") == "Arrow.shift"
    assert normalize_target_id(Path("arrow/api.py"), "get") == "arrow.get"


def test_filter_mutants_to_targets_keeps_only_allowlisted_function_bodies():
    mutants = [
        Mutant(name="shift__mutmut_1", source_path=Path("arrow/arrow.py")),
        Mutant(name="week__mutmut_1", source_path=Path("arrow/arrow.py")),
        Mutant(name="is_timestamp__mutmut_1", source_path=Path("arrow/util.py")),
    ]

    kept, skipped = filter_mutants_to_targets(mutants)

    assert [m.name for m in kept] == ["shift__mutmut_1", "is_timestamp__mutmut_1"]
    assert [m.name for m in skipped] == ["week__mutmut_1"]


def test_discover_mutants_reads_meta_files(tmp_path: Path):
    meta = tmp_path / "arrow" / "util.py.meta"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({"exit_code_by_key": {"is_timestamp__mutmut_1": 1}}))

    mutants = discover_mutants(tmp_path)

    assert mutants == [
        Mutant(name="is_timestamp__mutmut_1", source_path=Path("arrow/util.py"))
    ]


def test_mutant_function_key_handles_actual_mutmut_name_shapes():
    assert mutant_function_key("arrow.util.x_is_timestamp__mutmut_1") == "is_timestamp"
    assert mutant_function_key("arrow.api.x_get__mutmut_1") == "get"
    assert mutant_function_key("arrow.arrow.xǁArrowǁ_shift__mutmut_1") == "shift"


def test_limit_mutants_in_metadata_keeps_only_first_n_retained(tmp_path: Path):
    util_meta = tmp_path / "arrow" / "util.py.meta"
    util_meta.parent.mkdir(parents=True)
    util_meta.write_text(json.dumps({
        "exit_code_by_key": {
            "arrow.util.x_is_timestamp__mutmut_1": 1,
            "arrow.util.x_is_timestamp__mutmut_2": 1,
            "arrow.util.x_validate_bounds__mutmut_1": 1,
        }
    }))
    arrow_meta = tmp_path / "arrow" / "arrow.py.meta"
    arrow_meta.write_text(json.dumps({
        "exit_code_by_key": {
            "arrow.arrow.xǁArrowǁ_shift__mutmut_1": 1,
        }
    }))

    kept = limit_mutants_in_metadata(tmp_path, max_mutants=2)

    assert kept == [
        "arrow.arrow.xǁArrowǁ_shift__mutmut_1",
        "arrow.util.x_is_timestamp__mutmut_1",
    ]
    util_payload = json.loads(util_meta.read_text())
    arrow_payload = json.loads(arrow_meta.read_text())
    assert sorted(util_payload["exit_code_by_key"].keys()) == [
        "arrow.util.x_is_timestamp__mutmut_1",
    ]
    assert sorted(arrow_payload["exit_code_by_key"].keys()) == [
        "arrow.arrow.xǁArrowǁ_shift__mutmut_1",
    ]


def test_limit_mutants_to_target_in_metadata_keeps_only_one_target(tmp_path: Path):
    util_meta = tmp_path / "arrow" / "util.py.meta"
    util_meta.parent.mkdir(parents=True)
    util_meta.write_text(json.dumps({
        "exit_code_by_key": {
            "arrow.util.x_is_timestamp__mutmut_1": 1,
            "arrow.util.x_validate_bounds__mutmut_1": 1,
        }
    }))
    arrow_meta = tmp_path / "arrow" / "arrow.py.meta"
    arrow_meta.write_text(json.dumps({
        "exit_code_by_key": {
            "arrow.arrow.xǁArrowǁ_shift__mutmut_1": 1,
            "arrow.arrow.xǁArrowǁ_shift__mutmut_2": 1,
            "arrow.arrow.xǁArrowǁ_format__mutmut_1": 1,
        }
    }))

    kept = limit_mutants_to_target_in_metadata(tmp_path, target_id="Arrow.shift")

    assert kept == [
        "arrow.arrow.xǁArrowǁ_shift__mutmut_1",
        "arrow.arrow.xǁArrowǁ_shift__mutmut_2",
    ]
    util_payload = json.loads(util_meta.read_text())
    arrow_payload = json.loads(arrow_meta.read_text())
    assert util_payload["exit_code_by_key"] == {}
    assert sorted(arrow_payload["exit_code_by_key"].keys()) == [
        "arrow.arrow.xǁArrowǁ_shift__mutmut_1",
        "arrow.arrow.xǁArrowǁ_shift__mutmut_2",
    ]



def test_check_baseline_raises_when_suite_fails(monkeypatch):
    monkeypatch.setattr("run_mutmut_bruteforce.run_pytest_suite", lambda timeout_seconds: ("killed", 1.0, "FAILED"))
    with pytest.raises(SystemExit, match="Baseline"):
        check_baseline()


def test_check_baseline_passes_when_suite_green(monkeypatch):
    monkeypatch.setattr("run_mutmut_bruteforce.run_pytest_suite", lambda timeout_seconds: ("survived", 1.0, "passed"))
    check_baseline()  # must not raise
    results = [
        MutationResult("a", Path("arrow/util.py"), "killed", 1.0),
        MutationResult("b", Path("arrow/util.py"), "survived", 1.0),
        MutationResult("c", Path("arrow/util.py"), "timeout", 1.0),
        MutationResult("d", Path("arrow/util.py"), "error", 1.0),
    ]

    summary = summarize_results(results)

    assert summary.killed == 1
    assert summary.survived == 1
    assert summary.timeout == 1
    assert summary.error == 1
    assert summary.tested == 3
    assert summary.mutation_score == pytest.approx(100.0 / 3.0)


def test_pytest_command_disables_repo_addopts():
    assert pytest_command() == [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_pbt.py",
        "-q",
        "-x",
        "-o",
        "addopts=",
    ]


def test_run_pytest_suite_marks_zero_exit_as_survived(monkeypatch):
    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    status, _, detail = run_pytest_suite(timeout_seconds=5)

    assert status == "survived"
    assert "ok" in detail


def test_score_mutants_restores_file_after_each_mutant(monkeypatch, tmp_path: Path):
    source = tmp_path / "arrow" / "util.py"
    source.parent.mkdir(parents=True)
    source.write_text("original\n")
    mutants_dir = tmp_path / "mutants"
    meta = mutants_dir / "arrow" / "util.py.meta"
    meta.parent.mkdir(parents=True)
    meta.write_text(json.dumps({"exit_code_by_key": {"is_timestamp__mutmut_1": 1}}))

    monkeypatch.setattr("run_mutmut_bruteforce.apply_mutant", lambda name: source.write_text("mutated\n"))
    monkeypatch.setattr("run_mutmut_bruteforce.run_pytest_suite", lambda timeout_seconds: ("killed", 0.1, "failed"))
    monkeypatch.setattr("run_mutmut_bruteforce.check_baseline", lambda: None)

    results, summary = score_mutants(mutants_dir=mutants_dir, timeout_seconds=5, project_root=tmp_path)

    assert source.read_text() == "original\n"
    assert len(results) == 1
    assert summary.killed == 1





def test_generate_mutants_patches_paths_to_mutate(monkeypatch, tmp_path: Path):
    class FakeConfig:
        def __init__(self):
            self.paths_to_mutate = []
            self.also_copy = []

    class FakeModule:
        def __init__(self):
            self.loaded = False
            self.config = FakeConfig()
            self.copy_called = False
            self.create_called = False

        def load_config(self):
            return self.config

        def ensure_config_loaded(self):
            self.loaded = True
            self.config = self.load_config()

        def copy_src_dir(self):
            self.copy_called = True

        def create_mutants(self, workers):
            self.create_called = True
            return None

    fake = FakeModule()
    monkeypatch.setattr("run_mutmut_bruteforce.MUTANTS_DIR", tmp_path / "mutants")
    monkeypatch.setattr("run_mutmut_bruteforce.source_files_for_targets", lambda target_ids=None: [Path("arrow/util.py")])
    monkeypatch.setattr("run_mutmut_bruteforce._mutmut_main", lambda: fake)

    generate_mutants()

    assert fake.loaded is True
    assert fake.copy_called is True
    assert fake.create_called is True
    assert fake.config.paths_to_mutate == [Path("arrow/util.py")]


def test_generate_mutants_applies_max_mutants_limit(monkeypatch, tmp_path: Path):
    class FakeConfig:
        def __init__(self):
            self.paths_to_mutate = []
            self.also_copy = []

    class FakeModule:
        def __init__(self):
            self.config = FakeConfig()

        def load_config(self):
            return self.config

        def ensure_config_loaded(self):
            self.config = self.load_config()

        def copy_src_dir(self):
            return None

        def create_mutants(self, workers):
            return None

    calls = []
    monkeypatch.setattr("run_mutmut_bruteforce._mutmut_main", lambda: FakeModule())
    monkeypatch.setattr("run_mutmut_bruteforce.source_files_for_targets", lambda target_ids=None: [Path("arrow/util.py")])
    monkeypatch.setattr("run_mutmut_bruteforce.limit_mutants_in_metadata", lambda mutants_dir, max_mutants: calls.append((mutants_dir, max_mutants)) or [])

    generate_mutants(mutants_dir=tmp_path / "mutants", max_mutants=3)

    assert calls == [(tmp_path / "mutants", 3)]


def test_generate_mutants_applies_target_filter(monkeypatch, tmp_path: Path):
    class FakeConfig:
        def __init__(self):
            self.paths_to_mutate = []
            self.also_copy = []

    class FakeModule:
        def __init__(self):
            self.config = FakeConfig()

        def load_config(self):
            return self.config

        def ensure_config_loaded(self):
            self.config = self.load_config()

        def copy_src_dir(self):
            return None

        def create_mutants(self, workers):
            return None

    calls = []
    monkeypatch.setattr("run_mutmut_bruteforce._mutmut_main", lambda: FakeModule())
    monkeypatch.setattr("run_mutmut_bruteforce.source_files_for_targets", lambda target_ids=None: [Path("arrow/util.py")])
    monkeypatch.setattr("run_mutmut_bruteforce.limit_mutants_to_target_in_metadata", lambda mutants_dir, target_id: calls.append((mutants_dir, target_id)) or [])

    generate_mutants(mutants_dir=tmp_path / "mutants", target_id="Arrow.shift")

    assert calls == [(tmp_path / "mutants", "Arrow.shift")]


