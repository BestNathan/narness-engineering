# Generational Source Architecture

> Status: Research / working design.
>
> This note explores a source-code evolution model for AI-native repositories. It is intentionally not a canonical Narness contract yet.

## 1. Thesis

Traditional repositories usually treat source code as the mutable representation of the current system:

```text
source tree = current implementation
Git history = previous implementations
```

That model is optimized for human maintenance. Engineers mutate files in place, remove dead code, consolidate duplicate logic, and use Git to reconstruct why the code changed.

An AI-native repository can consider a different trade-off:

> **Preserve semantic implementation history inside the repository and evolve behavior by succession rather than by in-place mutation.**

The working model is:

```text
stable mechanism
    +
versioned contracts
    +
generational behavior units
    +
immutable lineage
    +
a small manifest selecting the active implementation
```

Instead of repeatedly mutating one implementation:

```text
session.attach()
    edit
    edit
    edit
    edit
```

the repository may evolve an explicit semantic unit:

```text
unit://session.attach

contract v2
    |
    +-- g0041
    +-- g0042
    +-- g0043  <- active
```

The old implementation remains repository memory. The active implementation changes by moving a pointer.

This changes the optimization target from:

```text
minimize code volume
minimize duplication
keep one current implementation
```

toward:

```text
minimize context ambiguity
maximize semantic locality
preserve lineage
make rollback explicit
make runtime behavior addressable
keep proof local to the changed behavior
```

The key hypothesis is not that duplication is free. It is that, for AI-authored behavior, **context uncertainty may be more expensive than bounded duplication**.

## 2. Repository as memory

This model follows a broader AI-native repository thesis:

> The repository itself is durable memory.

Important engineering memory should not need to be reconstructed from an external memory service before an agent can work.

The repository can preserve several kinds of memory:

```text
Semantic memory
  architecture / domain / contracts

Constitutional memory
  principles / invariants

Procedural memory
  Skills / playbooks

Episodic memory
  implementation generations / incidents / decisions

Working state
  active specs / manifests / selected generations

Proof memory
  tests / evidence / contracts / recorded validation
```

Git still records storage history, but Git history is not the only representation of semantic evolution.

A generation lineage can express the history that matters to the engineering concept itself.

```text
Git history:
  repository storage events

Generation lineage:
  semantic implementation evolution
```

The two graphs can overlap without being identical.

## 3. Semantic Unit as the unit of evolution

Files, directories, modules, and packages are storage and compilation structures.

The proposed unit of AI-native evolution is a **Semantic Unit**.

Examples:

```text
unit://session.attach
unit://session.create
unit://capability.resolve
unit://workspace.presence
unit://protocol.session-sync
unit://api.workspace.list
```

A Unit should represent behavior that can be understood, changed, validated, and evolved as one semantic concern.

A stronger working definition is:

> **A Unit is a Provider whose consumer-visible semantics form an independently evolvable contract.**

This reframes "external" as a relationship, not a process boundary. An HTTP operation, a layout provider, a scheduling policy, a context selector, or a protocol method can all be Providers when some Consumer relies on their semantics.

Conceptually:

```text
Unit
├── Identity
├── Contract
├── Invariants
├── Dependencies
├── Generations
├── Active pointer
├── Tests / evidence
├── Observability identity
└── Lineage
```

A file may contain one Unit or participate in several Units. The long-term model should not assume one Unit equals one source file.

The important property is that an agent can resolve:

```text
task
  -> Unit
  -> current contract
  -> current generation
  -> invariants
  -> dependencies
  -> required evidence
```

without broad repository exploration.

## 4. Kernel and Unit are different architectural roles

Not all code should become generational.

The first major boundary is:

> **Kernel provides stable mechanisms. Units provide evolving behavior and policy.**

A useful shape is:

```text
                  Generational Units

         session.attach@g43
         capability.resolve@g21
         workspace.compose@g17
         api.workspace.list@g08

                       |
                       | depend on / compose
                       v

                  Runtime Kernel

         transport
         storage primitives
         transactions
         scheduling primitives
         tracing
         cryptography
         serialization mechanisms
         process/runtime integration
```

The Runtime Kernel should be as small, stable, and single-implementation as practical.

Generational Units should be replaceable, addressable, and independently evolvable.

A strong dependency rule is:

