# narness-policy (v0.1 core engine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `narness-policy` Rust crate — a ToolCall AST, a bash command parser, a Policy IR, and an evaluator — exposed through a `narness-policy` binary with `inspect` and `eval` subcommands.

**Architecture:** A single Rust crate (`narness-policy/`) with four library modules (`ast`, `parse`, `policy`, `eval`) and one binary (`main.rs`). `parse` turns a command string into a semantic `Pipeline` of `Command`s; `eval` takes a `ToolCall` + `Vec<Policy>` and returns an `EvaluationResult` that preserves both the original and (when rewritten) the effective call. The CLI reads policies from a plain JSON file that is a direct serde mirror of `Vec<Policy>`.

**Tech Stack:** Rust 2021, `clap` (derive) for the CLI, `serde` + `serde_json` for serialization, `thiserror` for typed errors.

**Spec:** `docs/superpowers/specs/2026-08-14-narness-policy-design.md`

**Conventions for this plan:**
- All commands run from the `narness-policy/` directory.
- Every commit message ends with the trailer `Co-Authored-By: Claude <noreply@anthropic.com>`.
- v0.1 evaluates the **first command** of a parsed pipeline; multi-command pipeline evaluation is v0.2 (documented in the spec).

---

### Task 1: Scaffold the crate

**Files:**
- Create: `narness-policy/Cargo.toml`
- Create: `narness-policy/.gitignore`
- Create: `narness-policy/src/lib.rs`
- Create: `narness-policy/src/main.rs`

- [ ] **Step 1: Write Cargo.toml**

```toml
[package]
name = "narness-policy"
version = "0.1.0"
edition = "2021"
description = "Narness policy engine: parse an agent tool call into a semantic AST and evaluate it against a policy IR"

[lib]
name = "narness_policy"
path = "src/lib.rs"

[[bin]]
name = "narness-policy"
path = "src/main.rs"

[dependencies]
clap = { version = "4", features = ["derive"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"
```

- [ ] **Step 2: Write .gitignore**

```
/target
```

- [ ] **Step 3: Write lib.rs**

```rust
pub mod ast;
pub mod parse;
pub mod policy;
pub mod eval;
```

- [ ] **Step 4: Write main.rs (minimal stub)**

```rust
fn main() {}
```

- [ ] **Step 5: Verify the crate builds**

Run: `cargo build`
Expected: builds successfully (warning about unused `main` is fine).

- [ ] **Step 6: Commit**

```bash
git add narness-policy/Cargo.toml narness-policy/.gitignore narness-policy/src/lib.rs narness-policy/src/main.rs
git commit -m "chore(narness-policy): scaffold crate" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: ToolCall AST types

**Files:**
- Create: `narness-policy/src/ast.rs`
- Test: `narness-policy/tests/ast.rs`

- [ ] **Step 1: Write the failing test**

```rust
use narness_policy::ast::*;

