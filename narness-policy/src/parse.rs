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

/// Parse a shell command string into a semantic [`Pipeline`].
///
/// # Known limitations (v0.1 — no type-hint schema)
///
/// - A `--flag` followed by a non-dash token is parsed as an `Option` that consumes
///   that token (e.g. `cmd --public repo` → `Option{name:"public", value:"repo"}`),
///   because without a schema we cannot distinguish a value-taking option from a flag.
/// - Bundled short flags are not supported: `-rf` parses as a single short-attached
///   option `Option{name:"r", value:"f"}` rather than two flags.
/// - Logical operators (`&&`, `||`) and the pipe `|` are only recognized when
///   surrounded by whitespace.
/// - Inside double quotes a backslash escapes *any* following character (bash only
///   treats `\` specially before `$`, `` ` ``, `"`, `\`, and newline).
/// - A negative-number positional (e.g. `echo -5`) parses as a short option, not a
///   `Positional(Integer(-5))`.
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
        let (arg, consumed) = classify_arg(tokens, idx);
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