```text
Unit -> Kernel
Kernel -X-> Unit
```

The Kernel should not know which generation of a Unit is active.

A resolver, composition root, or manifest chooses generations above the Kernel.

## 5. Why externally meaningful behavior tends to be a Unit

Externally meaningful behavior usually has one or more of these properties:

- it changes relatively frequently;
- compatibility matters;
- callers may depend on historical semantics;
- rollback can be valuable;
- several implementations may need to coexist;
- incidents need to be traced to an exact behavior revision;
- the behavior has domain-specific invariants;
- validation is more useful when scoped to that behavior.

Therefore public or externally observable boundaries are strong Unit candidates:

```text
API operations
protocol methods
tool schemas
CLI behavior
workflow behavior
capability resolution
domain use cases
UI product behavior
compatibility adapters
model-visible prompts / instructions with behavioral semantics
```

However, "external" should not be the only test.

Some internal policies are high-churn and semantically important enough to be Units.

Some externally reachable mechanisms are stable enough to remain Kernel infrastructure.

The deeper distinction is:

> **Does this code express evolving semantic behavior, or does it provide a stable mechanism used by many behaviors?**

## 5.1 Provider / Consumer as the semantic boundary

The Provider / Consumer relationship is a more fundamental test than "public API" or "external process."

If something is consumed, some Provider supplies the semantics being consumed.

```text
Consumer
   ↓ depends on
Contract
   ↓ provided by
Provider
```

A process boundary is not required.

Examples:

```text
API consumer
  -> session.attach contract
  -> session.attach Provider

Terminal surface
  -> workspace.layout contract
  -> workspace.layout Provider

Agent loop
  -> tool-routing contract
  -> agent.tool-routing Provider

Scheduler runtime
  -> scheduling-policy contract
  -> scheduler.policy Provider
```

This means a front-end layout can be as legitimate a Provider as an HTTP API.

A layout may provide stable semantics such as:

```text
regions
slots
placement
visibility rules
responsive behavior
composition constraints
```

Its implementations can then evolve independently:

```text
provider://workspace.layout

contract v1
  ├── g0001 fixed toolbar layout
  ├── g0002 contextual capability layout
  └── g0003 adaptive contextual layout
```

The important rule is:

> **"External" is relative to a Consumer, not relative to a process.**

A Provider becomes a strong Unit candidate when its Consumer-visible semantics need an independent evolution history.

### Consumer dependency law

Consumers should depend on Contracts, never on concrete Generations.

Avoid:

```text
terminal
  -> workspace.layout@g0008
```

Prefer:

```text
terminal
  -> workspace.layout/v1
  -> Provider Resolver
  -> workspace.layout@g0008
```

Generation identity belongs to Provider evolution and composition. It should not leak into ordinary Consumer dependencies.

This yields a general dependency law:

> **Consumer -> Contract -> Provider -> Generation**

A Unit may itself be both Consumer and Provider.

For example:

```text
session.attach Unit

consumes:
  stream contract
  session-store contract
  clock contract

provides:
  session.attach contract
```

That makes the semantic graph richer than a normal import graph:

```text
import graph:
  file A -> module B

semantic graph:
  Consumer -> Contract -> Provider
```

The semantic graph is a stronger basis for context routing, compatibility analysis, change impact, and evidence planning.

### Unit-to-Unit dependency

One Unit Generation should not depend directly on another Unit Generation.

Avoid:

```text
session.attach@g0043
  -> session.resolve@g0021
```

Prefer:

```text
session.attach@g0043
  -> session.resolve/v1
  -> Provider Resolver
  -> session.resolve@g0021
```

The Composition Root or release manifest resolves Contract identities to concrete Generations.

This keeps succession local to the Provider and prevents generation coupling from spreading through the repository.

### Provider role and evolution model are orthogonal

Provider / Consumer role alone does not decide Unit versus Kernel because the Kernel is also a Provider.

A better model uses two dimensions:

| Semantic role | Generational evolution | Convergent evolution |
|---|---|---|
| Provider | Unit | Kernel Capability |
| Consumer | Consumes Contract | Consumes Contract |

A **Generational Provider** evolves by succession:

```text
Provider
  ├── g1
  ├── g2
  └── g3
```

Its goals are compatibility, rollback, coexistence, and semantic traceability.

