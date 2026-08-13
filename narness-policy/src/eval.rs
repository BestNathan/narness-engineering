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
                    if let Some(f) = &rule.feedback {
                        feedback.push(Feedback { spec: f.clone() });
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

    let effective_call = if rewritten && !denied {
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
                    Some(Value::String(s)) if s == *sub => {}
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
