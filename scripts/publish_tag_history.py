"""Replay Git tags into a LOCAL seed database through the installed publisher.

Plan: venv/Scripts/python.exe scripts/publish_tag_history.py --repository=""
Run:  venv/Scripts/python.exe scripts/publish_tag_history.py --execute --database-url-env HISTORY_DATABASE_URL  --repository=""

The API has no backdating contract. This seed utility therefore changes only
timestamps of its own publications after REST publication. Use a dedicated local
seed database, never a production database. The API must use the same database.
Credentials stay in HARNESS_MEMORY_API_KEY (requires memory:publish).
Dates come from the requested git show %ai command: author dates of the tagged
commits, not necessarily tag creation dates or actual release dates.
Publication reads docs/ inside --repository. Tags where that directory or its
docs/ directory does not exist are reported and skipped.
Older documentation without the current memory layout is imported as source
documents, preserving its text and commit provenance without inventing content.

$env:HISTORY_DATABASE_URL='postgresql+psycopg2://harness_memory:harness_memory@localhost:5432/harness_memory'
"""

import argparse
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
from uuid import UUID
import zipfile


ROOT = Path(__file__).resolve().parents[1]

# Reuse the SDK CLI while ensuring unchanged documentation still produces one
# snapshot per release. Historical metadata participates in the payload hash.
RUNNER = """
import { CliApp, ProjectMemoryWorkflow, RestPublicationClient, GraphValidator,
  GraphValidationError } from SDK_URL;
import { createHash } from 'node:crypto';
const { MemoryGraph } = await import(new URL('./application/memory/memory-graph.js', SDK_URL));
const reconcile = MemoryGraph.prototype.reconcile;
MemoryGraph.prototype.reconcile = function (proposed, local, previous, ...options) {
  if (previous) {
    // Older releases use path hashes; newer releases declare node IDs.
    // Align the same document before reconciliation retains historical entities.
    const documentTypes = new Set(['adr', 'feature', 'document']);
    const currentKeys = new Map(local.entities.filter(entity =>
      documentTypes.has(entity.type)).map(entity => [entity.metadata?.path, entity.key]));
    const aliases = new Map(previous.entities.filter(entity =>
      documentTypes.has(entity.type) && currentKeys.has(entity.metadata?.path))
      .map(entity => [entity.key, currentKeys.get(entity.metadata.path)]));
    previous = structuredClone(previous);
    for (const entity of previous.entities) {
      entity.key = aliases.get(entity.key) ?? entity.key;
      if (entity.metadata?.document_key) {
        entity.metadata.document_key = aliases.get(entity.metadata.document_key) ?? entity.metadata.document_key;
      }
    }
    for (const relation of previous.relations) {
      relation.source_entity_key = aliases.get(relation.source_entity_key) ?? relation.source_entity_key;
      relation.target_entity_key = aliases.get(relation.target_entity_key) ?? relation.target_entity_key;
    }
  }
  return reconcile.call(this, proposed, local, previous, ...options);
};
const original = ProjectMemoryWorkflow.prototype.run;
ProjectMemoryWorkflow.prototype.run = async function (...args) {
  try {
    const result = await original.apply(this, args);
    return { ...result, status: 'READY' };
  } catch (error) {
    if (!(error instanceof GraphValidationError) ||
        error.message !== 'Existing documentation is incomplete') throw error;
    const context = args[1];
    const files = context.files.filter(file => file.path.startsWith('docs/') &&
      !file.path.startsWith('docs/workflow/') && /\\.md$/i.test(file.path));
    if (!files.length) throw new GraphValidationError('Historical docs contain no Markdown documents');
    console.error('Historical documentation predates the current memory layout; importing source documents.');
    const hash = text => createHash('sha256').update(text, 'utf8').digest('hex');
    const graph = { schema_version: '1.0', entities: files.map(file => {
      const type = file.path.startsWith('docs/adr/') ? 'adr' :
        file.path.startsWith('docs/feature/') ? 'feature' : 'document';
      return { key: `${type}:${hash(file.path).slice(0, 24)}`, type,
        name: (file.content.match(/^#\\s+(.+)$/m)?.[1] ?? file.path).slice(0, 255),
        metadata: { path: file.path, content: file.content,
          content_sha256: hash(file.content), source_commit_sha: context.commitSha,
          lifecycle: 'active' } };
    }), relations: [], evidence: files.map(file => ({ source: file.path,
      metadata: { source_commit_sha: context.commitSha, content_sha256: hash(file.content) } })) };
    const { DocumentContentCodec } = await import(
      new URL('./application/memory/document-content-codec.js', SDK_URL));
    return { status: 'READY', graph: new DocumentContentCodec().encode(graph) };
  }
};
const publish = RestPublicationClient.prototype.publish;
RestPublicationClient.prototype.publish = async function (request) {
  const document = { ...request.graph.document, metadata: {
    ...request.graph.document.metadata,
    historical_release: JSON.parse(process.env.HISTORY_RELEASE) } };
  return publish.call(this, { ...request,
    graph: new GraphValidator().validateAndCanonicalize(document) });
};
process.exitCode = await new CliApp().run(process.argv.slice(2));
"""


