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
                println!("{}", serde_json::to_string_pretty(&pipeline).expect("serialize pipeline"));
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
            println!("{}", serde_json::to_string_pretty(&result).expect("serialize evaluation result"));
            ExitCode::SUCCESS
        }
    }
}

fn make_tool_call(pipeline: Pipeline) -> ToolCall {
    // v0.1 evaluates the first command of a pipeline (documented in the spec).
    let cmd = pipeline.commands.into_iter().next().expect("parsed pipeline has at least one command");
    ToolCall {
        id: "cli".to_string(),
        tool: ToolRef { name: "bash".to_string(), version: None },
        input: ToolInput::Command(cmd),
        context: Default::default(),
        metadata: Default::default(),
    }
}
