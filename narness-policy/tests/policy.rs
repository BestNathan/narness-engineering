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

#[test]
fn defaults_fill_missing_fields() {
    let back: Policy = serde_json::from_str(r#"{"id":"x","matcher":{"All":[]}}"#).unwrap();
    assert_eq!(back.name, "");
    assert_eq!(back.priority, 0);
    assert_eq!(back.scope, Scope::Global);
    assert!(back.rules.is_empty());
}