A **Convergent Provider** evolves toward one current implementation:

```text
Provider
  -> current implementation
  -> repaired / improved in place
```

Its goals are global fix propagation, shared correctness, and minimal duplication.

This gives a sharper distinction:

> **Unit evolves by succession. Kernel evolves by convergence.**

For example:

```text
session.attach          -> Generational Provider -> Unit
workspace.layout        -> Generational Provider -> Unit
scheduler.policy        -> Generational Provider -> Unit

transport.stream        -> Convergent Provider   -> Kernel Capability
database.transaction    -> Convergent Provider   -> Kernel Capability
ui.popover              -> Convergent Provider   -> UI Kernel Capability
```

A useful architectural interpretation is:

```text
semantic evolution boundary
  -> Unit

shared correctness boundary
  -> Kernel
```

## 6. A practical Unit vs Kernel decision model

A component is a stronger **Unit** candidate when several of these are true:

| Signal | Why it favors a Unit |
|---|---|
| High change frequency | Successive implementations are expected |
| Compatibility pressure | Historical semantics matter |
| Public / cross-process contract | Callers may outlive an implementation |
| Rollback value | Previous behavior may need reactivation |
| Coexistence requirement | Multiple generations or contract versions may run together |
| Domain-specific invariants | Behavior can be reasoned about locally |
| Distinct evidence | The behavior has focused proof obligations |
| Incident traceability | Runtime failures benefit from exact generation identity |
| Policy rather than mechanism | Different decisions can share one runtime substrate |
| Independent ownership | The behavior can evolve without replacing infrastructure |

A component is a stronger **Kernel** candidate when several of these are true:

| Signal | Why it favors the Kernel |
|---|---|
| Low semantic churn | One implementation can remain authoritative |
| Broad reuse | Many Units depend on it |
| Global security patching | Fixes should apply everywhere immediately |
| Mechanism rather than policy | It does not decide product/domain semantics |
| No compatibility identity of its own | Callers care about capability, not historical behavior |
| Expensive duplication | Multiple copies increase risk more than locality |
| Foundational lifecycle | It owns execution, storage, transport, or resource safety |
| Stable internal contract | It can support many generations above it |

This is not a binary compile-time taxonomy. Some components may move across the boundary as the architecture matures.

## 7. Examples of the boundary

### Database

Usually Kernel:

```text
connection pool
transaction primitive
query execution
retry / timeout mechanism
database driver integration
```

Usually versioned or Unit-owned:

```text
logical persistence behavior
domain repository semantics
schema version
migration behavior
compatibility mapping
```

The database mechanism should normally stay single.

The data contract may evolve.

### Redis

Usually Kernel:

```text
client
connection lifecycle
serialization primitive
retry / backoff
basic cache operations
```

Potential Units:

```text
session cache policy
distributed lock policy
presence projection
rate-limit semantics
```

The Redis client is infrastructure. Cache policy is behavior.

### Transport

Usually Kernel:

```text
socket lifecycle
framing primitives
TLS
reconnect mechanism
backpressure primitives
stream I/O
```

Usually Unit / contract territory:

```text
protocol method semantics
message routing policy
negotiation behavior
compatibility handling
request lifecycle semantics
```

The transport mechanism should not need one copy per protocol generation.

### Scheduler

Potential Kernel:

```text
task queue
wakeups
timer mechanism
execution slots
cancellation primitive
resource accounting
```

Potential Units:

```text
routing policy
retry policy
agent scheduling policy
priority policy
workflow transition behavior
```

Again:

```text
mechanism -> Kernel
policy    -> Unit
```

### API

The HTTP/WebSocket server mechanism may be Kernel.

The operations are Units:

```text
unit://api.session.attach
unit://api.session.create
unit://api.workspace.list
```

Each operation can have explicit contract and implementation lineage.

## 8. Contract version and implementation generation are separate

A critical requirement is to avoid using one version number for two different forms of evolution.

The model should distinguish:

```text
Contract Version
        x
Implementation Generation
```

Example:

```text
session.attach
|
+-- contract v1
|    +-- g0001
|    +-- g0002
|    +-- g0003 <- active v1
|
+-- contract v2
     +-- g0001
     +-- g0002 <- active v2
```

A race-condition fix does not necessarily create a new contract version.

