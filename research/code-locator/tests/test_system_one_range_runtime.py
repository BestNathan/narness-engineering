import importlib.util
import pathlib
import sys
import unittest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))
MODULE_PATH = SRC / "system_one_range_runtime.py"
SPEC = importlib.util.spec_from_file_location(
    "system_one_range_runtime",
    MODULE_PATH,
)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RangeActionSpaceTest(unittest.TestCase):
    def test_unread_file_gets_head_middle_tail_without_text_analysis(self):
        file_state = {
            "path": "docs/guide.md",
            "line_count": 1000,
            "coverage": [],
            "latest_range": None,
        }
        actions = MODULE.generate_file_actions(
            file_state,
            window_lines=100,
            max_jumps_per_file=2,
        )
        self.assertEqual(
            ["seed_head", "seed_middle", "seed_tail"],
            [item["navigation"] for item in actions],
        )
        self.assertEqual((1, 100), (
            actions[0]["start_line"],
            actions[0]["end_line"],
        ))

    def test_read_file_gets_expand_and_geometry_jump_actions(self):
        file_state = {
            "path": "src/large.txt",
            "line_count": 1000,
            "coverage": [[1, 100]],
            "latest_range": [1, 100],
        }
        actions = MODULE.generate_file_actions(
            file_state,
            window_lines=100,
            max_jumps_per_file=2,
        )
        by_navigation = {}
        for item in actions:
            by_navigation.setdefault(item["navigation"], []).append(item)

        self.assertNotIn("expand_before", by_navigation)
        self.assertEqual(
            (101, 200),
            (
                by_navigation["expand_after"][0]["start_line"],
                by_navigation["expand_after"][0]["end_line"],
            ),
        )
        jump = by_navigation["jump"][0]
        self.assertGreaterEqual(jump["start_line"], 101)
        self.assertLessEqual(jump["end_line"], 1000)
        self.assertTrue(
            MODULE.fully_uncovered(
                jump["start_line"],
                jump["end_line"],
                [[1, 100]],
            )
        )

    def test_dynamic_space_always_contains_stop(self):
        state = {
            "files": [{
                "path": "README.md",
                "line_count": 20,
                "coverage": [],
                "latest_range": None,
            }],
        }
        actions = MODULE.generate_action_space(
            state,
            window_lines=140,
        )
        self.assertEqual("stop_task", actions[-1]["kind"])


class SelectorTest(unittest.TestCase):
    def test_threshold_controls_parallelism(self):
        scored = [
            {"id": "a", "kind": "read_range", "score": 0.91},
            {"id": "b", "kind": "read_range", "score": 0.72},
            {"id": "c", "kind": "read_range", "score": 0.50},
            {"id": "stop_task", "kind": "stop_task", "score": 0.40},
        ]
        selected, mode = MODULE.select_actions(scored, 0.65)
        self.assertEqual(["a", "b"], [item["id"] for item in selected])
        self.assertEqual("parallel_above_threshold", mode)

    def test_no_action_above_threshold_executes_best_read(self):
        scored = [
            {"id": "a", "kind": "read_range", "score": 0.58},
            {"id": "b", "kind": "read_range", "score": 0.40},
            {"id": "stop_task", "kind": "stop_task", "score": 0.20},
        ]
        selected, mode = MODULE.select_actions(scored, 0.65)
        self.assertEqual(["a"], [item["id"] for item in selected])
        self.assertEqual("fallback_top1", mode)

    def test_stop_must_be_high_and_best(self):
        scored = [
            {"id": "read", "kind": "read_range", "score": 0.70},
            {"id": "stop_task", "kind": "stop_task", "score": 0.76},
        ]
        selected, mode = MODULE.select_actions(scored, 0.65)
        self.assertEqual(["stop_task"], [item["id"] for item in selected])
        self.assertEqual("model_stop", mode)

        scored = [
            {"id": "read", "kind": "read_range", "score": 0.83},
            {"id": "stop_task", "kind": "stop_task", "score": 0.76},
        ]
        selected, mode = MODULE.select_actions(scored, 0.65)
        self.assertEqual(["read"], [item["id"] for item in selected])
        self.assertEqual("parallel_above_threshold", mode)

    def test_low_stop_never_terminates_when_read_exists(self):
        scored = [
            {"id": "read", "kind": "read_range", "score": 0.31},
            {"id": "stop_task", "kind": "stop_task", "score": 0.29},
        ]
        selected, mode = MODULE.select_actions(scored, 0.65)
        self.assertEqual(["read"], [item["id"] for item in selected])
        self.assertEqual("fallback_top1", mode)


if __name__ == "__main__":
    unittest.main()
