# narness-policy core engine — design spec (v0.1)

## 1. Goal and scope

`narness-policy` is the execution-time enforcement engine for the Narness project. It turns an
agent's tool call into a **semantic AST** ("what the agent wants to do"), evaluates it against a
**Policy IR** ("what the system allows it to do"), and returns an **evaluation result** that either
allows, denies, or rewrites the call — while always preserving both the original and the effective
call for behavior analysis.

v0.1 is the **core engine only**: the IR types, a bash command parser, the evaluator, and a thin CLI.
The user-facing policy DSL (YAML) is explicitly out of scope and deferred to v0.2. Policies are
constructed in Rust (for tests) or loaded from a machine-format JSON file that is a direct serde
mirror of the Policy IR — no DSL design happens in v0.1.

## 2. Resolved decisions

| Fork | Decision |
|---|---|
| Language | Rust (new crate), not TypeScript |
| Config layer | None in v0.1 (core engine only); YAML DSL deferred to v0.2 |
| Packaging | Single crate `narness-policy/`, lib + bin, binary name `narness-policy` |
| CLI surface | `inspect` (parse + dump AST) and `eval` (parse + evaluate against a `--policy` JSON file) |

## 3. Crate layout and dependencies

```
narness-policy/
  Cargo.toml
  src/
    lib.rs                     # pub mod ast, parse, policy, eval
    main.rs                    # clap CLI: inspect, eval
    ast.rs                     # all AST types
    parse.rs                   # bash command string → Pipeline
    policy.rs                  # Policy IR (Matcher / Condition / Expr / Action / Feedback)
    eval.rs                    # Evaluator → EvaluationResult
  tests/
    parse.rs                   # parser tests
    eval.rs                    # evaluator tests (policies constructed in code)
```

Dependencies: `clap` (CLI), `serde` + `serde_json` (serialize AST and results), `thiserror`
(typed errors). No third-party shell parser: a hand-written tokenizer (~50 lines, quote-aware) is
used because preserving option syntax (`--limit=100` vs `--limit 100`) is core and a generic
tokenizer would lose it.

## 4. ToolCall AST

Faithful to the original IR, with placeholders marked for types not implemented in v0.1.

```rust
pub type ToolCallId = String;
pub type SessionId = String;

pub struct ToolCall {
    pub id: ToolCallId,
    pub tool: ToolRef,
    pub input: ToolInput,
    pub context: ExecutionContext,
    pub metadata: CallMetadata,
}

pub struct ToolRef {
    pub name: String,
    pub version: Option<String>,
}

pub enum ToolInput {
    Structured(Value),
    Command(Command),
    FileOperation(FileOperation),   // placeholder — future tools (v0.2+)
    HttpRequest(HttpRequest),       // placeholder — future tools (v0.2+)
    Unknown(Value),
}

pub struct FileOperation;   // defined for shape only; not implemented in v0.1
pub struct HttpRequest;     // defined for shape only; not implemented in v0.1
```

### 4.1 Pipeline and Command

Design note (deviation from the original sketch): the original sketch put `pipeline: Option<Pipeline>`
on `Command`, which is redundant/circular (a `Pipeline` already holds `Vec<Command>`). v0.1 resolves
this by making **`Pipeline` the top-level parse result** and keeping `Command` atomic:

```rust
/// A shell pipeline: one or more `Command`s joined by `|`.
/// A single command is a pipeline of length 1. This is the top-level parse result.
pub struct Pipeline {
    pub commands: Vec<Command>,
    pub operators: Vec<PipelineOperator>,   // len == commands.len() - 1
}

pub enum PipelineOperator {
    Pipe,   // |  — && and || are out of scope for v0.1
}

pub struct Command {
    pub executable: String,               // the command token (or path); `CommandPart` from the
                                          // sketch is simplified to a String in v0.1
    pub arguments: Vec<Argument>,
    pub environment: Vec<EnvAssignment>,
    pub working_directory: Option<PathExpr>,  // populated from context, not parsed
    pub stdin: Option<Value>,
    pub shell: ShellKind,
}

pub enum ShellKind {
    Bash,
    Sh,
    Zsh,
    Unknown,
}

pub enum Argument {
    Positional(Value),
    Flag(Flag),
    Option(OptionArg),
}

pub struct Flag {
    pub name: String,    // without leading dashes; for `--no-cache`, name == "cache"
    pub negated: bool,   // true when the flag was `--no-*`
}

pub struct OptionArg {
    pub name: String,    // canonical name without leading dashes, e.g. "limit", "json"
    pub value: Value,
    pub syntax: OptionSyntax,
}

pub enum OptionSyntax {
    Separate,      // --limit 100
    Equals,        // --limit=100
    ShortSeparate, // -n 100
    ShortAttached, // -n100
}
```

