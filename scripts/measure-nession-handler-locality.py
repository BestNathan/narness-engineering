#!/usr/bin/env python3
"""Exact-SHA deterministic source retrieval experiment for Nession #1258.
NOT an AI-agent task / token or productivity comparison.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess

A = "6b7dcff69275b1e69ad6f8484240a41436db4cc5"
C = "696892d0cb003a507dde5f9b7087014db8f92e18"
PREFIX = "crates/nession-server/src/server/"
TASKS = [
 ("T01", "server.session.attach", "handle_client_session_attach", "server_session_attach_v1"),
 ("T02", "server.env.write", "handle_client_env_write", "server_env_write_v1"),
 ("T03", "server.agent.rename", "handle_client_agent_rename", "server_agent_rename_v1"),
 ("T04", "server.session.capture-preview", "handle_client_session_capture_preview", "server_session_capture_preview_v1"),
 ("T05", "server.session.relay.end", None, None),
]

def cmd(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout

def blob(repo, sha, path):
    return cmd(repo, "show", sha + ":" + path)

def exists(repo, sha, path):
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", sha + ":" + path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0

def measure(repo, sha, task, treatment):
    task_id, wire, method, leaf = task
    if leaf is None:
        paths = ([PREFIX + "handler/routes.rs", PREFIX + "websocket.rs"] if treatment
                 else [PREFIX + "handler.rs", PREFIX + "websocket.rs"])
        sources = {p: blob(repo, sha, p) for p in paths}
        if wire.encode() not in sources[paths[0]] or b"RELAY_END_WIRE" not in sources[paths[-1]]:
            raise AssertionError("relay.end ownership evidence missing")
        result = {"kind": "runtime-owner negative control",
                  "source_paths": paths, "test_paths": [], "owner_found": True,
                  "payload_bytes": sum(len(v) for v in sources.values()),
                  "closure_bytes": sum(len(v) for v in sources.values())}
    else:
        route = PREFIX + ("handler/routes.rs" if treatment else "handler.rs")
        impl = PREFIX + ("handler/" + leaf + ".rs" if treatment else "handler.rs")
        test_local = PREFIX + "handler/tests/" + leaf + ".rs"
        test = (test_local if treatment and exists(repo, sha, test_local)
                else PREFIX + ("handler/tests.rs" if treatment else "handler.rs"))
        implementation = blob(repo, sha, impl)
        route_source = blob(repo, sha, route)
        if ("async fn " + method + "(").encode() not in implementation:
            raise AssertionError(task_id + " handler was not found in " + impl)
        if wire.encode() not in route_source or method.encode() not in route_source:
            raise AssertionError(task_id + " route identity was not found")
        paths = list(dict.fromkeys(
            ([impl, route, test, PREFIX + "handler/mod.rs"] if treatment else [impl])))
        sources = {p: blob(repo, sha, p) for p in paths}
        result = {"kind": "versioned operation", "source_paths": [impl],
                  "test_paths": [test], "test_localized": test == test_local,
                  "owner_found": True, "payload_bytes": len(implementation),
                  "closure_bytes": sum(len(v) for v in sources.values())}
    result.update({"task": task_id, "unit": wire, "sha": sha,
                   "blobs_sha256": {p: hashlib.sha256(v).hexdigest() for p, v in sources.items()}})
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-repo", required=True, type=pathlib.Path)
    p.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = p.parse_args()
    repo = args.source_repo.resolve()
    for sha in [A, C]:
        if len(cmd(repo, "rev-parse", sha + "^{commit}").strip()) != 40:
            raise AssertionError("missing frozen source SHA " + sha)
    observations = []
    for task in TASKS:
        before = measure(repo, A, task, False)
        after = measure(repo, C, task, True)
        observations.append({"task": task[0], "baseline": before, "treatment": after,
                             "payload_byte_delta": before["payload_bytes"] - after["payload_bytes"],
                             "conservative_closure_byte_delta": before["closure_bytes"] - after["closure_bytes"]})
    units = observations[:4]
    summary = {
        "task_count": len(observations),
        "unit_count": len(units),
        "correct_owner_resolution_A": sum(x["baseline"]["owner_found"] for x in observations),
        "correct_owner_resolution_C": sum(x["treatment"]["owner_found"] for x in observations),
        "implementation_payload_bytes_A": sum(x["baseline"]["payload_bytes"] for x in units),
        "implementation_payload_bytes_C": sum(x["treatment"]["payload_bytes"] for x in units),
        "conservative_closure_bytes_A": sum(x["baseline"]["closure_bytes"] for x in units),
        "conservative_closure_bytes_C": sum(x["treatment"]["closure_bytes"] for x in units),
        "localized_tests_C": sum(x["treatment"]["test_localized"] for x in units),
    }
    result = {
        "schema_version": 1, "experiment_id": "nession-1258-source-locality-retrieval",
        "baseline_sha": A, "treatment_sha": C,
        "source": "Git blobs from immutable nession commits via git show",
        "protocol": "5 frozen tasks: 4 known Unit identities + relay.end exceptional runtime-owned negative control",
        "limitations": [
            "No LLM, coding agent, real task patches, token costs, or navigation durations were measured.",
            "Method names were supplied identically across snapshots; natural-language discovery and false-positive exploration were not tested.",
            "Source bytes of the selected paths are a retrieval surface proxy, not a causal engineering productivity estimate.",
            "Shared dependencies beyond the conservative closure might be needed for correct changes.",
        ],
        "summary": summary, "observations": observations,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output_dir / "observations.json"
    raw_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    report = [
        "# Nession #1258 bounded retrieval experiment",
        "",
        "Paired baseline/treatment Git-tree source retrieval, not an AI-agent productivity experiment.",
        "",
        "Baseline: " + A,
        "Treatment: " + C,
        "",
        "| Task | Baseline payload bytes | Treatment payload bytes | Baseline conservative closure | Treatment conservative closure | Localized treatment test? |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for x in observations:
        a, c = x["baseline"], x["treatment"]
        report.append("| " + x["task"] + " " + a["unit"] + " | " +
          str(a["payload_bytes"]) + " | " + str(c["payload_bytes"]) + " | " +
          str(a["closure_bytes"]) + " | " + str(c["closure_bytes"]) + " | " +
          str(c.get("test_localized", "N/A")) + " |")
    report.extend([
        "",
        "Versioned-operation payload bytes across 4 tasks: " +
          str(summary["implementation_payload_bytes_A"]) + " (A), " + str(summary["implementation_payload_bytes_C"]) + " (C).",
        "Conservative closure bytes: " + str(summary["conservative_closure_bytes_A"]) +
          " (A), " + str(summary["conservative_closure_bytes_C"]) + " (C).",
        "Relay.end is a negative control: active transition remains owned by websocket runtime.",
        "",
        "Interpretation: direct file addressability changed; this cannot establish inference/token/agent-time improvements.",
        "Complete source paths and per-blob SHA256 fingerprints are recorded in observations.json.",
        "",
    ])
    print("\n".join(report))
    print("observations_sha256=" + hashlib.sha256(raw_path.read_bytes()).hexdigest())
    (args.output_dir / "report.md").write_text("\n".join(report))

if __name__ == "__main__":
    main()
