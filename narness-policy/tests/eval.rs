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

#[test]
fn removes_option() {
    let policy = Policy {
        id: "strip".into(), name: "strip".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(),
            condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Remove {
                target: Target::Argument { name: "limit".into() },
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list --limit 100"), &[policy]);
    assert_eq!(result.decision, Decision::Rewrite);
    match &result.effective_call.as_ref().unwrap().input {
        ToolInput::Command(c) => {
            assert!(!c.arguments.iter().any(|a| matches!(a, Argument::Option(o) if o.name == "limit")));
        }
        _ => panic!("expected command input"),
    }
}

#[test]
fn inserts_option() {
    let policy = Policy {
        id: "add".into(), name: "add".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(),
            condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Insert {
                target: Target::Argument { name: "json".into() },
                value: Expr::Literal(Value::String("status".into())),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list"), &[policy]);
    assert_eq!(result.decision, Decision::Rewrite);
    match &result.effective_call.as_ref().unwrap().input {
        ToolInput::Command(c) => {
            assert!(c.arguments.iter().any(|a| matches!(
                a, Argument::Option(o) if o.name == "json" && o.value == Value::String("status".into())
            )));
        }
        _ => panic!("expected command input"),
    }
}

#[test]
fn replaces_option() {
    let policy = Policy {
        id: "replace".into(), name: "replace".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(),
            condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Replace {
                target: Target::Argument { name: "limit".into() },
                value: Expr::Literal(Value::Integer(5)),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list --limit 100"), &[policy]);
    assert_eq!(result.decision, Decision::Rewrite);
    match &result.effective_call.as_ref().unwrap().input {
        ToolInput::Command(c) => {
            assert!(c.arguments.iter().any(|a| matches!(
                a, Argument::Option(o) if o.name == "limit" && o.value == Value::Integer(5)
            )));
        }
        _ => panic!("expected command input"),
    }
}

#[test]
fn warns_and_adds_feedback() {
    let policy = Policy {
        id: "warn".into(), name: "warn".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(),
            condition: Condition::All(vec![]),
            action: Action::Warn(FeedbackSpec {
                code: "WARN".into(), severity: Severity::Warning,
                message: Template("heads up".into()), guidance: vec![],
                retry: RetryPolicy::Never, expose_rule: false,
            }),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list"), &[policy]);
    assert_eq!(result.decision, Decision::Warn);
    assert_eq!(result.feedback.len(), 1);
    assert!(result.effective_call.is_none());
}

#[test]
fn allows_unmatched_policy() {
    let policy = Policy {
        id: "no-rm".into(), name: "block rm".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::Command(CommandMatcher { executable: Some("rm".into()), subcommand: None }),
        rules: vec![Rule {
            id: "r".into(), condition: Condition::All(vec![]), action: Action::Deny, feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list"), &[policy]);
    assert_eq!(result.decision, Decision::Allow);
    assert!(result.effective_call.is_none());
    assert!(result.matched_policies.is_empty());
}

#[test]
fn sets_positional() {
    let policy = Policy {
        id: "p".into(), name: "p".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(), condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Set {
                target: Target::Positional { index: 1 },
                value: Expr::Literal(Value::String("list".into())),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run foo"), &[policy]);
    assert_eq!(result.decision, Decision::Rewrite);
    match &result.effective_call.as_ref().unwrap().input {
        ToolInput::Command(c) => {
            let pos: Vec<&String> = c.arguments.iter().filter_map(|a| match a {
                Argument::Positional(Value::String(s)) => Some(s),
                _ => None,
            }).collect();
            assert_eq!(pos, vec!["run", "list"]);
        }
        _ => panic!("expected command"),
    }
}

#[test]
fn sets_environment() {
    let policy = Policy {
        id: "e".into(), name: "e".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(), condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Set {
                target: Target::Environment { name: "FOO".into() },
                value: Expr::Literal(Value::String("bar".into())),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list"), &[policy]);
    match &result.effective_call.as_ref().unwrap().input {
        ToolInput::Command(c) => {
            assert!(c.environment.iter().any(|e| e.name == "FOO" && e.value == Value::String("bar".into())));
        }
        _ => panic!("expected command"),
    }
}

#[test]
fn sets_executable() {
    let policy = Policy {
        id: "x".into(), name: "x".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(), condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Set {
                target: Target::Executable,
                value: Expr::Literal(Value::String("echo".into())),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list"), &[policy]);
    match &result.effective_call.as_ref().unwrap().input {
        ToolInput::Command(c) => assert_eq!(c.executable, "echo"),
        _ => panic!("expected command"),
    }
}

#[test]
fn sets_working_directory() {
    let policy = Policy {
        id: "w".into(), name: "w".into(), priority: 100, scope: Scope::Global,
        matcher: Matcher::All(vec![]),
        rules: vec![Rule {
            id: "r".into(), condition: Condition::All(vec![]),
            action: Action::Rewrite(vec![RewriteOp::Set {
                target: Target::WorkingDirectory,
                value: Expr::Literal(Value::Path(PathExpr { raw: "/tmp".into(), normalized: None, absolute: true })),
            }]),
            feedback: None,
        }],
        metadata: PolicyMetadata,
    };
    let result = evaluate(&bash_call("gh run list"), &[policy]);
    match &result.effective_call.as_ref().unwrap().input {
        ToolInput::Command(c) => {
            assert_eq!(c.working_directory.as_ref().map(|p| p.raw.as_str()), Some("/tmp"));
        }
        _ => panic!("expected command"),
    }
}
