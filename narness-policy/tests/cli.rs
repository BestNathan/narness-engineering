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