Name canonicalization (resolves an ambiguity in the original sketch, which used `name = "limit"`
in the `OptionArg` example but `Argument { name: "--limit" }` in the `Expr` example): names are
canonicalized by **stripping the leading dashes only**. `--limit` → `"limit"`, `-n` → `"n"`,
`-n100` → `"n"`. Short and long forms of the same option are **not** unified in v0.1 (that requires
an alias map, deferred to the v0.2 DSL). `Expr::Argument` matches these canonical names.
```

### 4.2 Value and PathExpr

```rust
pub enum Value {
    String(String),
    Integer(i64),
    Float(f64),
    Boolean(bool),
    Path(PathExpr),
    Url(String),
    Ip(std::net::IpAddr),
    Cidr(String),        // raw string in v0.1; typed via the `ipnet` crate in v0.2
    Duration(Duration),  // defined but not auto-coerced in v0.1
    Enum(String),
    List(Vec<Value>),
    Null,
    Raw(String),
}

pub struct Duration {
    pub amount: f64,
    pub unit: DurationUnit,   // Seconds, Minutes, ... — populated only with a type hint (v0.2)
}

pub struct PathExpr {
    pub raw: String,
    pub normalized: Option<String>,
    pub absolute: bool,
}

pub struct EnvAssignment {
    pub name: String,
    pub value: Value,
}
```

### 4.3 ExecutionContext

```rust
pub struct ExecutionContext {
    pub cwd: Option<PathExpr>,
    pub user: Option<String>,
    pub workspace: Option<PathExpr>,
    pub network: NetworkContext,          // placeholder — populated in v0.2
    pub environment: EnvironmentContext,  // placeholder — populated in v0.2
    pub parent_call: Option<ToolCallId>,
    pub session: Option<SessionId>,
}

pub struct NetworkContext;     // placeholder
pub struct EnvironmentContext; // placeholder

pub struct CallMetadata;       // placeholder
```

## 5. Parser (v0.1 scope)

`parse::parse_bash(input: &str) -> Result<Pipeline, ParseError>`.

- Tokenize with single/double-quote and backslash awareness.
- Classify tokens into `Positional` / `Flag` / `Option`, preserving `OptionSyntax`.
- Split the top-level `|` into a `Pipeline` of `Command`s with `Pipe` operators.
- Detect leading `FOO=bar` tokens as `environment` assignments (best-effort).
- `working_directory` is not parsed from the string (it comes from `ExecutionContext`).

### 5.1 Value coercion policy

- Default token type is `Value::String`.
- Unambiguous numeric tokens → `Value::Integer(i64)` / `Value::Float(f64)`.
- `true` / `false` → `Value::Boolean`.
- Tokens that look like paths (`/`, `./`, `../`, `~` prefix) → `Value::Path(PathExpr)`.
- `Duration` / `Ip` / `Cidr` / `Enum` / `List` are **not auto-coerced** in v0.1: they require a
  type hint (declaring "this argument is a duration" or "this is a comma-separated list"), which
  belongs to the v0.2 DSL. Until then they surface as `Value::String`.

## 6. Policy IR

```rust
pub type PolicyId = String;
pub type RuleId = String;

pub struct Policy {
    pub id: PolicyId,
    pub name: String,
    pub priority: i32,
    pub scope: Scope,
    pub matcher: Matcher,
    pub rules: Vec<Rule>,
    pub metadata: PolicyMetadata,
}

pub enum Scope {
    Global,
    Project,   // placeholder — refined in v0.2
}

pub enum Matcher {
    All(Vec<Matcher>),
    Any(Vec<Matcher>),
    Not(Box<Matcher>),
    Tool(ToolMatcher),
    Command(CommandMatcher),
    Context(ContextMatcher),
}

pub struct ToolMatcher {
    pub name: String,   // "bash", "github", ...
}

pub struct CommandMatcher {
    pub executable: Option<String>,
    pub subcommand: Option<String>,   // the first positional
}

pub struct ContextMatcher {           // placeholder — populated in v0.2
    pub cwd: Option<PathExpr>,
}

pub struct Rule {
    pub id: RuleId,
    pub condition: Condition,
    pub action: Action,
    pub feedback: Option<FeedbackSpec>,
}
```

### 6.1 Condition and Expr

```rust
pub enum Condition {
    All(Vec<Condition>),
    Any(Vec<Condition>),
    Not(Box<Condition>),
    Exists(PathExpr),
    Compare { lhs: Expr, op: CompareOp, rhs: Expr },
    Matches { expr: Expr, pattern: Pattern },   // Pattern placeholder — v0.2
    In { expr: Expr, set: Vec<Expr> },
}

pub enum CompareOp {
    Eq, Ne, Gt, Ge, Lt, Le,
}

pub enum Expr {
    Literal(Value),
    ToolName,
    Executable,
    Arguments,
    Argument { name: String },   // canonical no-dash name (matches OptionArg::name), e.g. "limit"
    Positional { index: usize },
    Environment { name: String },
    WorkingDirectory,
    Context { path: String },
    Function { name: String, args: Vec<Expr> },   // placeholder — v0.2
}
```

### 6.2 Action, RewriteOp, Target

```rust
pub enum Action {
    Allow,
    Deny,
    Ask(AskSpec),              // placeholder — v0.2
    Warn(FeedbackSpec),
    Rewrite(Vec<RewriteOp>),
    Transform(Vec<TransformOp>),  // placeholder — v0.2
    Constrain(Vec<Constraint>),   // placeholder — v0.2
}

