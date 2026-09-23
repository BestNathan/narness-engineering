import importlib.util
import pathlib
import sys
import tempfile
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "src" / "localization_result.py"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
SPEC = importlib.util.spec_from_file_location("localization_result", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class LocalizationResultTest(unittest.TestCase):
    def test_system_one_result_groups_evidence_by_file(self):
        engine = {
            "query": "find websocket",
            "model": "jev-latest",
            "reader_states": [{
                "files": [{
                    "path": "src/client.py",
                    "phase1_score": 0.88,
                    "last_activation_score": 0.72,
                    "activation_count": 2,
                    "read_count": 2,
                    "stop_reason": "model_stop",
                }],
            }],
            "snippets": [
                {
                    "path": "src/client.py",
                    "start_line": 1,
                    "end_line": 20,
                    "score": 0.91,
                    "action_probability": 0.84,
                    "content": "1: def connect():",
                },
                {
                    "path": "src/client.py",
                    "start_line": 21,
                    "end_line": 40,
                    "score": 0.76,
                    "action_probability": 0.80,
                    "content": "21: def reconnect():",
                },
            ],
        }

        result = MODULE.build_system_one_result(engine)

        self.assertEqual("code-localization-result", result["kind"])
        self.assertEqual("system_one", result["producer"]["system"])
        self.assertEqual(1, len(result["files"]))
        self.assertEqual(
            0.91,
            result["files"][0]["confidence"]["score"],
        )
        self.assertEqual(2, len(result["files"][0]["evidence"]))
        self.assertEqual(
            "noul_relevance",
            result["files"][0]["evidence"][0]["confidence"]["type"],
        )

    def test_claude_canonical_result_materializes_evidence_content(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            src = root / "src"
            src.mkdir()
            (src / "client.py").write_text(
                "line1\nline2\nline3\n",
                encoding="utf-8",
            )
            raw = {
                "schema_version": 1,
                "kind": "code-localization-result",
                "task": "find client",
                "producer": {
                    "system": "claude_code",
                    "model": "ds",
                },
                "summary": "client implementation",
                "confidence": 0.92,
                "files": [{
                    "path": "src/client.py",
                    "role": "primary",
                    "confidence": 0.88,
                    "reason": "main implementation",
                    "evidence": [{
                        "start_line": 2,
                        "end_line": 3,
                        "confidence": 0.81,
                        "reason": "relevant logic",
                    }],
                }],
            }

            result = MODULE.normalize_claude_result(raw, root, "ds")

            self.assertEqual(
                "model_self_assessment",
                result["confidence"]["type"],
            )
            self.assertEqual(
                "2: line2\n3: line3",
                result["files"][0]["evidence"][0]["content"],
            )
            self.assertEqual(
                0.88,
                result["files"][0]["confidence"]["score"],
            )


if __name__ == "__main__":
    unittest.main()