def git(repository, *arguments, binary=False):
    return subprocess.check_output(
        ["git", "-C", str(repository), *arguments],
        text=not binary,
        encoding=None if binary else "utf-8",
    )


def releases(repository):
    result = []
    for tag in git(repository, "tag", "--list").splitlines():
        commit = git(repository, "rev-parse", f"refs/tags/{tag}^{{commit}}").strip()
        raw = git(repository, "show", f"refs/tags/{tag}", "--no-patch", "--format=%ai")
        # Annotated tags prepend tagger information and the tag message.
        date = datetime.strptime(raw.strip().splitlines()[-1], "%Y-%m-%d %H:%M:%S %z")
        result.append((date.astimezone(UTC), tag, commit))
    return sorted(result)


def contains_directory(repository, commit, relative):
    if relative == Path("."):
        return True
    path = relative.as_posix()
    entries = git(repository, "ls-tree", "-d", "-z", commit, "--", path)
    for entry in entries.split("\0"):
        attributes, separator, name = entry.partition("\t")
        if separator and name == path and attributes.split()[1] == "tree":
            return True
    return False


def materialize(repository, commit, destination):
    subprocess.run(
        ["git", "clone", "--quiet", "--shared", "--no-checkout", str(repository), str(destination)],
        check=True,
    )
    git(destination, "update-ref", "HEAD", commit)
    git(destination, "read-tree", commit)
    archive = git(repository, "archive", "--format=zip", commit, binary=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as files:
        for member in files.infolist():
            target = (destination / member.filename).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise ValueError("Git archive contains an unsafe path")
            if (member.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"Git archive contains a symlink: {member.filename}")
        files.extractall(destination)


def backdate(engine, output, release, options):
    from sqlalchemy import text

    date, tag, commit = release
    with engine.begin() as connection:
        row = (
            connection.execute(
                text("""
            SELECT p.id, p.snapshot_id, p.tenant_id, p.environment_id,
                   s.metadata, s.generated_at
            FROM knowledge_publications p
            JOIN projects project ON project.id = p.project_id AND project.tenant_id = p.tenant_id
            JOIN environments e ON e.id = p.environment_id AND e.tenant_id = p.tenant_id
            JOIN snapshots s ON s.id = p.snapshot_id AND s.tenant_id = p.tenant_id
            WHERE p.id = :publication AND s.id = :snapshot
              AND project.key = :project AND e.name = :environment
              AND p.deployment_id = :deployment AND p.version = :version
            FOR UPDATE OF p, s, e
        """),
                {
                    "publication": UUID(str(output["publication_id"])),
                    "snapshot": UUID(str(output["snapshot_id"])),
                    "project": options.project_key,
                    "environment": options.environment,
                    "deployment": output["deployment_id"],
                    "version": tag,
                },
            )
            .mappings()
            .one()
        )
        if options.tenant_id and str(row["tenant_id"]) != options.tenant_id:
            raise ValueError("Publication tenant does not match --tenant-id")
        expected = {"tag": tag, "commit": commit, "released_at": date.isoformat()}
        if row["metadata"].get("historical_release") != expected:
            raise ValueError("Publication does not belong to this history import")
        values = {"date": date, "publication": row["id"], "snapshot": row["snapshot_id"]}
        connection.execute(
            text("UPDATE knowledge_publications SET created_at = :date WHERE id = :publication"),
            values,
        )
        # Publication hashes exclude generated_at; graph and hash remain intact.
        connection.execute(
            text(
                "UPDATE snapshots SET created_at = :date, generated_at = :date WHERE id = :snapshot"
            ),
            values,
        )
        connection.execute(
            text("""
            UPDATE environments SET updated_at = :date
            WHERE id = :environment AND current_snapshot_id = :snapshot
        """),
            {**values, "environment": row["environment_id"]},
        )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--sdk", type=Path, default=ROOT / "sdk/dist/index.js")
    parser.add_argument("--project-key", default="harness-kit")
    parser.add_argument("--environment", default="production")
    parser.add_argument("--api-url", default="http://localhost:8080")
    parser.add_argument("--agent", default="codex-cli")
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--tenant-id")
    parser.add_argument("--token-env", default="HARNESS_MEMORY_API_KEY")
    parser.add_argument("--database-url-env", default="HISTORY_DATABASE_URL")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Publish and backdate in a dedicated local seed database",
    )
    options = parser.parse_args()
    repository = options.repository.resolve()
    if not (repository / "docs").is_dir():
        raise ValueError(f"The requested repository must contain a docs directory: {repository}")
    top = Path(git(repository, "rev-parse", "--show-toplevel").strip()).resolve()
    relative = repository.relative_to(top)
    history = releases(top)
    if not history:
        raise ValueError("Repository has no tags")
    available = []
    for release in history:
        if not contains_directory(top, release[2], relative):
            print(
                f"Skipped {release[1]}: directory {relative} does not exist at this tag.",
                flush=True,
            )
        elif not contains_directory(top, release[2], relative / "docs"):
            print(
                f"Skipped {release[1]}: directory {relative / 'docs'} does not exist at this tag.",
                flush=True,
            )
        else:
            available.append(release)
    history = available
    if not history:
        raise ValueError(f"No tags contain documentation for the requested directory: {relative}")
    for date, tag, commit in history:
        print(f"{date.isoformat()} {tag} {commit}", flush=True)
    if not options.execute:
        print(f"Plan: {len(history)} tags. Add --execute to publish.")
        return
    if urlparse(options.api_url).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("History seeding requires a local API")
    if not options.sdk.is_file():
        raise ValueError("Build the harness-memory SDK first")
    if not os.environ.get(options.token_env):
        raise ValueError(f"Set {options.token_env} to a token with memory:publish")
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url

    database_url = os.environ.get(options.database_url_env)
    if not database_url:
        raise ValueError(
            f"Set {options.database_url_env} to the API's dedicated local seed database URL"
        )
    database = make_url(database_url)
    if database.get_backend_name() != "postgresql" or database.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("History seeding requires local PostgreSQL")
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        with tempfile.TemporaryDirectory(prefix="harness-tag-history-") as temporary:
            temporary = Path(temporary)
            runner = temporary / "publish.mjs"
            runner.write_text(
                RUNNER.replace("SDK_URL", json.dumps(options.sdk.resolve().as_uri())),
                encoding="utf-8",
            )
            for index, release in enumerate(history):
                date, tag, commit = release
                identity = hashlib.sha256(
                    f"{options.project_key}\0{options.environment}\0{relative.as_posix()}\0{tag}\0{commit}".encode()
                ).hexdigest()
                from sqlalchemy import text

                with engine.connect() as connection:
                    existing = (
                        connection.execute(
                            text("""
                        SELECT p.id AS publication_id, p.snapshot_id, p.deployment_id, p.tenant_id
                        FROM knowledge_publications p
                        JOIN projects project ON project.id = p.project_id AND project.tenant_id = p.tenant_id
                        JOIN environments e ON e.id = p.environment_id AND e.tenant_id = p.tenant_id
                        WHERE project.key = :project AND e.name = :environment
                          AND p.deployment_id = :deployment
                    """),
                            {
                                "project": options.project_key,
                                "environment": options.environment,
                                "deployment": f"tag-history-{identity}",
                            },
                        )
                        .mappings()
                        .all()
                    )
                if options.tenant_id:
                    existing = [
                        row for row in existing if str(row["tenant_id"]) == options.tenant_id
                    ]
                if len(existing) > 1:
                    raise ValueError("History deployment matches multiple tenants")
                if existing:
                    backdate(engine, dict(existing[0]), release, options)
                    print(f"Already published {tag}; historical date verified.", flush=True)
                    continue
                destination = temporary / f"release-{index}"
                materialize(top, commit, destination)
                source = destination / relative
                if not source.is_dir():
                    raise ValueError(f"{tag}: repository subdirectory does not exist: {relative}")
                env = dict(os.environ)
                env["HISTORY_RELEASE"] = json.dumps(
                    {"tag": tag, "commit": commit, "released_at": date.isoformat()}
                )
                command = [
                    "node",
                    str(runner),
                    "publish",
                    "--repository",
                    str(source),
                    "--agent",
                    options.agent,
                    "--model",
                    options.model,
                    "--effort",
                    options.effort,
                    "--environment",
                    options.environment,
                    "--project-key",
                    options.project_key,
                    "--version",
                    tag,
                    "--deployment-id",
                    f"tag-history-{identity}",
                    "--api-url",
                    options.api_url,
                    "--token-env",
                    options.token_env,
                    "--output",
                    "json",
                ]
                if options.tenant_id:
                    command.extend(["--tenant-id", options.tenant_id])
                completed = subprocess.run(
                    command,
                    cwd=source,
                    env=env,
                    text=True,
                    encoding="utf-8",
                    stdout=subprocess.PIPE,
                    check=True,
                )
                output = json.loads(completed.stdout)
                if output["status"] not in {"ACTIVATED", "ALREADY_PUBLISHED"}:
                    raise ValueError(f"{tag}: no publication created: {output['status']}")
                backdate(engine, output, release, options)
                print(f"Published {tag} at {date.isoformat()}: {output['snapshot_id']}", flush=True)
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"History import failed: {error}", file=sys.stderr)
        sys.exit(1)
