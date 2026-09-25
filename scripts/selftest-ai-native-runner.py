#!/usr/bin/env python3
"""End-to-end smoke test for the isolated experiment runner and scorer."""

from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]


def sh(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def main() -> int:
    spec = importlib.util.spec_from_file_location("scorer", ROOT / "scripts/score-ai-native-run.py")
    scorer_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer_module)
    root = "/tmp/narness-T15-B-01-example/worktree"
    target = "web/src/platform/session-runtime/SessionRuntime.ts"
    assert scorer_module.normalize_path(root + "/" + target, root) == target
    assert scorer_module.matches("./" + target, [target])
    assert not scorer_module.matches("../" + target, [target])
    assert not scorer_module.matches("." + target, [target])
    assert not scorer_module.matches(
        scorer_module.normalize_path(root + "-other/" + target, root), [target]
    )
    events = [{"type": "search", "results": [root + "/" + target, {"path": root + "/" + target}]}]
    scorer_module.normalize_trace_paths(events, root)
    assert events[0]["results"] == [target, {"path": target}]
    with tempfile.TemporaryDirectory(prefix="narness-runner-selftest-") as tmp:
        root = Path(tmp)
        source = root / "subject"
        source.mkdir()
        sh(["git", "init"], source)
        sh(["git", "config", "user.email", "selftest@example.invalid"], source)
        sh(["git", "config", "user.name", "Narness Selftest"], source)

        (source / "tests").mkdir()
        (source / "tests" / ".keep").write_text("", encoding="utf-8")
        (source / "README.md").write_text("baseline\n", encoding="utf-8")
        (source / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        sh(["git", "add", "."], source)
        sh(["git", "commit", "-m", "baseline"], source)
        baseline = sh(["git", "rev-parse", "HEAD"], source).stdout.strip()

        (source / ".hidden").mkdir()
        (source / ".hidden" / "smoke.txt").write_text("oracle\n", encoding="utf-8")
        sh(["git", "add", ".hidden/smoke.txt"], source)
        sh(["git", "commit", "-m", "oracle"], source)
        oracle = sh(["git", "rev-parse", "HEAD"], source).stdout.strip()

        spec = root / "spec"
        spec.mkdir()
        task = {
            "schema_version": 1,
            "task_id": "SMOKE",
            "prompt": "Create the requested smoke artifact.",
            "fixtures": {"A": {}, "B": {}, "C": {}},
            "oracle": {
                "ref": oracle,
                "files": [{
                    "source": ".hidden/smoke.txt",
                    "destination": "tests/__hidden_smoke.txt",
                }],
            },
            "acceptance_commands": [
                "test -f tests/__hidden_smoke.txt",
                "grep -q oracle tests/__hidden_smoke.txt",
                "grep -q agent-created changed.txt",
                "test ! -e node_modules/agent-poison.txt",
            ],
            "verification_commands": [
                "test ! -f tests/__hidden_smoke.txt",
                "grep -q agent-created changed.txt",
                "test ! -e node_modules/agent-poison.txt",
            ],
        }
        (spec / "task.json").write_text(json.dumps(task, indent=2) + "\n", encoding="utf-8")
        treatments = {
            "schema_version": 1,
            "treatments": {
                name: {"name": name, "sha": baseline, "agent_instruction": None}
                for name in ("A", "B", "C")
            },
        }
        (spec / "treatments.json").write_text(
            json.dumps(treatments, indent=2) + "\n",
            encoding="utf-8",
        )
        gold = {
            "schema_version": 1,
            "tasks": {
                "SMOKE": {
                    "treatments": {
                        "A": {
                            "primary": ["README.md"],
                            "relevant": [],
                            "adjacent": [],
                            "required_artifacts": ["README.md"],
                            "allowed_edit_prefixes": ["changed.txt", "new_test.txt"],
                        }
                    }
                }
            },
        }
        (spec / "gold.json").write_text(json.dumps(gold, indent=2) + "\n", encoding="utf-8")

        fake = root / "fake_agent.py"
        fake.write_text(
            """from pathlib import Path
import json, os
Path('changed.txt').write_text('agent-created\\n', encoding='utf-8')
Path('new_test.txt').write_text('new-file\\n', encoding='utf-8')
Path('node_modules').mkdir(exist_ok=True)
Path('node_modules/agent-poison.txt').write_text('must-not-propagate\\n', encoding='utf-8')
trace = Path(os.environ['NARNESS_TRACE_FILE'])
events = [
    {'type': 'read', 'ts_ms': 10, 'path': str(Path.cwd() / 'README.md')},
    {'type': 'edit', 'ts_ms': 20, 'paths': [str(Path.cwd() / 'changed.txt'), 'new_test.txt'], 'operation': 'selftest'},
    {'type': 'usage', 'ts_ms': 30, 'input_tokens': 100, 'cached_tokens': 0, 'output_tokens': 20, 'reasoning_tokens': 5},
]
trace.write_text(''.join(json.dumps(x) + '\\n' for x in events), encoding='utf-8')
""",
            encoding="utf-8",
        )

        out = root / "runs"
        runner = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "ai-native-repo-experiment.py"),
                "--source-repo", str(source),
                "--task", str(spec / "task.json"),
                "--treatments", str(spec / "treatments.json"),
                "--treatment", "A",
                "--agent-cmd", f"{sys.executable} {fake}",
                "--agent-timeout-seconds", "30",
                "--output-dir", str(out),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if runner.returncode != 0:
            print(runner.stdout)
            print(runner.stderr, file=sys.stderr)
            raise RuntimeError(f"runner selftest failed with {runner.returncode}")

        run_dir = out / "SMOKE-A-01"
        run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        assert run["task_success"] is True
        assert run["trace_present"] is True

        agent = run["commands"]["agent"]
        agent_end = agent["started_at_unix"] + agent["duration_ms"] / 1000
        installs = run["commands"]["oracle_install"]
        assert installs and installs[0]["installed_at_unix"] >= agent_end

        diff = (run_dir / "final.diff").read_text(encoding="utf-8")
        assert "changed.txt" in diff, diff
        assert "new_test.txt" in diff, diff
        assert "__hidden_smoke" not in diff, diff
        assert "agent-poison" not in diff, diff

        scorer = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "score-ai-native-run.py"),
                "--run-dir", str(run_dir),
                "--gold", str(spec / "gold.json"),
                "--treatment", "A",
                "--update-run-json",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if scorer.returncode != 0:
            print(scorer.stdout)
            print(scorer.stderr, file=sys.stderr)
            raise RuntimeError("scorer selftest failed")

        score = json.loads((run_dir / "score.json").read_text(encoding="utf-8"))
        assert score["metrics"]["primary_reads"] == 1
        assert score["metrics"]["time_to_first_relevant_artifact_ms"] == 0
        assert score["metrics"]["files_read"] == 1
        assert score["metrics"]["navigation_events_before_first_edit"] == 1
        assert score["metrics"]["files_read_before_first_edit"] == 1
        assert score["metrics"]["search_calls_before_first_edit"] == 0
        assert score["metrics"]["important_artifacts_missed_count"] == 0
        assert score["metrics"]["out_of_scope_edit_count"] == 0
        assert score["metrics"]["patch_count"] == 1
        assert score["metrics"]["first_hit_correct"] is True

        worktrees = sh(["git", "worktree", "list", "--porcelain"], source).stdout
        assert "narness-SMOKE-A-01-" not in worktrees

    print("Runner/scorer selftest OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
