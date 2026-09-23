# System One Kubernetes Command Generator

> Experimental research prototype. This is not a production Kubernetes agent and is not part of the canonical Narness runtime.

This example explores a specific System One harness pattern:

> A large dynamic environment does not need a globally finite state space. The runtime can discover state progressively and expose only a small, grounded local action frontier to a fast decision model.

The demo turns a request such as:

> Show me the Kubernetes logs for nession in staging.

into a grounded command such as:

~~~text
kubectl -n staging logs nession-staging-7d4c6d9d7f-k8m2p
~~~

The model does not generate that shell command. It selects typed actions whose parameters were discovered from the Kubernetes environment. The runtime validates the selection and lowers it into command arguments deterministically.

## Flow

~~~text
Goal
  |
  v
Discover namespaces
  |
  v
Known state expands
  |
  v
Compile namespace action frontier
  |
  +-- one candidate -> deterministic transition
  |
  +-- multiple candidates -> System One Choice
  |
  v
Discover pods in selected namespace
  |
  v
Known state expands again
  |
  v
Compile pod/container log-target frontier
  |
  +-- one candidate -> deterministic transition
  |
  +-- multiple candidates -> System One Choice
  |
  v
Validate grounded parameters
  |
  v
Deterministically render kubectl command
~~~

The important property is that both state and the action space are progressively disclosed.

## State machine

The current demo has five useful phases:

~~~text
DISCOVER_NAMESPACES
        |
        v
SELECT_NAMESPACE
        |
        v
DISCOVER_PODS
        |
        v
SELECT_LOG_TARGET
        |
        v
DONE
~~~

A blocked state is also available for invalid observations, exhausted step budgets, empty discovery results, or an action frontier that is too large for this prototype.

The discovery phases are deterministic environment operations. The selection phases are judgment points.

## TypeSafe System One mapping

The TypeSafe API is used as a thin decision function.

The demo sends:

~~~text
POST https://api.typesafe.ai/v1/systemone

state:
  goal
  current phase
  Kubernetes context
  discovered namespaces
  selected namespace
  discovered pods and containers
  recent decisions

model:
  jev-latest

questions.next_action:
  type: choice
  criteria: current grounded action frontier
~~~

Each Choice criterion is an action ID plus a description and already-grounded parameters.

For example, after namespace discovery the frontier may look conceptually like:

~~~text
namespace:default
namespace:kube-system
namespace:monitoring
namespace:staging
~~~

System One chooses one of these IDs. It cannot invent another namespace because an invented value is not part of the Choice criteria.

After staging is selected, the runtime performs a read-only pod discovery. That observation may expand the state with:

~~~text
nession-staging-7d4c6d9d7f-k8m2p
postgres-staging-0
redis-staging-0
~~~

The next frontier is then instantiated from those real pod/container identities.

## Action templates vs dynamic action instances

The command vocabulary is finite at the template level:

~~~text
discover_namespaces()
select_namespace(namespace)
discover_pods(namespace)
emit_logs_command(namespace, pod, container?)
~~~

But the action instances are dynamic:

~~~text
select_namespace("staging")
emit_logs_command(
  namespace="staging",
  pod="nession-staging-7d4c6d9d7f-k8m2p"
)
~~~

This is the core research distinction.

The runtime does not enumerate every possible Kubernetes state in advance. It defines a small set of affordance templates and instantiates them only from entities that have actually been observed.

## Run the deterministic fixture

No Kubernetes cluster or TypeSafe API key is required for the fixture path:

~~~bash
python3 examples/system-one-k8s/system_one_k8s.py \
  "Show me the Kubernetes logs for nession in staging." \
  --fixture examples/system-one-k8s/fixtures/cluster.json \
  --offline-decider
~~~

Expected final line:

~~~text
final command: kubectl -n staging logs nession-staging-7d4c6d9d7f-k8m2p
~~~

The offline decider exists only so the state-machine behavior is runnable in tests and documentation. It is not intended to emulate System One.

## Run the real TypeSafe decision API against the fixture

Set the API key and omit the offline flag:

~~~bash
export TYPESAFE_API_KEY=...

python3 examples/system-one-k8s/system_one_k8s.py \
  "Show me the Kubernetes logs for nession in staging." \
  --fixture examples/system-one-k8s/fixtures/cluster.json
~~~

Optional environment variables:

~~~bash
export TYPESAFE_API_URL=https://api.typesafe.ai/v1/systemone
export TYPESAFE_MODEL=jev-latest
~~~

## Run against the current Kubernetes configuration

The live mode performs read-only discovery with kubectl:

~~~bash
export TYPESAFE_API_KEY=...

python3 examples/system-one-k8s/system_one_k8s.py \
  "Show me the Kubernetes logs for nession in staging." \
  --live
~~~

Optional context selection:

~~~bash
python3 examples/system-one-k8s/system_one_k8s.py \
  "Show me the Kubernetes logs for nession in staging." \
  --live \
  --context my-cluster
~~~

The live environment currently executes only these discovery classes:

~~~text
kubectl config current-context
kubectl get namespaces -o json
kubectl -n <namespace> get pods -o json
~~~

It does not execute the generated logs command. The final command is printed for inspection.

## Safety properties of the demo

1. System One selects only IDs from the current frontier.
2. Namespace, pod, and container values must come from observations.
3. Shell command text is never generated by the model.
4. Commands are represented as argv arrays instead of interpolated shell strings.
5. Live discovery is read-only.
6. A single-candidate frontier skips the model entirely.
7. An oversized frontier blocks rather than silently flooding the Choice question.
8. Final action parameters are revalidated against current in-memory observations before rendering.

Confidence is judgment metadata, not authorization. A production runtime would still need RBAC, policy, approval, freshness, and destructive-action controls.

## Choice size and hierarchical discovery

TypeSafe Choice supports a bounded set of options. This prototype caps the local frontier at 200 candidates, leaving margin below the API limit.

A production design should not arbitrarily truncate a large frontier. It should introduce another state transition that narrows the world deterministically or hierarchically, for example:

~~~text
all namespaces
  -> selected namespace
  -> workload type
  -> workload
  -> pod
  -> container
~~~

That preserves the principle that the model sees a small local frontier rather than the whole cluster.

## Tests

~~~bash
python3 -m unittest discover \
  -s examples/system-one-k8s \
  -p 'test_*.py' \
  -v
~~~

The tests prove:

- progressive discovery reaches the expected nession log command;
- a multi-container pod renders an explicit container flag;
- the TypeSafe request is a Choice question whose criteria exactly match the grounded local frontier.

## What this prototype intentionally does not solve

- durable persistence and replay;
- observation freshness and stale-action rejection across long delays;
- discovery strategies for very large clusters;
- Kubernetes RBAC and authorization;
- mutating or destructive kubectl operations;
- retries and transient API failure policy;
- richer Kubernetes resource affordances;
- a System Two escalation path when the local ontology is insufficient.

Those are part of the research surface rather than hidden assumptions.

## Related topic

See [System One Progressive Action Spaces](../../docs/topics/system-one-progressive-action-space/README.md).
