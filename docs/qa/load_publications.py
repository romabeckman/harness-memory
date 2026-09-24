"""Publish repeatable documentation snapshots through the REST API, without an LLM.

Edit the defaults below or pass the equivalent command-line options. One copy
creates one publication and snapshot per environment. Reuse RUN_ID to resume a
partially completed run against the same unchanged docs directory.
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


# Load-test defaults. The token comes from an environment variable, never this file.
DOCS_ROOT = Path(".")  # Directory containing docs/
API_URL = "http://127.0.0.1:8080"
PROJECT_KEY = "default"  # Must exist in the target API; use search_projects to confirm.
ENVIRONMENTS = ("production",)
SNAPSHOT_COPIES = 1000  # Copies per environment; 10_000 is supported.
TENANT_ID = None  # Required when using API_ADMIN_TOKEN.
RUN_ID = None  # Set a fixed value to resume an interrupted run.
TOKEN_ENV = "HARNESS_MEMORY_API_KEY"
REQUEST_TIMEOUT_SECONDS = 120

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
    "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
    "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.",
    "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum.",
    "Excepteur sint occaecat cupidatat non proident, sunt in culpa.",
)
MAX_METADATA_BYTES = 64 * 1024
CONTENT_CHUNK_BYTES = 48 * 1024
ALLOWED_RELATIONS = {
    "part_of", "owned_by", "provides", "consumes", "depends_on", "publishes",
    "subscribes_to", "implements", "references", "tested_by", "child_of",
    "defines", "applies_to", "supersedes",
}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def chunks(value, limit=CONTENT_CHUNK_BYTES):
    """Split text on character boundaries while respecting UTF-8 byte limits."""
    current = []
    size = 0
    for character in value:
        width = len(character.encode("utf-8"))
        if current and size + width > limit:
            yield "".join(current)
            current = []
            size = 0
        current.append(character)
        size += width
    if current:
        yield "".join(current)


def relation(source, kind, target):
    return {
        "ref": "load:" + digest(f"{source}|{kind}|{target}")[:40],
        "source_entity_key": source,
        "target_entity_key": target,
        "type": kind,
        "provenance": "declared",
    }


def load_docs(root):
    docs = root / "docs"
    if not docs.is_dir():
        raise ValueError(f"Missing docs directory: {docs}")
    graph_file = docs / ".graph.json"
    index = json.loads(graph_file.read_text(encoding="utf-8")) if graph_file.exists() else {"nodes": [], "edges": []}
    if not isinstance(index, dict) or not isinstance(index.get("nodes"), list) or not isinstance(index.get("edges"), list):
        raise ValueError("docs/.graph.json must contain nodes and edges arrays")
    indexed = {node["path"]: node for node in index["nodes"] if isinstance(node, dict) and isinstance(node.get("path"), str)}
    entities = []
    relations = []
    paths = {}
    for file in sorted(docs.rglob("*.md")):
        relative = file.relative_to(root).as_posix()
        if "workflow" in file.relative_to(docs).parts:
            continue
        content = file.read_text(encoding="utf-8")
        node = indexed.get(relative, {})
        category = "adr" if relative.startswith("docs/adr/") else "feature" if relative.startswith("docs/feature/") else "document"
        frontmatter_id = re.search(r'^node_id:\s*["\']?([^"\'\r\n]+)', content, re.MULTILINE)
        key = node.get("id") or (frontmatter_id.group(1).strip() if frontmatter_id else f"{category}:{digest(relative)[:24]}")
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = node.get("title") or (title_match.group(1) if title_match else file.name)
        if len(key) > 255 or len(title) > 255:
            raise ValueError(f"Entity key or title exceeds 255 characters: {relative}")
        paths[key] = relative
        base = {"path": relative, "content_sha256": digest(content), "lifecycle": "active"}
        parts = list(chunks(content, 4000))
        if len(parts) == 1:
            base["content"] = content
        else:
            base["content_parts"] = []
        entities.append({"key": key, "type": category, "name": title, "metadata": base})
        if len(parts) > 1:
            for number, part in enumerate(parts):
                section_key = f"document_section:{digest(f'{key}|{number}|{part}')[:40]}"
                base["content_parts"].append(section_key)
                entities.append({"key": section_key, "type": "document_section", "name": f"{title} ({number + 1})"[:255],
                                 "metadata": {"path": relative, "document_key": key, "index": number,
                                              "content": part, "content_sha256": digest(part)}})
                relations.append(relation(section_key, "part_of", key))
    if not entities:
        raise ValueError(f"No Markdown files found in {docs}")
    if len({item["key"] for item in entities}) != len(entities):
        raise ValueError("Duplicate entity keys in documentation")
    for edge in index["edges"]:
        if not isinstance(edge, dict):
            continue
        source, target, kind = edge.get("source"), edge.get("target"), edge.get("relation")
        if source in paths and target in paths and kind in ALLOWED_RELATIONS:
            relations.append(relation(source, kind, target))
    refs = set()
    unique_relations = []
    for item in relations:
        if item["ref"] not in refs:
            refs.add(item["ref"])
            unique_relations.append(item)
    evidence = [{"source": paths.get(item["source_entity_key"], "docs/.graph.json"),
                 "relation_ref": item["ref"]} for item in unique_relations]
    if len(entities) > 10_000 or len(unique_relations) > 50_000:
        raise ValueError("Documentation graph exceeds per-snapshot entity/relation limits")
    return entities, unique_relations, evidence, index


def publication_payload(entities, relations, evidence, project, environment, tenant, run_id, copy_number,
                        graph_index=None):
    changed = []
    for entity in entities:
        item = {**entity, "metadata": dict(entity["metadata"])}
        metadata = item["metadata"]
        seed = int(digest(f"{run_id}|{environment}|{copy_number}|{item['key']}")[:16], 16)
        phrase = random.Random(seed).choice(LOREM)
        suffix = f"\n\n{phrase} Load copy {copy_number}; seed {seed:016x}."
        if "content" in metadata:
            metadata["content"] += suffix
            metadata["content_sha256"] = digest(metadata["content"])
        else:
            metadata["load_note"] = suffix.strip()
        if len(json.dumps(metadata, ensure_ascii=False).encode("utf-8")) > MAX_METADATA_BYTES:
            raise ValueError(f"Entity metadata exceeds 64 KiB: {item['key']}")
        changed.append(item)
    by_key = {item["key"]: item for item in changed}
    for item in changed:
        parts = item["metadata"].get("content_parts")
        if parts:
            item["metadata"]["content_sha256"] = digest("".join(
                by_key[key]["metadata"]["content"] for key in parts
            ))
    snapshot_metadata = dict(graph_index or {})
    snapshot_metadata.update({"load_run_id": run_id, "load_copy": copy_number})
    if len(json.dumps(snapshot_metadata, ensure_ascii=False).encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError("Snapshot metadata exceeds 64 KiB; reduce docs/.graph.json")
    payload = {
        "project_key": project,
        "environment": environment,
        "deployment_id": f"load-{run_id}-{environment}-{copy_number}",
        "version": f"{run_id[:14]}.{copy_number:05d}",
        "metadata": snapshot_metadata,
        "entities": changed,
        "relations": relations,
        "evidence": evidence,
    }
    if tenant:
        payload["tenant_id"] = tenant
    return payload


def publish(url, token, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url.rstrip("/") + "/v1/knowledge-publications", body,
        {"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-root", type=Path, default=DOCS_ROOT, help="Directory containing docs/")
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--project", default=PROJECT_KEY)
    parser.add_argument("--environments", nargs="+", default=ENVIRONMENTS)
    parser.add_argument("--count", type=int, default=SNAPSHOT_COPIES, help="Snapshot copies per environment")
    parser.add_argument("--tenant-id", default=TENANT_ID)
    parser.add_argument("--run-id", default=RUN_ID, help="Stable ID for resuming; defaults to a new ID")
    parser.add_argument("--dry-run", action="store_true", help="Build one sample payload; send nothing")
    args = parser.parse_args(argv)
    if args.count < 1 or not args.project.strip() or not args.environments:
        parser.error("count must be positive; project and environments must be nonempty")
    if len(set(args.environments)) != len(args.environments):
        parser.error("environments must be unique")
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + uuid4().hex[:12]
    if not re.fullmatch(r"\d{14}[A-Za-z0-9_-]{0,66}", run_id):
        parser.error("run-id must start with 14 timestamp digits, then use up to 66 letters, digits, underscores or hyphens")
    token = os.environ.get(TOKEN_ENV)
    if not args.dry_run and not token:
        parser.error(f"Set {TOKEN_ENV} to a token with memory:publish")
    entities, relations, evidence, graph_index = load_docs(args.docs_root.resolve())
    total = args.count * len(args.environments)
    print(f"run_id={run_id} publications={total} entities_per_snapshot={len(entities)} "
          f"relations_per_snapshot={len(relations)} evidence_per_snapshot={len(evidence)}", flush=True)
    if args.dry_run:
        sample = publication_payload(entities, relations, evidence, args.project,
                                     args.environments[0], args.tenant_id, run_id, 1, graph_index)
        print(f"dry_run payload_bytes={len(json.dumps(sample).encode('utf-8'))}")
        return 0
    completed = 0
    try:
        for number in range(1, args.count + 1):
            for environment in args.environments:
                payload = publication_payload(entities, relations, evidence, args.project,
                                              environment, args.tenant_id, run_id, number, graph_index)
                result = publish(args.api_url, token, payload)
                if result.get("status") not in {"ACTIVATED", "ALREADY_PUBLISHED"}:
                    raise ValueError(f"Unexpected publication response: {result}")
                completed += 1
                print(f"{completed}/{total} {environment} copy={number} "
                      f"status={result['status']} snapshot_id={result['snapshot_id']}", flush=True)
    except (urllib.error.HTTPError, urllib.error.URLError, ValueError, KeyError) as error:
        detail = error.read().decode("utf-8", errors="replace") if isinstance(error, urllib.error.HTTPError) else str(error)
        print(f"Stopped after {completed}/{total}. run_id={run_id}. Error: {detail}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
