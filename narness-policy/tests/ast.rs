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