```text
before:
  contract v2
  generation g0042

after:
  contract v2
  generation g0043
```

A semantic or wire-compatibility change may create a new contract version:

```text
before:
  contract v2

after:
  contract v3
```

This separation prevents implementation churn from exploding public API versions.

## 9. Persistence schema is a third evolution axis

Persistence evolution should not be conflated with either API contract or implementation generation.

A runtime Unit may therefore have three independent references:

```text
contract:       v2
implementation: g0043
schema:         s0017
```

For example:

```text
unit://session.create
  contract       = v2
  implementation = g0014
  schema         = s0017
```

This lets an agent reason explicitly about what changed:

```text
same contract + new generation
  -> internal implementation change

new contract + same schema
  -> external semantic change

same contract + new schema
  -> storage evolution behind stable behavior
```

## 10. A possible physical representation

One possible representation is:

```text
src/
└── units/
    └── session/
        └── attach/
            ├── UNIT.yaml
            ├── INVARIANTS.md
            ├── contracts/
            │   ├── v1/
            │   │   └── contract.yaml
            │   └── v2/
            │       └── contract.yaml
            └── generations/
                ├── g0041/
                │   ├── META.yaml
                │   ├── impl.rs
                │   └── tests.rs
                ├── g0042/
                │   ├── META.yaml
                │   ├── impl.rs
                │   └── tests.rs
                └── g0043/
                    ├── META.yaml
                    ├── impl.rs
                    └── tests.rs
```

The exact layout is not important yet.

The important semantic relationships are.

A Unit manifest might say:

```yaml
id: session.attach

active:
  v1: g0031
  v2: g0043

invariants:
  - ./INVARIANTS.md

kernel_dependencies:
  - transport.stream
  - runtime.task
  - tracing
```

A generation may record:

```yaml
id: session.attach/v2@g0043
parent: g0042

reason:
  fix relay reconnect race

supersedes:
  - g0042

issue:
  - "#921"

validation:
  - session_attach_reconnect
  - relay_backward_compatibility
```

These examples are intentionally conceptual. Narness should not standardize a schema before proving the model.

## 11. Published generations should be immutable

A strong rule is:

> **Published implementation generations are immutable. Evolve by succession, not mutation.**

Once `g0042` is published, a change creates `g0043`.

This has several consequences.

### Lineage becomes explicit

```text
g0041
  |
  v
g0042
  |
  v
g0043
```

### Rollback becomes pointer movement

```text
active:
  g0043 -> g0042
```

### Debugging becomes generation-local

A production failure tagged with `g0042` resolves directly to the exact implementation.

### Refactoring can be replacement

Instead of mutating the old implementation into a new architecture:

```text
g0027
  -> create g0028
  -> prove behavioral equivalence
  -> move active pointer
```

The predecessor remains available for comparison and rollback.

## 12. Source-level copy-on-write

The repository can be understood as a persistent data structure.

Only changed Units produce new generations.

Example release:

```text
release r1052

session.create       -> g0014
session.attach       -> g0042
capability.resolve   -> g0021
terminal.attach      -> g0009
```

A change to `session.attach` produces:

```text
release r1053

session.create       -> g0014
session.attach       -> g0043   <- changed
capability.resolve   -> g0021
terminal.attach      -> g0009
```

The repository may contain many historical generations while the active implementation graph remains small.

This is analogous to copy-on-write or persistent data structures:

> unchanged semantic nodes continue to reference existing generations; changed nodes fork successors.

## 13. Release as an implementation graph

A release may eventually be represented as an immutable manifest of Unit selections:

```yaml
release: r1053

units:
  session.create:
    contract: v2
    generation: g0014

  session.attach:
    contract: v2
    generation: g0043

  capability.resolve:
    contract: v1
    generation: g0021
```

This makes a release closer to a semantic lockfile than a vague source snapshot.

The build system resolves logical Unit identities to selected generations.

Conceptually:

```text
logical Unit
   ↓
release / source manifest
   ↓
selected generation
   ↓
compiler / packager
```

## 14. Historical code and executable code must be different sets

Keeping historical code does not mean keeping every historical implementation executable.

This distinction is essential.

```text
All generations
    |
    +-- historical
    |     readable
    |     excluded from normal build
    |
    +-- supported
    |     executable for compatibility
    |
    +-- active
          default runtime selection
```

