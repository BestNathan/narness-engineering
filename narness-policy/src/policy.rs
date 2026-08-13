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
