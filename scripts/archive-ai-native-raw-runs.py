#!/usr/bin/env python3
"""Create a deterministic archive of the sealed formal run collection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from typing import Any


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def zip_write(zf: zipfile.ZipFile, arcname: str, data: bytes) -> None:
    info = zipfile.ZipInfo(arcname, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    zf.writestr(info, data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", required=True, type=Path)
    ap.add_argument("--collection-manifest", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()

    runs_root = args.runs_root.resolve()
    collection_path = args.collection_manifest.resolve()
    output = args.output.resolve()
    collection = load(collection_path)

    if collection.get("complete") is not True:
        raise RuntimeError("collection manifest is not complete")

    selected: dict[str, Path] = {}

    collection_start = runs_root / "_collection" / "collection-start.json"
    if not collection_start.exists():
        raise RuntimeError("collection-start.json is missing")
    selected["_collection/collection-start.json"] = collection_start
    selected["_collection/collection-manifest.json"] = collection_path

    for row in collection.get("runs", []):
        run_id = row["run_id"]
        run_dir = runs_root / run_id
        seal_path = run_dir / "seal.json"
        if not seal_path.exists():
            raise RuntimeError(f"{run_id}: seal.json missing")
        seal_hash = sha256_file(seal_path)
        if seal_hash != row.get("run_seal_sha256"):
            raise RuntimeError(
                f"{run_id}: seal hash differs from collection manifest"
            )

        seal = load(seal_path)
        selected[f"{run_id}/seal.json"] = seal_path

        for name, expected_hash in sorted((seal.get("artifacts") or {}).items()):
            path = run_dir / name
            if not path.exists():
                raise RuntimeError(f"{run_id}: sealed artifact missing: {name}")
            actual = sha256_file(path)
            if actual != expected_hash:
                raise RuntimeError(
                    f"{run_id}: sealed artifact hash mismatch: {name}"
                )
            selected[f"{run_id}/{name}"] = path

        review_hash = row.get("review_sha256")
        review_path = run_dir / "review.json"
        if review_hash:
            if not review_path.exists():
                raise RuntimeError(f"{run_id}: reviewed run has no review.json")
            if sha256_file(review_path) != review_hash:
                raise RuntimeError(f"{run_id}: review hash mismatch")
            selected[f"{run_id}/review.json"] = review_path
        elif review_path.exists():
            raise RuntimeError(
                f"{run_id}: review.json exists but is not represented by collection manifest"
            )

    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing raw archive: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    file_manifest: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        for arcname, path in sorted(selected.items()):
            data = path.read_bytes()
            zip_write(zf, arcname, data)
            file_manifest[arcname] = {
                "sha256": sha256_bytes(data),
                "bytes": len(data),
            }

    content_material = "\n".join(
        f"{name}:{item['sha256']}:{item['bytes']}"
        for name, item in sorted(file_manifest.items())
    ).encode("utf-8")

    archive_manifest = {
        "schema_version": 1,
        "experiment_id": collection["experiment_id"],
        "benchmark_revision": collection["benchmark_revision"],
        "benchmark_definition_sha": collection["benchmark_definition_sha"],
        "analysis_revision": collection.get("analysis_revision"),
        "analysis_definition_sha": collection.get("analysis_definition_sha"),
        "formal_plan_id": collection.get("formal_plan_id"),
        "formal_plan_sha256": collection.get("formal_plan_sha256"),
        "collection_digest_sha256": collection["collection_digest_sha256"],
        "collection_manifest_sha256": sha256_file(collection_path),
        "archiver_file_sha256": sha256_file(Path(__file__).resolve()),
        "content_set_digest_sha256": hashlib.sha256(content_material).hexdigest(),
        "archive_filename": output.name,
        "archive_sha256": sha256_file(output),
        "archive_bytes": output.stat().st_size,
        "file_count": len(file_manifest),
        "uncompressed_bytes": sum(
            item["bytes"] for item in file_manifest.values()
        ),
        "files": file_manifest,
        "policy": (
            "Archive contains only the completed collection-start record, final "
            "collection manifest, each run seal, artifacts named by each run seal, "
            "and represented failure reviews. Quarantined/incomplete runs and "
            "unsealed extras are intentionally excluded."
        ),
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(
        json.dumps(archive_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("Deterministic raw-run archive ready")
    print(f"  archive: {output}")
    print(f"  sha256: {archive_manifest['archive_sha256']}")
    print(f"  files: {archive_manifest['file_count']}")
    print(f"  manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