Possible lifecycle states:

```text
current
supported
compatibility-only
retired
unsafe
```

For example:

```yaml
g0021:
  status: compatibility-only

g0035:
  status: supported

g0043:
  status: current

g0012:
  status: unsafe
  replacement: g0043
```

This prevents "repository memory" from becoming "runtime attack surface."

A useful invariant is:

> **Memory is not executability.**

## 15. Why Kernel duplication should be resisted

Generational behavior can tolerate some duplication because locality and lineage are valuable.

Kernel duplication has different economics.

If TLS handling, cryptographic validation, database transactions, or transport safety are copied into many generations, one security fix may require patching dozens of historical implementations.

That creates **patch fan-out**.

Therefore the model should prefer:

> **Reuse infrastructure; version behavior.**

Or:

> **Stable mechanism; replaceable policy.**

Security-sensitive and foundational mechanisms should usually have one current implementation so a fix becomes globally effective.

Generations should depend on the Kernel rather than snapshotting the Kernel into themselves.

## 16. Composition should happen above the Kernel

A generation should declare the stable capabilities it requires.

Example:

```text
session.attach@g0043

requires:
  transport.stream
  runtime.task
  runtime.clock
  tracing.span
  session.store
```

The Unit composes those mechanisms into behavior.

The Kernel does not need to know:

```text
session.attach
g0043
contract v2
```

This produces a useful inversion:

```text
Traditional:
  central runtime contains behavior-specific branches

Generational:
  behavior Unit imports stable runtime capabilities
```

The composition root chooses the behavior implementation.

## 17. Invariants are the constitution of a Unit

Each evolving Unit needs durable truths that survive generations.

Example:

```text
unit://session.attach

I1. Attachment survives transient relay reconnect.

I2. Session identity cannot change during reattach.

I3. Contract v1 peers remain accepted while v1 is supported.

I4. Attach behavior does not own Session lifecycle.
```

The normal AI evolution loop becomes:

```text
resolve Unit
  ↓
load scoped instructions
  ↓
load invariants
  ↓
load current contract
  ↓
load current generation
  ↓
load focused evidence
  ↓
fork successor generation
  ↓
implement
  ↓
validate invariants + contract
  ↓
move active pointer
```

Historical generations remain deferred context.

The agent loads lineage only when it needs to answer a historical question.

This is progressive disclosure applied to source evolution itself.

## 18. Scoped instructions and Skills

Scoped instructions should make the model discoverable without embedding the whole architecture in every context.

A scoped `AGENTS.md` may say:

```text
This subtree owns Session behavior Units.

Canonical invariants:
  -> docs/invariants/session.md

When changing a published Unit:
  -> load skill: generation-evolution

Do not mutate a published generation.

Internal implementation change:
  -> keep contract version
  -> fork implementation generation

External semantic change:
  -> evaluate new contract version
```

The corresponding Skill can describe the procedure:

```text
1. Resolve current Unit and generation.
2. Load Unit invariants.
3. Load the active contract.
4. Load the current implementation.
5. Resolve required evidence.
6. Fork the next generation.
7. Modify only the successor.
8. Validate.
9. Update the active manifest.
10. Preserve the predecessor.
```

This lets the repository remain large while the task context stays narrow.

## 19. Runtime observability should carry Unit identity

The model becomes much more useful if runtime evidence can address the exact source generation.

Logs and traces may carry:

```text
unit=session.attach
contract=v2
generation=g0043
operation=relay_attach
```

A trace can become:

```text
request
  ↓
session.resolve@g0019
  ↓
session.attach@g0043
  ↓
transport.relay
```

Then production diagnosis can resolve directly:

```text
runtime event
  -> Unit
  -> generation
  -> contract
  -> invariants
  -> tests
  -> parent generation
```

This creates a strong Repository <-> Runtime mapping for AI-assisted operations.

## 20. Failure localization

A conventional debugging flow often begins with broad search:

```text
error
  -> grep repository
  -> inspect many files
  -> reconstruct ownership
  -> identify relevant history
```

A generation-addressable flow can begin with:

```text
unit=session.attach
generation=g0042
```

The context resolver can immediately return:

```text
UNIT metadata
invariants
contract v2
generation g0042
focused tests
parent g0041 metadata
```

