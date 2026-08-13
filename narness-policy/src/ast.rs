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