pub enum RewriteOp {
    Set { target: Target, value: Expr },
    Remove { target: Target },
    Insert { target: Target, value: Expr },
    Replace { target: Target, value: Expr },
}

pub enum Target {
    Argument { name: String },
    Positional { index: usize },
    Environment { name: String },
    Executable,
    WorkingDirectory,
}
```

### 6.3 Feedback

```rust
pub struct FeedbackSpec {
    pub code: String,
    pub severity: Severity,
    pub message: Template,
    pub guidance: Vec<Template>,
    pub retry: RetryPolicy,
    pub expose_rule: bool,
}

pub enum Severity { Info, Warning, Error }
pub struct Template(String);   // interpolation support lands in v0.2
pub enum RetryPolicy { Never, Once, Always }
```

## 7. Evaluator

```rust
pub enum Decision {
    Allow,
    Deny,
    Rewrite,
    Ask,
    Warn,
}

pub struct EvaluationResult {
    pub decision: Decision,
    pub matched_policies: Vec<PolicyMatch>,
    pub transformations: Vec<Transformation>,
    pub feedback: Vec<Feedback>,
    pub effective_call: Option<ToolCall>,
}

pub struct PolicyMatch { pub policy: PolicyId, pub rule: RuleId }
pub struct Transformation { pub op: RewriteOp }
pub struct Feedback { pub spec: FeedbackSpec }
```

### 7.1 Decision merge (deterministic semantics)

Policies are evaluated in `priority` order (descending). The result is merged as:

1. If any matched rule's action is `Deny` → final `Decision::Deny`, aggregating that rule's feedback.
2. Else if any matched action is `Rewrite`/`Transform`/`Constrain` → apply transformations in
   priority order → final `Decision::Rewrite`.
3. Else if any matched action is `Allow` (or nothing matched) → `Decision::Allow`.

`Transform` and `Constrain` collapse to `Decision::Rewrite` at the decision level; their detail is
recorded in `transformations`.

### 7.2 Original + effective call

`EvaluationResult` always carries the original `ToolCall` (the input) and, when a rewrite happened,
an `effective_call` (the rewritten AST). This pairing is what enables later behavior analysis:
what the agent asked for → what policy changed → whether the agent then adapted.

## 8. CLI

Binary `narness-policy`, two subcommands. Both exit 0 on success (the decision is carried in the
JSON body), and exit 2 on parse/error with diagnostics on stderr.

```
narness-policy inspect <command>
    # parse the command string and dump the AST as JSON

narness-policy eval <command> --policy <policies.json>
    # parse the command, evaluate against a JSON file holding a Vec<Policy>
    # (direct serde mirror of the Policy IR — machine format, not a designed DSL),
    # and dump the EvaluationResult as JSON
```

The `--policy` file is a plain serde_json round-trip of `Vec<Policy>`. No DSL syntax is designed in
v0.1; `Policy` derives `Serialize`/`Deserialize` and the file is just that shape.

The hook adapter (`check`: read `PreToolUse` stdin JSON, map `Deny` → exit 2 + stderr, `Rewrite` →
`updatedInput`) is **out of scope for v0.1** and lands in v0.2 alongside the DSL.

## 9. Testing and error handling

- **Parser tests**: each `OptionSyntax`; single/double-quote handling; flag/option/positional
  classification; pipeline splitting; env-prefix detection; numeric/boolean/path coercion; the
  `--no-*` negation convention.
- **Evaluator tests**: matcher match/no-match; `Compare` on `Argument { name: "limit" } > 20` (canonical no-dash name);
  each `RewriteOp` (set/remove/insert/replace); deny + feedback aggregation; original vs effective
  preservation; priority ordering; the decision-merge table in §7.1.
- **Integration test**: `narness-policy inspect 'gh run list --limit 100'` produces the expected
  AST JSON snapshot.
- **Errors**: `ParseError` (tokenize/classification failure) and `EvalError` (unknown target, type
  mismatch in `Compare`). CLI writes to stderr and exits 2.

## 10. Out of scope (v0.2+)

- YAML DSL (the `match` / `when` / `expression` / `action` / `feedback` syntax).
- The `check` hook adapter (`PreToolUse` stdin → exit-2 block / `updatedInput` rewrite).
- `&&` / `||` command expressions; richer `Value` coercion (`Duration`/`Ip`/`Cidr` via type hints).
- `Context` matcher, `Matches`/`In` conditions, `Function` expr, `Constrain`/`Transform` actions.
- `FileOperation` / `HttpRequest` tool inputs.
- Integration: a `narness policy` subcommand in the existing TS CLI that shells out to this binary.