The agent may discover that the defect first appeared in `g0042`, produce `g0043`, validate it, and move the pointer.

This is one of the strongest potential benefits of the model:

> **The source tree itself becomes an index for failure localization.**

## 21. Relationship to Engineering Surfaces

A Unit and an Engineering Surface should not be assumed to be the same concept.

A Unit is primarily an **evolution boundary**.

A Surface is primarily a **reasoning, constraint, impact, and evidence boundary**.

A Surface may contain several Units:

```text
Surface: websocket-contract

Units:
  protocol.session-sync
  api.session.attach
  codec.session-message
```

A Unit may also participate in several Surfaces.

This suggests:

```text
Intent
  -> Surface
  -> Unit(s)
  -> Generation(s)
```

Before a change, Surfaces help locate the relevant semantic area.

During implementation, Units provide replacement boundaries.

After the change, Surfaces expand evidence obligations.

## 22. Relationship to the Runtime Kernel

The Kernel is not simply "code that never changes."

Kernel code still evolves.

The difference is that Kernel evolution normally remains **single-lineage infrastructure evolution**, not behavior coexistence.

For example, upgrading the database pool implementation should generally replace the one Kernel implementation rather than leave every historical pool implementation routable.

The Kernel can still use normal source history, tests, releases, and Git.

Generational evolution is reserved for code where preserving explicit semantic predecessors provides enough value to justify the additional structure.

This boundary keeps the model from turning the entire repository into historical duplication.

## 23. Candidate architecture layers

A working layered model is:

```text
Contracts
  external semantics / compatibility
        |
        v
Generational Units
  policy / behavior / workflows / public operations
        |
        v
Stable Runtime Kernel
  execution / transport / storage / resource mechanisms
        |
        v
Infrastructure
  DB / Redis / OS / network / filesystem / external systems
```

Another useful view is:

```text
what may change independently?
    -> Unit

what must remain compatible?
    -> Contract

what should be globally fixed once?
    -> Kernel

what is provided outside the process?
    -> Infrastructure
```

## 24. What should not become generational by default

The model should resist generation proliferation for:

- tiny private helpers with no semantic identity;
- low-level data structures;
- general-purpose utility code;
- cryptographic primitives;
- network I/O mechanisms;
- database connection infrastructure;
- tracing/logging plumbing;
- memory allocators and process runtime details;
- code where every caller should immediately inherit a fix;
- code with no meaningful independent rollback or compatibility story.

Making these generational would increase code volume without improving semantic locality.

## 25. What is especially promising as Units

Strong candidates include:

- API operations;
- protocol methods and negotiation behavior;
- domain commands / use cases;
- workflow transitions;
- schedulers' policy layers;
- compatibility adapters;
- product capability resolution;
- model-facing tool behavior;
- prompts whose semantics affect external behavior;
- migration logic where historical compatibility must remain understandable;
- UI interaction policies with important state transitions;
- orchestration behavior whose regressions benefit from precise rollback.

These have explicit semantic identities and tend to change faster than the mechanisms they compose.

## 26. Research risks

### Generation explosion

If every edit creates a new full copy, repository growth and tooling cost may become unreasonable.

Research should distinguish:

- full source copies;
- generated deltas;
- structural sharing;
- compile-time selection;
- archived generations.

### Patch fan-out

Security or correctness defects in duplicated mechanisms may require many fixes.

The Kernel boundary is intended to reduce this risk.

### Build cost

Historical generations should not automatically participate in default builds.

### False immutability

A generation may depend on Kernel behavior that changes underneath it.

Therefore exact reproducibility may require recording Kernel/runtime compatibility ranges or release manifests, not only Unit generation IDs.

### Contract ambiguity

A new generation must not silently change externally meaningful semantics while claiming the same contract version.

Executable contract evidence is important.

### Over-modeling

If Unit metadata becomes more expensive than the behavior itself, the model will fail.

The smallest useful Unit declaration needs empirical study.

### Human review load

Humans should not be forced to compare entire copied generations manually.

Tooling should render semantic diffs between predecessor and successor.

## 27. Evaluation metrics

Candidate measurements include:

### Context locality

How much context is needed to modify one Unit safely?

### Lineage lookup cost

How quickly can an agent find the predecessor that introduced a behavior?