#[test]
fn tool_call_serializes_to_json() {
    let call = ToolCall {
        id: "t1".into(),
        tool: ToolRef { name: "bash".into(), version: None },
        input: ToolInput::Command(Command {
            executable: "gh".into(),
            arguments: vec![Argument::Positional(Value::String("run".into()))],
            environment: vec![],
            working_directory: None,
            stdin: None,
            shell: ShellKind::Unknown,
        }),
        context: ExecutionContext::default(),
        metadata: CallMetadata,
    };
    let json = serde_json::to_string(&call).unwrap();
    let v: serde_json::Value = serde_json::from_str(&json).unwrap();
    assert_eq!(v["tool"]["name"], "bash");
    assert_eq!(v["input"]["Command"]["executable"], "gh");
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cargo test --test ast`
Expected: FAIL — `ast` module does not exist.

- [ ] **Step 3: Write src/ast.rs**

```rust
//! ToolCall AST: a semantic representation of "what the agent wants to do".

use serde::{Deserialize, Serialize};
use std::net::IpAddr;

pub type ToolCallId = String;
pub type SessionId = String;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolCall {
    pub id: ToolCallId,
    pub tool: ToolRef,
    pub input: ToolInput,
    #[serde(default)]
    pub context: ExecutionContext,
    #[serde(default)]
    pub metadata: CallMetadata,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolRef {
    pub name: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum ToolInput {
    Structured(Value),
    Command(Command),
    FileOperation(FileOperation),
    HttpRequest(HttpRequest),
    Unknown(Value),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct FileOperation; // placeholder — future tools (v0.2+)

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct HttpRequest; // placeholder — future tools (v0.2+)

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Pipeline {
    pub commands: Vec<Command>,
    #[serde(default)]
    pub operators: Vec<PipelineOperator>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum PipelineOperator {
    Pipe,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Command {
    pub executable: String,
    #[serde(default)]
    pub arguments: Vec<Argument>,
    #[serde(default)]
    pub environment: Vec<EnvAssignment>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub working_directory: Option<PathExpr>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stdin: Option<Value>,
    #[serde(default)]
    pub shell: ShellKind,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub enum ShellKind {
    Bash,
    Sh,
    Zsh,
    #[default]
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Argument {
    Positional(Value),
    Flag(Flag),
    Option(OptionArg),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Flag {
    pub name: String,
    #[serde(default)]
    pub negated: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct OptionArg {
    pub name: String,
    pub value: Value,
    pub syntax: OptionSyntax,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum OptionSyntax {
    Separate,      // --limit 100
    Equals,        // --limit=100
    ShortSeparate, // -n 100
    ShortAttached, // -n100
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Value {
    String(String),
    Integer(i64),
    Float(f64),
    Boolean(bool),
    Path(PathExpr),
    Url(String),
    Ip(IpAddr),
    Cidr(String),
    Duration(Duration),
    Enum(String),
    List(Vec<Value>),
    Null,
    Raw(String),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Duration {
    pub amount: f64,
    pub unit: DurationUnit,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum DurationUnit {
    Seconds,
    Minutes,
    Hours,
    Milliseconds,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PathExpr {
    pub raw: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub normalized: Option<String>,
    #[serde(default)]
    pub absolute: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EnvAssignment {
    pub name: String,
    pub value: Value,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct ExecutionContext {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cwd: Option<PathExpr>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub user: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub workspace: Option<PathExpr>,
    #[serde(default)]
    pub network: NetworkContext,
    #[serde(default)]
    pub environment: EnvironmentContext,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub parent_call: Option<ToolCallId>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub session: Option<SessionId>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct NetworkContext; // placeholder — populated in v0.2

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct EnvironmentContext; // placeholder — populated in v0.2

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct CallMetadata; // placeholder
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cargo test --test ast`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add narness-policy/src/ast.rs narness-policy/tests/ast.rs
git commit -m "feat(narness-policy): add ToolCall AST types" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Bash command parser

**Files:**
- Create: `narness-policy/src/parse.rs`
- Test: `narness-policy/tests/parse.rs`

- [ ] **Step 1: Write the failing tests**

```rust
use narness_policy::ast::*;
use narness_policy::parse::parse_bash;

#[test]
fn parses_simple_command() {
    let p = parse_bash("gh run list --limit 100").unwrap();
    assert_eq!(p.commands.len(), 1);
    let cmd = &p.commands[0];
    assert_eq!(cmd.executable, "gh");
    assert_eq!(
        cmd.arguments,
        vec![
            Argument::Positional(Value::String("run".into())),
            Argument::Positional(Value::String("list".into())),
            Argument::Option(OptionArg {
                name: "limit".into(),
                value: Value::Integer(100),
                syntax: OptionSyntax::Separate,
            }),
        ]
    );
}

#[test]
fn parses_option_syntaxes() {
    let p = parse_bash("cmd --a=1 --b 2 -c 3 -d4").unwrap();
    assert_eq!(
        p.commands[0].arguments,
        vec![
            Argument::Option(OptionArg { name: "a".into(), value: Value::Integer(1), syntax: OptionSyntax::Equals }),
            Argument::Option(OptionArg { name: "b".into(), value: Value::Integer(2), syntax: OptionSyntax::Separate }),
            Argument::Option(OptionArg { name: "c".into(), value: Value::Integer(3), syntax: OptionSyntax::ShortSeparate }),
            Argument::Option(OptionArg { name: "d".into(), value: Value::Integer(4), syntax: OptionSyntax::ShortAttached }),
        ]
    );
}

#[test]
fn parses_flags() {
    let p = parse_bash("cmd --verbose --no-cache").unwrap();
    assert_eq!(
        p.commands[0].arguments,
        vec![
            Argument::Flag(Flag { name: "verbose".into(), negated: false }),
            Argument::Flag(Flag { name: "cache".into(), negated: true }),
        ]
    );
}

#[test]
fn respects_quotes() {
    let p = parse_bash("echo \"hello world\"").unwrap();
    assert_eq!(
        p.commands[0].arguments,
        vec![Argument::Positional(Value::String("hello world".into()))]
    );
}

#[test]
fn splits_pipeline() {
    let p = parse_bash("cat foo | grep bar").unwrap();
    assert_eq!(p.commands.len(), 2);
    assert_eq!(p.commands[0].executable, "cat");
    assert_eq!(p.commands[1].executable, "grep");
    assert_eq!(p.operators, vec![PipelineOperator::Pipe]);
}

#[test]
fn parses_env_assignment() {
    let p = parse_bash("FOO=bar gh run list").unwrap();
    let cmd = &p.commands[0];
    assert_eq!(cmd.executable, "gh");
    assert_eq!(
        cmd.environment,
        vec![EnvAssignment { name: "FOO".into(), value: Value::String("bar".into()) }]
    );
}

#[test]
fn coerces_paths() {
    let p = parse_bash("cat /workspace/foo.txt").unwrap();
    assert_eq!(
        p.commands[0].arguments,
        vec![Argument::Positional(Value::Path(PathExpr {
            raw: "/workspace/foo.txt".into(),
            normalized: None,
            absolute: true,
        }))]
    );
}

#[test]
fn rejects_logical_operators() {
    assert!(parse_bash("a && b").is_err());
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cargo test --test parse`
Expected: FAIL — `parse` module and `parse_bash` do not exist.

- [ ] **Step 3: Write src/parse.rs**

```rust
//! Bash command parser: turn a command string into a semantic `Pipeline`.

use crate::ast::*;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ParseError {
    #[error("unterminated quote in command")]
    UnterminatedQuote,
    #[error("logical operators (&&, ||) are not supported in v0.1")]
    LogicalOperator,
    #[error("empty command")]
    EmptyCommand,
}

pub fn parse_bash(input: &str) -> Result<Pipeline, ParseError> {
    let tokens = tokenize(input)?;
    if tokens.is_empty() {
        return Err(ParseError::EmptyCommand);
    }
    let segments = split_pipeline(&tokens)?;
    let mut commands = Vec::new();
    for seg in segments {
        if seg.is_empty() {
            return Err(ParseError::EmptyCommand);
        }
        commands.push(parse_command(&seg)?);
    }
    let operators = vec![PipelineOperator::Pipe; commands.len().saturating_sub(1)];
    Ok(Pipeline { commands, operators })
}

fn tokenize(input: &str) -> Result<Vec<String>, ParseError> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut chars = input.chars().peekable();
    let mut in_single = false;
    let mut in_double = false;
    let mut started = false;

    while let Some(c) = chars.next() {
        match c {
            '\'' if !in_double => {
                in_single = !in_single;
                started = true;
            }
            '"' if !in_single => {
                in_double = !in_double;
                started = true;
            }
            '\\' if !in_single => {
                if let Some(next) = chars.next() {
                    current.push(next);
                    started = true;
                }
            }
            c if c.is_whitespace() && !in_single && !in_double => {
                if started {
                    tokens.push(std::mem::take(&mut current));
                    started = false;
                }
            }
            c => {
                current.push(c);
                started = true;
            }
        }
    }
    if in_single || in_double {
        return Err(ParseError::UnterminatedQuote);
    }
    if started {
        tokens.push(current);
    }
    Ok(tokens)
}

fn split_pipeline(tokens: &[String]) -> Result<Vec<Vec<String>>, ParseError> {
    let mut segments = Vec::new();
    let mut current = Vec::new();
    for t in tokens {
        if t == "|" {
            segments.push(std::mem::take(&mut current));
        } else if t == "&&" || t == "||" {
            return Err(ParseError::LogicalOperator);
        } else {
            current.push(t.clone());
        }
    }
    segments.push(current);
    Ok(segments)
}

fn parse_command(tokens: &[String]) -> Result<Command, ParseError> {
    let mut env = Vec::new();
    let mut idx = 0;
    while idx < tokens.len() {
        if let Some((name, value)) = split_env(&tokens[idx]) {
            env.push(EnvAssignment { name: name.to_string(), value: coerce(value) });
            idx += 1;
        } else {
            break;
        }
    }
    if idx >= tokens.len() {
        return Err(ParseError::EmptyCommand);
    }
    let executable = tokens[idx].clone();
    let mut arguments = Vec::new();
    idx += 1;
    while idx < tokens.len() {
        let (arg, consumed) = classify_arg(&tokens, idx);
        arguments.push(arg);
        idx += consumed;
    }
    Ok(Command {
        executable,
        arguments,
        environment: env,
        working_directory: None,
        stdin: None,
        shell: ShellKind::Unknown,
    })
}

fn split_env(token: &str) -> Option<(&str, &str)> {
    let eq = token.find('=')?;
    let (name, value) = token.split_at(eq);
    let value = &value[1..];
    if !is_valid_env_name(name) {
        return None;
    }
    Some((name, value))
}

fn is_valid_env_name(name: &str) -> bool {
    let mut chars = name.chars();
    match chars.next() {
        Some(c) if c.is_ascii_alphabetic() || c == '_' => {}
        _ => return false,
    }
    chars.all(|c| c.is_ascii_alphanumeric() || c == '_')
}

fn classify_arg(tokens: &[String], idx: usize) -> (Argument, usize) {
    let token = &tokens[idx];
    let next = tokens.get(idx + 1).map(|s| s.as_str());

    if let Some(rest) = token.strip_prefix("--") {
        if rest.is_empty() {
            return (Argument::Positional(coerce(token)), 1);
        }
        if let Some((name, value)) = rest.split_once('=') {
            return (
                Argument::Option(OptionArg {
                    name: name.to_string(),
                    value: coerce(value),
                    syntax: OptionSyntax::Equals,
                }),
                1,
            );
        }
        if let Some(n) = next {
            if !n.starts_with('-') {
                return (
                    Argument::Option(OptionArg {
                        name: rest.to_string(),
                        value: coerce(n),
                        syntax: OptionSyntax::Separate,
                    }),
                    2,
                );
            }
        }
        let (name, negated) = split_no(rest);
        return (Argument::Flag(Flag { name, negated }), 1);
    }

    if let Some(rest) = token.strip_prefix('-') {
        if rest.is_empty() {
            return (Argument::Positional(coerce(token)), 1);
        }
        let mut chars = rest.chars();
        let name = chars.next().unwrap().to_string();
        let rest_of = chars.as_str();
        if !rest_of.is_empty() {
            return (
                Argument::Option(OptionArg {
                    name,
                    value: coerce(rest_of),
                    syntax: OptionSyntax::ShortAttached,
                }),
                1,
            );
        }
        if let Some(n) = next {
            if !n.starts_with('-') {
                return (
                    Argument::Option(OptionArg {
                        name,
                        value: coerce(n),
                        syntax: OptionSyntax::ShortSeparate,
                    }),
                    2,
                );
            }
        }
        return (Argument::Flag(Flag { name, negated: false }), 1);
    }

    (Argument::Positional(coerce(token)), 1)
}

fn split_no(rest: &str) -> (String, bool) {
    if let Some(name) = rest.strip_prefix("no-") {
        (name.to_string(), true)
    } else {
        (rest.to_string(), false)
    }
}

fn coerce(s: &str) -> Value {
    if s == "true" {
        return Value::Boolean(true);
    }
    if s == "false" {
        return Value::Boolean(false);
    }
    if let Ok(i) = s.parse::<i64>() {
        return Value::Integer(i);
    }
    if let Ok(f) = s.parse::<f64>() {
        return Value::Float(f);
    }
    if looks_like_path(s) {
        return Value::Path(PathExpr {
            raw: s.to_string(),
            normalized: None,
            absolute: s.starts_with('/'),
        });
    }
    Value::String(s.to_string())
}

fn looks_like_path(s: &str) -> bool {
    s.starts_with('/') || s.starts_with("./") || s.starts_with("../") || s.starts_with("~/")
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cargo test --test parse`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add narness-policy/src/parse.rs narness-policy/tests/parse.rs
git commit -m "feat(narness-policy): add bash command parser" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: Policy IR types

**Files:**
- Create: `narness-policy/src/policy.rs`
- Test: `narness-policy/tests/policy.rs`

- [ ] **Step 1: Write the failing test**

```rust
use narness_policy::policy::*;

#[test]
fn policy_roundtrips_json() {
    let p = Policy {
        id: "cap-limit".into(),
        name: "cap limit".into(),
        priority: 10,
        scope: Scope::Global,
        matcher: Matcher::Command(CommandMatcher { executable: Some("gh".into()), subcommand: None }),
        rules: vec![Rule {
            id: "r1".into(),
            condition: Condition::Compare {
                lhs: Expr::Argument { name: "limit".into() },
                op: CompareOp::Gt,
                rhs: Expr::Literal(narness_policy::ast::Value::Integer(20)),
            },
            action: Action::Rewrite(vec![RewriteOp::Set {
                target: Target::Argument { name: "limit".into() },
                value: Expr::Literal(narness_policy::ast::Value::Integer(20)),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let s = serde_json::to_string(&p).unwrap();
    let back: Policy = serde_json::from_str(&s).unwrap();
    assert_eq!(p, back);
}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cargo test --test policy`
Expected: FAIL — `policy` module does not exist.

- [ ] **Step 3: Write src/policy.rs**

```rust
//! Policy IR: a declarative description of "what the system allows".

use crate::ast::{PathExpr, Value};
use serde::{Deserialize, Serialize};

pub type PolicyId = String;
pub type RuleId = String;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Policy {
    pub id: PolicyId,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub priority: i32,
    #[serde(default)]
    pub scope: Scope,
    pub matcher: Matcher,
    #[serde(default)]
    pub rules: Vec<Rule>,
    #[serde(default)]
    pub metadata: PolicyMetadata,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub enum Scope {
    #[default]
    Global,
    Project,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct PolicyMetadata; // placeholder

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Matcher {
    All(Vec<Matcher>),
    Any(Vec<Matcher>),
    Not(Box<Matcher>),
    Tool(ToolMatcher),
    Command(CommandMatcher),
    Context(ContextMatcher),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ToolMatcher {
    pub name: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct CommandMatcher {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub executable: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subcommand: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct ContextMatcher {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cwd: Option<PathExpr>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Rule {
    pub id: RuleId,
    pub condition: Condition,
    pub action: Action,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub feedback: Option<FeedbackSpec>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Condition {
    All(Vec<Condition>),
    Any(Vec<Condition>),
    Not(Box<Condition>),
    Exists(PathExpr),
    Compare { lhs: Expr, op: CompareOp, rhs: Expr },
    Matches { expr: Expr, pattern: Pattern },
    In { expr: Expr, set: Vec<Expr> },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum CompareOp {
    Eq,
    Ne,
    Gt,
    Ge,
    Lt,
    Le,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Expr {
    Literal(Value),
    ToolName,
    Executable,
    Arguments,
    Argument { name: String },
    Positional { index: usize },
    Environment { name: String },
    WorkingDirectory,
    Context { path: String },
    Function { name: String, args: Vec<Expr> },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Action {
    Allow,
    Deny,
    Ask(AskSpec),
    Warn(FeedbackSpec),
    Rewrite(Vec<RewriteOp>),
    Transform(Vec<TransformOp>),
    Constrain(Vec<Constraint>),
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct AskSpec; // placeholder — v0.2

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum RewriteOp {
    Set { target: Target, value: Expr },
    Remove { target: Target },
    Insert { target: Target, value: Expr },
    Replace { target: Target, value: Expr },
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Target {
    Argument { name: String },
    Positional { index: usize },
    Environment { name: String },
    Executable,
    WorkingDirectory,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct TransformOp; // placeholder — v0.2

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Constraint; // placeholder — v0.2

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct FeedbackSpec {
    #[serde(default)]
    pub code: String,
    #[serde(default)]
    pub severity: Severity,
    pub message: Template,
    #[serde(default)]
    pub guidance: Vec<Template>,
    #[serde(default)]
    pub retry: RetryPolicy,
    #[serde(default)]
    pub expose_rule: bool,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub enum Severity {
    Info,
    #[default]
    Warning,
    Error,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Template(pub String);

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub enum RetryPolicy {
    #[default]
    Never,
    Once,
    Always,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct Pattern; // placeholder — v0.2
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cargo test --test policy`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add narness-policy/src/policy.rs narness-policy/tests/policy.rs
git commit -m "feat(narness-policy): add Policy IR types" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: Evaluator

**Files:**
- Create: `narness-policy/src/eval.rs`
- Test: `narness-policy/tests/eval.rs`

- [ ] **Step 1: Write the failing tests**

```rust
use narness_policy::ast::*;
use narness_policy::eval::{evaluate, Decision};
use narness_policy::parse::parse_bash;
use narness_policy::policy::*;

fn bash_call(input: &str) -> ToolCall {
    let p = parse_bash(input).unwrap();
    let cmd = p.commands.into_iter().next().unwrap();
    ToolCall {
        id: "t1".into(),
        tool: ToolRef { name: "bash".into(), version: None },
        input: ToolInput::Command(cmd),
        context: ExecutionContext::default(),
        metadata: CallMetadata,
    }
}

fn cap_limit_policy() -> Policy {
    Policy {
        id: "github-run-limit".into(),
        name: "limit github runs".into(),
        priority: 100,
        scope: Scope::Global,
        matcher: Matcher::All(vec![
            Matcher::Tool(ToolMatcher { name: "bash".into() }),
            Matcher::Command(CommandMatcher {
                executable: Some("gh".into()),
                subcommand: Some("run".into()),
            }),
        ]),
        rules: vec![Rule {
            id: "cap-limit".into(),
            condition: Condition::Compare {
                lhs: Expr::Argument { name: "limit".into() },
                op: CompareOp::Gt,
                rhs: Expr::Literal(Value::Integer(20)),
            },
            action: Action::Rewrite(vec![RewriteOp::Set {
                target: Target::Argument { name: "limit".into() },
                value: Expr::Literal(Value::Integer(20)),
            }]),
            feedback: Some(FeedbackSpec {
                code: "ARGUMENT_OUT_OF_RANGE".into(),
                severity: Severity::Warning,
                message: Template("--limit cannot exceed 20".into()),
                guidance: vec![Template("reduce --limit to 20 or less".into())],
                retry: RetryPolicy::Never,
                expose_rule: true,
            }),
        }],
        metadata: PolicyMetadata,
    }
}

#[test]
fn rewrites_out_of_range_limit() {
    let result = evaluate(&bash_call("gh run list --limit 100"), &[cap_limit_policy()]);
    assert_eq!(result.decision, Decision::Rewrite);
    let eff = result.effective_call.as_ref().unwrap();
    match &eff.input {
        ToolInput::Command(c) => {
            assert!(c.arguments.iter().any(|a| matches!(
                a,
                Argument::Option(o) if o.name == "limit" && o.value == Value::Integer(20)
            )));
        }
        _ => panic!("expected command input"),
    }
    assert_eq!(result.feedback.len(), 1);
}

#[test]
fn leaves_in_range_limit_untouched() {
    let result = evaluate(&bash_call("gh run list --limit 5"), &[cap_limit_policy()]);
    assert_eq!(result.decision, Decision::Allow);
    assert!(result.effective_call.is_none());
}

#[test]
fn denies_forbidden_command() {
    let policy = Policy {
        id: "no-rm".into(),
        name: "block rm".into(),
        priority: 100,
        scope: Scope::Global,
        matcher: Matcher::Command(CommandMatcher { executable: Some("rm".into()), subcommand: None }),
        rules: vec![Rule {
            id: "deny-rm".into(),
            condition: Condition::All(vec![]),
            action: Action::Deny,
            feedback: Some(FeedbackSpec {
                code: "FORBIDDEN_COMMAND".into(),
                severity: Severity::Error,
                message: Template("rm is forbidden".into()),
                guidance: vec![],
                retry: RetryPolicy::Never,
                expose_rule: true,
            }),
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("rm -rf foo"), &[policy]);
    assert_eq!(result.decision, Decision::Deny);
    assert_eq!(result.feedback.len(), 1);
}

#[test]
fn deny_wins_over_rewrite() {
    let rewrite = Policy {
        id: "cap".into(),
        name: "cap".into(),
        priority: 100,
        scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(),
            condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Set {
                target: Target::Argument { name: "limit".into() },
                value: Expr::Literal(Value::Integer(1)),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let deny = Policy {
        id: "block".into(),
        name: "block".into(),
        priority: 50,
        scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "d".into(),
            condition: Condition::All(vec![]),
            action: Action::Deny,
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list --limit 100"), &[rewrite, deny]);
    assert_eq!(result.decision, Decision::Deny);
    assert!(result.effective_call.is_none());
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cargo test --test eval`
Expected: FAIL — `eval` module does not exist.

- [ ] **Step 3: Write src/eval.rs**

```rust
//! Evaluator: ToolCall AST + Policy IR → EvaluationResult.

use crate::ast::*;
use crate::policy::*;
use serde::{Deserialize, Serialize};
use std::cmp::Ordering;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Decision {
    Allow,
    Deny,
    Rewrite,
    Ask,
    Warn,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EvaluationResult {
    pub decision: Decision,
    pub matched_policies: Vec<PolicyMatch>,
    pub transformations: Vec<Transformation>,
    pub feedback: Vec<Feedback>,
    pub effective_call: Option<ToolCall>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PolicyMatch {
    pub policy: PolicyId,
    pub rule: RuleId,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Transformation {
    pub op: RewriteOp,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Feedback {
    pub spec: FeedbackSpec,
}

pub fn evaluate(call: &ToolCall, policies: &[Policy]) -> EvaluationResult {
    let mut sorted: Vec<&Policy> = policies.iter().collect();
    sorted.sort_by(|a, b| b.priority.cmp(&a.priority));

    let mut matched_policies = Vec::new();
    let mut transformations = Vec::new();
    let mut feedback = Vec::new();
    let mut denied = false;
    let mut rewritten = false;
    let mut warned = false;

    for policy in sorted {
        if !matches(&policy.matcher, call) {
            continue;
        }
        for rule in &policy.rules {
            if !eval_condition(&rule.condition, call) {
                continue;
            }
            matched_policies.push(PolicyMatch {
                policy: policy.id.clone(),
                rule: rule.id.clone(),
            });
            match &rule.action {
                Action::Allow => {}
                Action::Deny => {
                    denied = true;
                    if let Some(f) = &rule.feedback {
                        feedback.push(Feedback { spec: f.clone() });
                    }
                }
                Action::Rewrite(ops) => {
                    rewritten = true;
                    for op in ops {
                        transformations.push(Transformation { op: op.clone() });
                    }
                }
                Action::Warn(f) => {
                    warned = true;
                    feedback.push(Feedback { spec: f.clone() });
                }
                Action::Ask(_) | Action::Transform(_) | Action::Constrain(_) => {
                    // placeholders — no-op in v0.1
                }
            }
        }
    }

    let decision = if denied {
        Decision::Deny
    } else if rewritten {
        Decision::Rewrite
    } else if warned {
        Decision::Warn
    } else {
        Decision::Allow
    };

    let effective_call = if rewritten {
        let mut new_call = call.clone();
        apply_rewrites(&mut new_call, &transformations);
        Some(new_call)
    } else {
        None
    };

    EvaluationResult {
        decision,
        matched_policies,
        transformations,
        feedback,
        effective_call,
    }
}

fn matches(matcher: &Matcher, call: &ToolCall) -> bool {
    match matcher {
        Matcher::All(ms) => ms.iter().all(|m| matches(m, call)),
        Matcher::Any(ms) => ms.iter().any(|m| matches(m, call)),
        Matcher::Not(m) => !matches(m, call),
        Matcher::Tool(t) => call.tool.name == t.name,
        Matcher::Command(cm) => {
            let ToolInput::Command(cmd) = &call.input else {
                return false;
            };
            if let Some(exe) = &cm.executable {
                if cmd.executable != *exe {
                    return false;
                }
            }
            if let Some(sub) = &cm.subcommand {
                match first_positional(cmd) {
                    Some(Value::String(s)) if s == sub => {}
                    _ => return false,
                }
            }
            true
        }
        Matcher::Context(_) => true, // placeholder — v0.2
    }
}

fn first_positional(cmd: &Command) -> Option<Value> {
    cmd.arguments.iter().find_map(|a| match a {
        Argument::Positional(v) => Some(v.clone()),
        _ => None,
    })
}

fn eval_condition(cond: &Condition, call: &ToolCall) -> bool {
    match cond {
        Condition::All(cs) => cs.iter().all(|c| eval_condition(c, call)),
        Condition::Any(cs) => cs.iter().any(|c| eval_condition(c, call)),
        Condition::Not(c) => !eval_condition(c, call),
        Condition::Compare { lhs, op, rhs } => {
            let l = eval_expr(lhs, call);
            let r = eval_expr(rhs, call);
            compare(&l, op, &r)
        }
        Condition::Exists(_) | Condition::Matches { .. } | Condition::In { .. } => false, // v0.2
    }
}

fn eval_expr(expr: &Expr, call: &ToolCall) -> Value {
    match expr {
        Expr::Literal(v) => v.clone(),
        Expr::ToolName => Value::String(call.tool.name.clone()),
        Expr::Executable => match &call.input {
            ToolInput::Command(c) => Value::String(c.executable.clone()),
            _ => Value::Null,
        },
        Expr::Argument { name } => match &call.input {
            ToolInput::Command(c) => find_option(c, name),
            _ => Value::Null,
        },
        Expr::Positional { index } => match &call.input {
            ToolInput::Command(c) => positional(c, *index),
            _ => Value::Null,
        },
        Expr::Environment { name } => match &call.input {
            ToolInput::Command(c) => c
                .environment
                .iter()
                .find(|e| &e.name == name)
                .map(|e| e.value.clone())
                .unwrap_or(Value::Null),
            _ => Value::Null,
        },
        Expr::WorkingDirectory => match &call.input {
            ToolInput::Command(c) => match &c.working_directory {
                Some(p) => Value::Path(p.clone()),
                None => Value::Null,
            },
            _ => Value::Null,
        },
        Expr::Arguments => Value::Null,           // v0.2
        Expr::Context { .. } => Value::Null,      // v0.2
        Expr::Function { .. } => Value::Null,     // v0.2
    }
}

fn find_option(cmd: &Command, name: &str) -> Value {
    cmd.arguments
        .iter()
        .find_map(|a| match a {
            Argument::Option(o) if o.name == name => Some(o.value.clone()),
            _ => None,
        })
        .unwrap_or(Value::Null)
}

fn positional(cmd: &Command, index: usize) -> Value {
    let mut i = 0;
    for a in &cmd.arguments {
        if let Argument::Positional(v) = a {
            if i == index {
                return v.clone();
            }
            i += 1;
        }
    }
    Value::Null
}

fn compare(l: &Value, op: &CompareOp, r: &Value) -> bool {
    let ord = match (l, r) {
        (Value::Integer(a), Value::Integer(b)) => Some(a.cmp(b)),
        (Value::Float(a), Value::Float(b)) => a.partial_cmp(b),
        (Value::Integer(a), Value::Float(b)) => (*a as f64).partial_cmp(b),
        (Value::Float(a), Value::Integer(b)) => a.partial_cmp(&(*b as f64)),
        (Value::String(a), Value::String(b)) => Some(a.cmp(b)),
        (Value::Boolean(a), Value::Boolean(b)) => Some(a.cmp(b)),
        _ => None,
    };
    let Some(ord) = ord else {
        return false;
    };
    match op {
        CompareOp::Eq => ord == Ordering::Equal,
        CompareOp::Ne => ord != Ordering::Equal,
        CompareOp::Gt => ord == Ordering::Greater,
        CompareOp::Ge => ord != Ordering::Less,
        CompareOp::Lt => ord == Ordering::Less,
        CompareOp::Le => ord != Ordering::Greater,
    }
}

fn apply_rewrites(call: &mut ToolCall, transformations: &[Transformation]) {
    // Evaluate all value expressions first (immutable borrow), then mutate.
    let call_ref: &ToolCall = call;
    let values: Vec<Value> = transformations
        .iter()
        .map(|t| match &t.op {
            RewriteOp::Set { value, .. } | RewriteOp::Replace { value, .. } | RewriteOp::Insert { value, .. } => {
                eval_expr(value, call_ref)
            }
            RewriteOp::Remove { .. } => Value::Null,
        })
        .collect();

    let ToolInput::Command(cmd) = &mut call.input else {
        return;
    };
    for (t, v) in transformations.iter().zip(values.iter()) {
        match &t.op {
            RewriteOp::Set { target, .. } | RewriteOp::Replace { target, .. } => {
                set_value(cmd, target, v.clone());
            }
            RewriteOp::Remove { target } => remove(cmd, target),
            RewriteOp::Insert { target, .. } => insert(cmd, target, v.clone()),
        }
    }
}

fn set_value(cmd: &mut Command, target: &Target, value: Value) {
    match target {
        Target::Argument { name } => {
            for a in &mut cmd.arguments {
                if let Argument::Option(o) = a {
                    if &o.name == name {
                        o.value = value.clone();
                        return;
                    }
                }
            }
            cmd.arguments.push(Argument::Option(OptionArg {
                name: name.clone(),
                value,
                syntax: OptionSyntax::Separate,
            }));
        }
        Target::Positional { index } => set_positional(cmd, *index, value),
        Target::Environment { name } => {
            for e in &mut cmd.environment {
                if &e.name == name {
                    e.value = value.clone();
                    return;
                }
            }
            cmd.environment.push(EnvAssignment { name: name.clone(), value });
        }
        Target::Executable => {
            if let Value::String(s) = value {
                cmd.executable = s;
            }
        }
        Target::WorkingDirectory => {
            if let Value::Path(p) = value {
                cmd.working_directory = Some(p);
            }
        }
    }
}

fn remove(cmd: &mut Command, target: &Target) {
    match target {
        Target::Argument { name } => {
            cmd.arguments.retain(|a| match a {
                Argument::Option(o) => o.name != *name,
                _ => true,
            });
        }
        Target::Positional { index } => remove_positional(cmd, *index),
        Target::Environment { name } => {
            cmd.environment.retain(|e| e.name != *name);
        }
        Target::Executable => {}
        Target::WorkingDirectory => {
            cmd.working_directory = None;
        }
    }
}

fn insert(cmd: &mut Command, target: &Target, value: Value) {
    match target {
        Target::Argument { name } => {
            cmd.arguments.push(Argument::Option(OptionArg {
                name: name.clone(),
                value,
                syntax: OptionSyntax::Separate,
            }));
        }
        Target::Positional { index } => insert_positional(cmd, *index, value),
        Target::Environment { name } => {
            cmd.environment.push(EnvAssignment { name: name.clone(), value });
        }
        Target::Executable => {
            if let Value::String(s) = value {
                cmd.executable = s;
            }
        }
        Target::WorkingDirectory => {
            if let Value::Path(p) = value {
                cmd.working_directory = Some(p);
            }
        }
    }
}

fn set_positional(cmd: &mut Command, index: usize, value: Value) {
    let mut i = 0;
    for a in &mut cmd.arguments {
        if let Argument::Positional(v) = a {
            if i == index {
                *v = value.clone();
                return;
            }
            i += 1;
        }
    }
}

fn remove_positional(cmd: &mut Command, index: usize) {
    let mut i = 0;
    cmd.arguments.retain(|a| {
        if let Argument::Positional(_) = a {
            let keep = i != index;
            i += 1;
            keep
        } else {
            true
        }
    });
}

fn insert_positional(cmd: &mut Command, index: usize, value: Value) {
    let pos_count = cmd
        .arguments
        .iter()
        .filter(|a| matches!(a, Argument::Positional(_)))
        .count();
    if index >= pos_count {
        cmd.arguments.push(Argument::Positional(value));
    } else {
        let mut i = 0;
        let mut insert_at = cmd.arguments.len();
        for (j, a) in cmd.arguments.iter().enumerate() {
            if let Argument::Positional(_) = a {
                if i == index {
                    insert_at = j;
                    break;
                }
                i += 1;
            }
        }
        cmd.arguments.insert(insert_at, Argument::Positional(value));
    }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cargo test --test eval`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add narness-policy/src/eval.rs narness-policy/tests/eval.rs
git commit -m "feat(narness-policy): add evaluator" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: CLI (`inspect` and `eval`)

**Files:**
- Modify: `narness-policy/src/main.rs` (replace stub)
- Test: `narness-policy/tests/cli.rs`

- [ ] **Step 1: Write the failing integration test**

```rust
use std::process::Command;

const POLICY_JSON: &str = r#"[{
  "id": "cap-limit",
  "name": "cap limit",
  "priority": 100,
  "scope": "Global",
  "matcher": { "Command": { "executable": "gh", "subcommand": "run" } },
  "rules": [{
    "id": "r1",
    "condition": { "Compare": { "lhs": { "Argument": { "name": "limit" } }, "op": "Gt", "rhs": { "Literal": { "Integer": 20 } } } },
    "action": { "Rewrite": [{ "Set": { "target": { "Argument": { "name": "limit" } }, "value": { "Literal": { "Integer": 20 } } } }] },
    "feedback": { "code": "ARGUMENT_OUT_OF_RANGE", "severity": "Warning", "message": "cap", "guidance": [], "retry": "Never", "expose_rule": false }
  }],
  "metadata": null
}]"#;

#[test]
fn inspect_prints_ast_json() {
    let out = Command::new(env!("CARGO_BIN_EXE_narness-policy"))
        .args(["inspect", "gh run list --limit 100"])
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8(out.stdout).unwrap();
    let v: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(v["commands"][0]["executable"], "gh");
}

#[test]
fn eval_applies_policy() {
    let path = format!("{}/policy.json", env!("CARGO_TARGET_TMPDIR"));
    std::fs::write(&path, POLICY_JSON).unwrap();
    let out = Command::new(env!("CARGO_BIN_EXE_narness-policy"))
        .args(["eval", "gh run list --limit 100", "--policy", &path])
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8(out.stdout).unwrap();
    let v: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(v["decision"], "Rewrite");
    assert_eq!(
        v["effective_call"]["input"]["Command"]["arguments"][2]["Option"]["value"],
        serde_json::json!({ "Integer": 20 })
    );
}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cargo test --test cli`
Expected: FAIL — `main.rs` is still the stub, so `inspect`/`eval` are unknown.

- [ ] **Step 3: Write src/main.rs**

```rust
use clap::{Parser, Subcommand};
use narness_policy::ast::{Pipeline, ToolCall, ToolInput, ToolRef};
use narness_policy::eval::evaluate;
use narness_policy::parse::parse_bash;
use narness_policy::policy::Policy;
use std::process::ExitCode;

#[derive(Parser)]
#[command(name = "narness-policy", version, about = "Narness policy engine")]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Parse a command string and print its AST as JSON.
    Inspect {
        /// The command string to parse, e.g. "gh run list --limit 100"
        command: String,
    },
    /// Parse a command and evaluate it against a policy file (JSON Vec<Policy>).
    Eval {
        /// The command string to parse and evaluate
        command: String,
        /// Path to a JSON file holding a list of policies
        #[arg(long)]
        policy: String,
    },
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    match cli.command {
        Command::Inspect { command } => match parse_bash(&command) {
            Ok(pipeline) => {
                println!("{}", serde_json::to_string_pretty(&pipeline).unwrap());
                ExitCode::SUCCESS
            }
            Err(e) => {
                eprintln!("parse error: {e}");
                ExitCode::from(2)
            }
        },
        Command::Eval { command, policy } => {
            let call = match parse_bash(&command) {
                Ok(pipeline) => make_tool_call(pipeline),
                Err(e) => {
                    eprintln!("parse error: {e}");
                    return ExitCode::from(2);
                }
            };
            let policies: Vec<Policy> = match std::fs::read_to_string(&policy) {
                Ok(s) => match serde_json::from_str(&s) {
                    Ok(p) => p,
                    Err(e) => {
                        eprintln!("policy parse error: {e}");
                        return ExitCode::from(2);
                    }
                },
                Err(e) => {
                    eprintln!("cannot read policy file {}: {e}", policy);
                    return ExitCode::from(2);
                }
            };
            let result = evaluate(&call, &policies);
            println!("{}", serde_json::to_string_pretty(&result).unwrap());
            ExitCode::SUCCESS
        }
    }
}

fn make_tool_call(pipeline: Pipeline) -> ToolCall {
    // v0.1 evaluates the first command of a pipeline (documented in the spec).
    let cmd = pipeline.commands.into_iter().next().unwrap();
    ToolCall {
        id: "cli".to_string(),
        tool: ToolRef { name: "bash".to_string(), version: None },
        input: ToolInput::Command(cmd),
        context: Default::default(),
        metadata: Default::default(),
    }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cargo test --test cli`
Expected: all PASS.

- [ ] **Step 5: Run the full suite**

Run: `cargo test`
Expected: all tests across `ast`, `parse`, `policy`, `eval`, `cli` pass.

- [ ] **Step 6: Commit**

```bash
git add narness-policy/src/main.rs narness-policy/tests/cli.rs
git commit -m "feat(narness-policy): add inspect and eval CLI" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-review notes

- **Spec coverage:** AST (§4) → Task 2; parser + coercion (§5) → Task 3; Policy IR (§6) → Task 4; evaluator + decision merge (§7) → Task 5; CLI `inspect`/`eval` (§8) → Task 6. Value coercion policy (§5.1) and original+effective preservation (§7.2) are exercised by the parser and evaluator tests respectively.
- **v0.2 items intentionally not implemented:** YAML DSL, `check` hook adapter, `&&`/`||`, `Duration`/`Ip`/`Cidr`/`List` coercion, `Context` matcher, `Matches`/`In` conditions, `Function` expr, `Constrain`/`Transform` actions, `FileOperation`/`HttpRequest`. These are represented as placeholder types or return `false`/`Null` and are listed in the spec's §10.
- **Known v0.1 limitations to keep in mind (documented, not bugs):** short-option bundling (`-rf`) is parsed as `ShortAttached`; `--flag positional` is parsed as `Option` (a flag followed by a positional is ambiguous without a schema); negative-number option values are not handled. These are all consequences of the no-schema design and resolve in v0.2.
