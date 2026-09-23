import importlib.util
import pathlib
import sys
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("system_one_k8s.py")
SPEC = importlib.util.spec_from_file_location("system_one_k8s", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SystemOneKubernetesDemoTest(unittest.TestCase):
    def fixture(self):
        return pathlib.Path(__file__).with_name("fixtures") / "cluster.json"

    def test_progressive_disclosure_generates_grounded_logs_command(self):
        runtime = MODULE.SystemOneKubernetesRuntime(
            environment=MODULE.FixtureEnvironment(self.fixture()),
            decider=MODULE.OfflineFixtureDecider(),
        )

        state = runtime.run("Show me the Kubernetes logs for nession in staging.")

        self.assertEqual(MODULE.Phase.DONE, state.phase)
        self.assertEqual("staging", state.selected_namespace)
        self.assertEqual(
            [
                "kubectl",
                "-n",
                "staging",
                "logs",
                "nession-staging-7d4c6d9d7f-k8m2p",
            ],
            state.final_command,
        )
        self.assertEqual(
            [
                "discover.namespaces",
                "namespace:staging",
                "discover.pods:staging",
                "logs:nession-staging-7d4c6d9d7f-k8m2p",
            ],
            [decision.action_id for decision in state.decisions],
        )

    def test_multi_container_target_renders_container_flag(self):
        environment = MODULE.FixtureEnvironment(self.fixture())
        state = MODULE.RuntimeState(
            goal="Show redis metrics logs in staging.",
            phase=MODULE.Phase.SELECT_LOG_TARGET,
            context=environment.current_context(),
            namespaces=environment.discover_namespaces(),
            selected_namespace="staging",
            pods=environment.discover_pods("staging"),
        )
        actions = MODULE.FrontierCompiler().compile(state)
        action = next(
            item for item in actions if item.id == "logs:redis-staging-0:metrics"
        )
        runtime = MODULE.SystemOneKubernetesRuntime(
            environment=environment,
            decider=MODULE.OfflineFixtureDecider(),
        )

        runtime._apply(state, action)

        self.assertEqual(
            [
                "kubectl",
                "-n",
                "staging",
                "logs",
                "redis-staging-0",
                "-c",
                "metrics",
            ],
            state.final_command,
        )

    def test_typesafe_request_uses_choice_over_grounded_actions(self):
        environment = MODULE.FixtureEnvironment(self.fixture())
        state = MODULE.RuntimeState(
            goal="Show me the Kubernetes logs for nession in staging.",
            phase=MODULE.Phase.SELECT_NAMESPACE,
            context=environment.current_context(),
            namespaces=environment.discover_namespaces(),
        )
        actions = MODULE.FrontierCompiler().compile(state)
        client = MODULE.TypeSafeSystemOneDecider(api_key="test-key")

        payload = client.build_request(state, actions)

        self.assertEqual("jev-latest", payload["model"])
        question = payload["questions"]["next_action"]
        self.assertEqual("choice", question["type"])
        self.assertEqual(
            {action.id for action in actions},
            set(question["criteria"].keys()),
        )
        self.assertEqual(
            ["default", "kube-system", "monitoring", "staging"],
            payload["state"]["kubernetes"]["discovered_namespaces"],
        )


if __name__ == "__main__":
    unittest.main()
