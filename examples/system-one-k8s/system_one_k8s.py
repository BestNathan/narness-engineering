#!/usr/bin/env python3
"""System One Kubernetes command generator demo.

The demo treats Kubernetes as a progressively disclosed environment. Read-only
observations expand the known state, a frontier compiler instantiates only the
actions currently grounded by that state, and TypeSafe System One chooses among
those actions. The model never emits shell text or invents Kubernetes resource
names. The final kubectl command is rendered deterministically from the selected
typed action.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


DEFAULT_TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
MAX_CHOICE_OPTIONS = 200  # Keep margin below the API's 255-option Choice limit.


class Phase(str, Enum):
    DISCOVER_NAMESPACES = "discover_namespaces"
    SELECT_NAMESPACE = "select_namespace"
    DISCOVER_PODS = "discover_pods"
    SELECT_LOG_TARGET = "select_log_target"
    DONE = "done"
    BLOCKED = "blocked"


class ActionKind(str, Enum):
    DISCOVER_NAMESPACES = "discover_namespaces"
    SELECT_NAMESPACE = "select_namespace"
    DISCOVER_PODS = "discover_pods"
    EMIT_LOGS_COMMAND = "emit_logs_command"


@dataclass(frozen=True)
class Pod:
    name: str
    phase: str
    containers: tuple[str, ...]
    labels: dict[str, str] = field(default_factory=dict)

    def to_state(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "phase": self.phase,
            "containers": list(self.containers),
            "labels": self.labels,
        }


@dataclass(frozen=True)
class Action:
    id: str
    kind: ActionKind
    description: str
    params: dict[str, str] = field(default_factory=dict)

    def to_criteria(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "description": self.description,
            "grounded_parameters": self.params,
        }


@dataclass(frozen=True)
class Decision:
    action_id: str
    source: str
    confidence: float | None = None
    probabilities: dict[str, float] | None = None
    model: str | None = None
    usage: dict[str, int] | None = None
    latency_ms: int | None = None
    request: dict[str, Any] | None = None
    response: dict[str, Any] | None = None


@dataclass
class RuntimeState:
    goal: str
    phase: Phase = Phase.DISCOVER_NAMESPACES
    context: str | None = None
    namespaces: list[str] = field(default_factory=list)
    selected_namespace: str | None = None
    pods: list[Pod] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    final_command: list[str] | None = None
    blocked_reason: str | None = None

    def to_typesafe_state(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "runtime": {
                "phase": self.phase.value,
                "policy": {
                    "model_may_generate_shell": False,
                    "model_may_invent_resources": False,
                    "discovery_is_read_only": True,
                },
            },
            "kubernetes": {
                "context": self.context,
                "discovered_namespaces": self.namespaces,
                "selected_namespace": self.selected_namespace,
                "discovered_pods": [pod.to_state() for pod in self.pods],
            },
            "recent_decisions": [
                {
                    "action_id": item.action_id,
                    "source": item.source,
                    "confidence": item.confidence,
                }
                for item in self.decisions[-5:]
            ],
        }


class Environment(Protocol):
    def current_context(self) -> str: ...

    def discover_namespaces(self) -> list[str]: ...

    def discover_pods(self, namespace: str) -> list[Pod]: ...

    def render_logs_command(
        self, namespace: str, pod: str, container: str | None
    ) -> list[str]: ...


class Decider(Protocol):
    def choose(self, state: RuntimeState, actions: list[Action]) -> Decision: ...


class KubectlEnvironment:
    """Live environment that performs only allowlisted read-only discovery."""

    def __init__(self, kubeconfig: str | None = None, context: str | None = None):
        self.kubeconfig = kubeconfig
        self.context = context

    def _prefix(self) -> list[str]:
        command = ["kubectl"]
        if self.kubeconfig:
            command.extend(["--kubeconfig", self.kubeconfig])
        if self.context:
            command.extend(["--context", self.context])
        return command

    def _run(self, args: list[str]) -> str:
        command = self._prefix() + args
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout

    def _run_json(self, args: list[str]) -> dict[str, Any]:
        return json.loads(self._run(args))

    def current_context(self) -> str:
        if self.context:
            return self.context
        return self._run(["config", "current-context"]).strip()

    def discover_namespaces(self) -> list[str]:
        payload = self._run_json(["get", "namespaces", "-o", "json"])
        return sorted(
            item["metadata"]["name"]
            for item in payload.get("items", [])
            if item.get("metadata", {}).get("name")
        )

    def discover_pods(self, namespace: str) -> list[Pod]:
        payload = self._run_json(["-n", namespace, "get", "pods", "-o", "json"])
        pods: list[Pod] = []
        for item in payload.get("items", []):
            metadata = item.get("metadata", {})
            spec = item.get("spec", {})
            status = item.get("status", {})
            name = metadata.get("name")
            if not name:
                continue
            containers = tuple(
                container["name"]
                for container in spec.get("containers", [])
                if container.get("name")
            )
            pods.append(
                Pod(
                    name=name,
                    phase=status.get("phase", "Unknown"),
                    containers=containers,
                    labels=dict(metadata.get("labels", {})),
                )
            )
        return sorted(pods, key=lambda pod: pod.name)

    def render_logs_command(
        self, namespace: str, pod: str, container: str | None
    ) -> list[str]:
        command = self._prefix() + ["-n", namespace, "logs", pod]
        if container:
            command.extend(["-c", container])
        return command


class FixtureEnvironment:
    """Deterministic environment used by the documented demo and tests."""

    def __init__(self, fixture_path: str | Path):
        self.fixture_path = Path(fixture_path)
        self.data = json.loads(self.fixture_path.read_text(encoding="utf-8"))

    def current_context(self) -> str:
        return self.data.get("current_context", "fixture-context")

    def discover_namespaces(self) -> list[str]:
        return sorted(self.data.get("namespaces", []))

    def discover_pods(self, namespace: str) -> list[Pod]:
        raw_pods = self.data.get("pods", {}).get(namespace, [])
        return sorted(
            [
                Pod(
                    name=item["name"],
                    phase=item.get("phase", "Unknown"),
                    containers=tuple(item.get("containers", [])),
                    labels=dict(item.get("labels", {})),
                )
                for item in raw_pods
            ],
            key=lambda pod: pod.name,
        )

    def render_logs_command(
        self, namespace: str, pod: str, container: str | None
    ) -> list[str]:
        command = ["kubectl", "-n", namespace, "logs", pod]
        if container:
            command.extend(["-c", container])
        return command


class FrontierCompiler:
    """Compiles a small local action frontier from already discovered state."""

    def compile(self, state: RuntimeState) -> list[Action]:
        if state.phase == Phase.DISCOVER_NAMESPACES:
            return [
                Action(
                    id="discover.namespaces",
                    kind=ActionKind.DISCOVER_NAMESPACES,
                    description=(
                        "Read the Kubernetes namespace list so later actions can be "
                        "bound to real namespace names."
                    ),
                )
            ]

        if state.phase == Phase.SELECT_NAMESPACE:
            return self._bounded(
                [
                    Action(
                        id=f"namespace:{namespace}",
                        kind=ActionKind.SELECT_NAMESPACE,
                        description=f"Use the discovered namespace {namespace!r}.",
                        params={"namespace": namespace},
                    )
                    for namespace in state.namespaces
                ],
                "namespaces",
            )

        if state.phase == Phase.DISCOVER_PODS:
            namespace = self._require(state.selected_namespace, "selected namespace")
            return [
                Action(
                    id=f"discover.pods:{namespace}",
                    kind=ActionKind.DISCOVER_PODS,
                    description=(
                        f"Read pods in discovered namespace {namespace!r} so a log "
                        "command can be bound to a real pod and container."
                    ),
                    params={"namespace": namespace},
                )
            ]

        if state.phase == Phase.SELECT_LOG_TARGET:
            namespace = self._require(state.selected_namespace, "selected namespace")
            actions: list[Action] = []
            for pod in state.pods:
                if len(pod.containers) <= 1:
                    container = pod.containers[0] if pod.containers else None
                    params = {"namespace": namespace, "pod": pod.name}
                    if container:
                        params["container"] = container
                    actions.append(
                        Action(
                            id=f"logs:{pod.name}",
                            kind=ActionKind.EMIT_LOGS_COMMAND,
                            description=(
                                f"Generate a kubectl logs command for pod {pod.name!r} "
                                f"(phase={pod.phase}, labels={pod.labels})."
                            ),
                            params=params,
                        )
                    )
                    continue

                for container in pod.containers:
                    actions.append(
                        Action(
                            id=f"logs:{pod.name}:{container}",
                            kind=ActionKind.EMIT_LOGS_COMMAND,
                            description=(
                                f"Generate a kubectl logs command for container "
                                f"{container!r} in pod {pod.name!r} "
                                f"(phase={pod.phase}, labels={pod.labels})."
                            ),
                            params={
                                "namespace": namespace,
                                "pod": pod.name,
                                "container": container,
                            },
                        )
                    )
            return self._bounded(actions, "pod/container log targets")

        return []

    @staticmethod
    def _require(value: str | None, name: str) -> str:
        if value is None:
            raise RuntimeError(f"missing {name}")
        return value

    @staticmethod
    def _bounded(actions: list[Action], label: str) -> list[Action]:
        if len(actions) > MAX_CHOICE_OPTIONS:
            raise RuntimeError(
                f"local frontier has {len(actions)} {label}, above the demo limit "
                f"of {MAX_CHOICE_OPTIONS}; add another deterministic narrowing or "
                "hierarchical discovery step before asking System One"
            )
        return actions


class TypeSafeSystemOneDecider:
    """Thin client for POST /v1/systemone using a single Choice question."""

    def __init__(
        self,
        api_key: str,
        endpoint: str = DEFAULT_TYPESAFE_URL,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 30.0,
    ):
        if not api_key:
            raise ValueError("TypeSafe API key is required")
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
        self.timeout_seconds = timeout_seconds

    def build_request(self, state: RuntimeState, actions: list[Action]) -> dict[str, Any]:
        return {
            "state": state.to_typesafe_state(),
            "model": self.model,
            "questions": {
                "next_action": {
                    "type": "choice",
                    "instructions": {
                        "question": (
                            "Which available action most directly advances the goal? "
                            "Choose only from the grounded actions. Do not invent a "
                            "namespace, pod, container, command, or parameter."
                        ),
                        "decision_policy": (
                            "Prefer the action that satisfies the user's request with "
                            "the least additional discovery."
                        ),
                    },
                    "criteria": {
                        action.id: action.to_criteria() for action in actions
                    },
                }
            },
        }

    def choose(self, state: RuntimeState, actions: list[Action]) -> Decision:
        payload = self.build_request(state, actions)
        encoded_payload = json.dumps(payload).encode("utf-8")
        started = time.perf_counter()
        body: dict[str, Any] | None = None
        retry_delays = [0.5, 1.0, 2.0]

        for attempt in range(len(retry_delays) + 1):
            request = urllib.request.Request(
                self.endpoint,
                data=encoded_payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(
                    request, timeout=self.timeout_seconds
                ) as response:
                    body = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code in {429, 529} and attempt < len(retry_delays):
                    time.sleep(retry_delays[attempt])
                    continue
                raise RuntimeError(f"TypeSafe HTTP {exc.code}: {detail}") from exc
            except urllib.error.URLError as exc:
                if attempt < len(retry_delays):
                    time.sleep(retry_delays[attempt])
                    continue
                raise RuntimeError(f"TypeSafe request failed: {exc}") from exc

        if body is None:
            raise RuntimeError("TypeSafe request completed without a response body")

        latency_ms = round((time.perf_counter() - started) * 1000)
        answer = body.get("answers", {}).get("next_action")
        if not answer or answer.get("type") != "choice":
            raise RuntimeError(f"unexpected TypeSafe response: {body}")

        action_id = answer.get("choice")
        action_ids = {action.id for action in actions}
        if action_id not in action_ids:
            raise RuntimeError(
                f"TypeSafe selected unknown action {action_id!r}; expected one of "
                f"{sorted(action_ids)!r}"
            )

        return Decision(
            action_id=action_id,
            source="typesafe-system-one",
            confidence=answer.get("confidence"),
            probabilities=answer.get("probabilities"),
            model=body.get("model", self.model),
            usage=body.get("usage"),
            latency_ms=latency_ms,
            request=payload,
            response=body,
        )


class OfflineFixtureDecider:
    """Deterministic stand-in for tests and documentation; not an AI substitute."""

    def choose(self, state: RuntimeState, actions: list[Action]) -> Decision:
        goal = state.goal.lower()

        namespace_matches = [
            action
            for action in actions
            if action.kind == ActionKind.SELECT_NAMESPACE
            and action.params.get("namespace", "").lower() in goal
        ]
        if namespace_matches:
            return Decision(namespace_matches[0].id, source="offline-fixture")

        log_actions = [
            action for action in actions if action.kind == ActionKind.EMIT_LOGS_COMMAND
        ]
        if log_actions:
            def score(action: Action) -> tuple[int, str]:
                haystack = " ".join(
                    [
                        action.params.get("pod", ""),
                        action.params.get("container", ""),
                        action.description,
                    ]
                ).lower()
                tokens = [
                    token
                    for token in goal.replace("/", " ").replace("-", " ").split()
                    if len(token) >= 3
                ]
                return (sum(token in haystack for token in tokens), action.id)

            selected = max(log_actions, key=score)
            return Decision(selected.id, source="offline-fixture")

        return Decision(actions[0].id, source="offline-fixture")


class SystemOneKubernetesRuntime:
    def __init__(
        self,
        environment: Environment,
        decider: Decider,
        frontier: FrontierCompiler | None = None,
    ):
        self.environment = environment
        self.decider = decider
        self.frontier = frontier or FrontierCompiler()

    def run(self, goal: str, max_steps: int = 12) -> RuntimeState:
        state = RuntimeState(goal=goal)
        self._record(
            state,
            "runtime_started",
            {
                "goal": goal,
                "max_steps": max_steps,
            },
        )

        for step in range(1, max_steps + 1):
            if state.phase in {Phase.DONE, Phase.BLOCKED}:
                return state

            try:
                actions = self.frontier.compile(state)
            except RuntimeError as exc:
                self._block(state, str(exc))
                return state

            if not actions:
                self._block(state, f"no actions available in phase {state.phase.value}")
                return state

            self._record(
                state,
                "frontier_compiled",
                {
                    "step": step,
                    "size": len(actions),
                    "actions": [
                        {
                            "id": action.id,
                            "kind": action.kind.value,
                            "description": action.description,
                            "params": action.params,
                        }
                        for action in actions
                    ],
                },
            )

            decision = self._choose(state, actions)
            state.decisions.append(decision)
            self._record(
                state,
                "action_selected",
                {
                    "step": step,
                    "action_id": decision.action_id,
                    "source": decision.source,
                    "confidence": decision.confidence,
                    "probabilities": decision.probabilities,
                    "model": decision.model,
                    "usage": decision.usage,
                    "latency_ms": decision.latency_ms,
                },
            )
            if decision.request is not None or decision.response is not None:
                self._record(
                    state,
                    "model_exchange",
                    {
                        "step": step,
                        "request": decision.request,
                        "response": decision.response,
                        "latency_ms": decision.latency_ms,
                    },
                )

            action = next(action for action in actions if action.id == decision.action_id)

            try:
                self._apply(state, action)
            except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
                self._block(state, str(exc))
                return state

        self._block(state, f"step budget exhausted after {max_steps} steps")
        return state

    def _choose(self, state: RuntimeState, actions: list[Action]) -> Decision:
        if len(actions) == 1:
            return Decision(actions[0].id, source="deterministic-single-candidate")
        return self.decider.choose(state, actions)

    def _apply(self, state: RuntimeState, action: Action) -> None:
        if action.kind == ActionKind.DISCOVER_NAMESPACES:
            state.context = self.environment.current_context()
            state.namespaces = self.environment.discover_namespaces()
            self._record(
                state,
                "observation_recorded",
                {
                    "kind": "namespaces",
                    "context": state.context,
                    "namespaces": state.namespaces,
                },
            )
            if not state.namespaces:
                self._block(state, "no Kubernetes namespaces were discovered")
                return
            state.phase = Phase.SELECT_NAMESPACE
            return

        if action.kind == ActionKind.SELECT_NAMESPACE:
            namespace = action.params["namespace"]
            if namespace not in state.namespaces:
                raise RuntimeError(f"action referenced undiscovered namespace {namespace!r}")
            state.selected_namespace = namespace
            self._record(
                state,
                "state_bound",
                {
                    "entity_type": "namespace",
                    "value": namespace,
                },
            )
            state.phase = Phase.DISCOVER_PODS
            return

        if action.kind == ActionKind.DISCOVER_PODS:
            namespace = action.params["namespace"]
            if namespace != state.selected_namespace:
                raise RuntimeError("pod discovery namespace does not match selected namespace")
            state.pods = self.environment.discover_pods(namespace)
            self._record(
                state,
                "observation_recorded",
                {
                    "kind": "pods",
                    "namespace": namespace,
                    "pods": [pod.to_state() for pod in state.pods],
                },
            )
            if not state.pods:
                self._block(state, f"no pods discovered in namespace {namespace!r}")
                return
            state.phase = Phase.SELECT_LOG_TARGET
            return

        if action.kind == ActionKind.EMIT_LOGS_COMMAND:
            namespace = action.params["namespace"]
            pod_name = action.params["pod"]
            container = action.params.get("container")
            discovered = {pod.name: pod for pod in state.pods}
            pod = discovered.get(pod_name)
            if not pod:
                raise RuntimeError(f"action referenced undiscovered pod {pod_name!r}")
            if container and container not in pod.containers:
                raise RuntimeError(
                    f"action referenced undiscovered container {container!r} in {pod_name!r}"
                )
            state.final_command = self.environment.render_logs_command(
                namespace=namespace,
                pod=pod_name,
                container=container if len(pod.containers) > 1 else None,
            )
            self._record(
                state,
                "command_rendered",
                {
                    "argv": state.final_command,
                    "namespace": namespace,
                    "pod": pod_name,
                    "container": container if len(pod.containers) > 1 else None,
                },
            )
            state.phase = Phase.DONE
            self._record(state, "runtime_completed", {"result": "done"})
            return

        raise RuntimeError(f"unsupported action kind: {action.kind}")

    @staticmethod
    def _record(state: RuntimeState, event: str, data: dict[str, Any]) -> None:
        state.trace.append(
            {
                "sequence": len(state.trace) + 1,
                "event": event,
                "phase": state.phase.value,
                "data": data,
            }
        )

    @staticmethod
    def _block(state: RuntimeState, reason: str) -> None:
        state.phase = Phase.BLOCKED
        state.blocked_reason = reason
        SystemOneKubernetesRuntime._record(
            state,
            "runtime_blocked",
            {"reason": reason},
        )


def print_trace(state: RuntimeState) -> None:
    print(f"goal: {state.goal}")
    print(f"context: {state.context or '-'}")
    print(f"phase: {state.phase.value}")
    print("decisions:")
    for index, decision in enumerate(state.decisions, start=1):
        confidence = (
            f" confidence={decision.confidence:.3f}"
            if decision.confidence is not None
            else ""
        )
        print(
            f"  {index}. {decision.action_id} "
            f"[{decision.source}]{confidence}"
        )
    if state.selected_namespace:
        print(f"selected namespace: {state.selected_namespace}")
    if state.pods:
        print("discovered pods:")
        for pod in state.pods:
            print(
                f"  - {pod.name} phase={pod.phase} "
                f"containers={','.join(pod.containers) or '-'}"
            )
    if state.final_command:
        print(f"final command: {shlex.join(state.final_command)}")
    if state.blocked_reason:
        print(f"blocked: {state.blocked_reason}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a grounded kubectl logs command via a progressive System One state machine."
    )
    parser.add_argument("goal", help="Natural-language request to satisfy.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--fixture",
        help="Use a JSON fixture as the Kubernetes environment instead of running kubectl.",
    )
    source.add_argument(
        "--live",
        action="store_true",
        help="Use the current kubectl configuration for read-only discovery.",
    )
    parser.add_argument("--kubeconfig", help="Optional kubeconfig path for --live.")
    parser.add_argument("--context", help="Optional kubectl context for --live.")
    parser.add_argument(
        "--offline-decider",
        action="store_true",
        help="Use a deterministic fixture decider instead of the TypeSafe API.",
    )
    parser.add_argument(
        "--typesafe-endpoint",
        default=os.getenv("TYPESAFE_API_URL", DEFAULT_TYPESAFE_URL),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("TYPESAFE_MODEL", DEFAULT_MODEL),
    )
    parser.add_argument("--json", action="store_true", help="Print the final state as JSON.")
    parser.add_argument(
        "--state-output",
        help="Write the complete final runtime state to this JSON file.",
    )
    parser.add_argument(
        "--trace-output",
        help="Write append-only runtime events to this JSONL file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.fixture:
        environment: Environment = FixtureEnvironment(args.fixture)
    else:
        environment = KubectlEnvironment(
            kubeconfig=args.kubeconfig,
            context=args.context,
        )

    if args.offline_decider:
        decider: Decider = OfflineFixtureDecider()
    else:
        api_key = os.getenv("TYPESAFE_API_KEY", "")
        if not api_key:
            print(
                "TYPESAFE_API_KEY is required unless --offline-decider is used.",
                file=sys.stderr,
            )
            return 2
        decider = TypeSafeSystemOneDecider(
            api_key=api_key,
            endpoint=args.typesafe_endpoint,
            model=args.model,
        )

    runtime = SystemOneKubernetesRuntime(environment=environment, decider=decider)
    state = runtime.run(args.goal)

    if args.state_output:
        state_path = Path(args.state_output)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(asdict(state), indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    if args.trace_output:
        trace_path = Path(args.trace_output)
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", encoding="utf-8") as handle:
            for event in state.trace:
                handle.write(json.dumps(event, default=str) + "\n")

    if args.json:
        print(json.dumps(asdict(state), indent=2, default=str))
    else:
        print_trace(state)

    return 0 if state.phase == Phase.DONE else 1


if __name__ == "__main__":
    raise SystemExit(main())
