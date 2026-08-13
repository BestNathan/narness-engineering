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

#[test]
fn handles_single_quotes() {
    let p = parse_bash("echo 'hello world'").unwrap();
    assert_eq!(
        p.commands[0].arguments,
        vec![Argument::Positional(Value::String("hello world".into()))]
    );
}

#[test]
fn coerces_booleans() {
    let p = parse_bash("cmd --flag true --other false").unwrap();
    assert_eq!(
        p.commands[0].arguments,
        vec![
            Argument::Option(OptionArg { name: "flag".into(), value: Value::Boolean(true), syntax: OptionSyntax::Separate }),
            Argument::Option(OptionArg { name: "other".into(), value: Value::Boolean(false), syntax: OptionSyntax::Separate }),
        ]
    );
}

#[test]
fn rejects_unterminated_quote() {
    assert!(parse_bash("echo \"unterminated").is_err());
}

#[test]
fn rejects_empty_command() {
    assert!(parse_bash("").is_err());
    assert!(parse_bash("   ").is_err());
}

#[test]
fn handles_backslash_escape() {
    let p = parse_bash("echo foo\\ bar").unwrap();
    assert_eq!(
        p.commands[0].arguments,
        vec![Argument::Positional(Value::String("foo bar".into()))]
    );
}
