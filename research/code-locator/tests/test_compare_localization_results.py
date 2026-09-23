import importlib.util
import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PROJECT_ROOT / "src" / "compare_localization_results.py"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
SPEC = importlib.util.spec_from_file_location(
    "compare_localization_results",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def result(system, files):
    return {
        "schema_version": 1,
        "kind": "code-localization-result",
        "task": "same task",
        "producer": {
            "system": system,
            "model": system,
        },
        "summary": "",
        "confidence": None,
        "files": files,
    }


class CompareLocalizationResultsTest(unittest.TestCase):
    def test_symmetric_file_and_region_comparison(self):
        left = result("system_one", [{
            "path": "src/a.py",
            "role": "relevant",
            "confidence": {
                "score": 0.9,
                "label": "high",
                "type": "noul_relevance",
            },
            "reason": "evidence",
            "evidence": [{
                "start_line": 10,
                "end_line": 30,
                "confidence": {
                    "score": 0.9,
                    "label": "high",
                    "type": "noul_relevance",
                },
                "reason": "range",
                "content": "",
            }],
        }, {
            "path": "src/left.py",
            "role": "relevant",
            "confidence": None,
            "reason": "",
            "evidence": [{
                "start_line": 1,
                "end_line": 10,
                "confidence": None,
                "reason": "",
                "content": "",
            }],
        }])
        right = result("claude_code", [{
            "path": "src/a.py",
            "role": "primary",
            "confidence": {
                "score": 0.8,
                "label": "high",
                "type": "model_self_assessment",
            },
            "reason": "implementation",
            "evidence": [{
                "start_line": 20,
                "end_line": 40,
                "confidence": {
                    "score": 0.8,
                    "label": "high",
                    "type": "model_self_assessment",
                },
                "reason": "range",
                "content": "",
            }],
        }, {
            "path": "src/right.py",
            "role": "supporting",
            "confidence": None,
            "reason": "",
            "evidence": [{
                "start_line": 1,
                "end_line": 5,
                "confidence": None,
                "reason": "",
                "content": "",
            }],
        }])

        report = MODULE.compare(left, right)

        self.assertEqual(["src/a.py"], report["files"]["shared"])
        self.assertEqual(["src/left.py"], report["files"]["left_only"])
        self.assertEqual(["src/right.py"], report["files"]["right_only"])
        self.assertEqual(1 / 3, report["files"]["jaccard"])
        self.assertEqual(
            0.5,
            report["evidence"]["left_covered_by_right"]["region_overlap_rate"],
        )
        self.assertEqual(
            0.5,
            report["evidence"]["right_covered_by_left"]["region_overlap_rate"],
        )
        pair = report["files"]["confidence_pairs"][0]
        self.assertEqual(0.9, pair["left_score"])
        self.assertEqual(0.8, pair["right_score"])


if __name__ == "__main__":
    unittest.main()