### Change blast radius

How many unrelated files need modification for one semantic change?

### Rollback cost

Can behavior return to a proven predecessor through pointer movement?

### Compatibility clarity

Can an agent determine which contract versions and implementations coexist?

### Patch fan-out

How many generations require modification when a Kernel-level defect is found?

### Build selectivity

Can historical memory remain available without increasing normal build cost proportionally?

### Failure resolution time

Does runtime generation identity reduce the search required to diagnose a production failure?

### Evidence locality

Can a generation carry or resolve the focused proof relevant to its behavior?

## 28. Prototype questions

A useful prototype should answer:

1. Can a small service compile Units selected through a manifest?
2. Can contract version and implementation generation evolve independently?
3. Can old generations remain in the repository but outside the default build?
4. Can two supported contract generations coexist at runtime?
5. Can a failure log identify a Unit and generation and resolve directly to source?
6. Can an agent generate a successor without reading unrelated historical generations?
7. Can the Kernel remain unaware of Unit generation identity?
8. Can the repository generate a useful predecessor/successor semantic diff?
9. Can a security fix in the Kernel apply to every active Unit without patch fan-out?
10. Can rollback be expressed as a manifest change plus evidence rather than source reconstruction?

## 29. Working principles

The current working principles are:

1. **Repository is memory.**
2. **Every meaningful consumed semantic has a Provider.**
3. **Every meaningful Provider exposes a Contract.**
4. **Consumers depend on Contracts, never concrete Generations.**
5. **A Provider whose semantics evolve independently becomes a Unit.**
6. **Semantic Unit is the evolution boundary.**
7. **Published generations are immutable.**
8. **Change by succession, not mutation.**
9. **Contract version and implementation generation are separate.**
10. **Persistence schema is an independent evolution axis.**
11. **Unit carries behavior; Kernel carries mechanism.**
12. **Unit evolves by succession; Kernel evolves by convergence.**
13. **Unit Generations may consume other Unit Contracts, not concrete Unit Generations.**
14. **Unit depends on Kernel capabilities; Kernel does not depend on Unit Generations.**
15. **Reuse infrastructure; version behavior.**
16. **Memory is not executability.**
17. **Historical generations are deferred context.**
18. **Runtime events should be source-addressable by Provider, Contract, Unit, and Generation where applicable.**
19. **Evidence should be local enough to validate a successor before activation.**
20. **Generation should reduce ambiguity, not become a new source of ceremony.**

## 30. Open questions

- What is the smallest practical Unit boundary?
- Should generation IDs be repository-global or Unit-local?
- Should generations be directories, generated artifacts, or logical references over structural sharing?
- When is a contract change required versus only a new generation?
- How should Kernel compatibility be recorded for historical reproducibility?
- How many supported generations should remain executable?
- How should Contract resolution and dependency injection remain explicit without making composition metadata too expensive?
- How should cyclic Unit dependencies be prevented?
- How should cross-Unit transactions work without collapsing Units back into one mutable implementation?
- How should generation garbage collection work while preserving repository memory?
- Should historical code eventually move to an archive while retaining addressable lineage?
- How should generated code participate in lineage?
- How should stateful migrations interact with rollback?
- What should a generation-aware debugger or code navigator expose to an agent?
- Can generation selection become part of Narness' Engineering Surface and evidence planner?

## 31. Relationship to the broader Agent-Native Repository topic

This model extends the agent-native repository thesis in one specific direction.

The broader topic asks:

```text
How should repository knowledge be structured for agents?
```

Generational Source Architecture asks:

```text
How should source implementation itself evolve when agents are the dominant code producers?
```

The combined hypothesis is:

```text
Repository as memory
        +
semantic context routing
        +
Provider / Consumer graph
        +
stable Contracts
        +
stable invariants
        +
generational Provider Units
        +
convergent Runtime Kernel Providers
        +
evidence-driven activation
```

This would turn the repository from a mutable tree of current source into a machine-navigable history of semantic implementations whose active composition remains explicit and provable.

## Related topic material

- [Agent-Native Repository Architecture](../README.md)
- [Engineering Surfaces](../../engineering-surfaces/README.md)
- [Change-to-Evidence Planning](../../change-to-evidence-planning/README.md)
- [Harness Engineering](../../harness-engineering/README.md)
