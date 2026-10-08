#!/usr/bin/env python3
"""Source/package review and explicitly authorized local MCP conformance."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import shlex
import signal
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
VERSIONS = {"conformance": "0.1.16", "semgrep": "1.180.0", "osv": "2.6.0"}
TRUSTED_CLIENT_ADAPTER_SHA256 = "2674256fb61149f8705467e8c1faa521e040c5e65f965f53b57b691fc09cec13"
TRUSTED_CLIENT_MANIFEST_SHA256 = "17ea5e88699d811a0adc1baa35c4e96a0598f32b2684617136145f6d2e8c6b57"
MAX_FILES, MAX_BYTES = 10000, 64 * 1024 * 1024
REVIEWED_NAMES = {"@modelcontextprotocol/sdk", "@modelcontextprotocol/conformance", "express", "zod", "requests", "httpx", "fastmcp", "mcp"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(source: Path, destination: Path, *, max_bytes: int = MAX_BYTES, neutralize_controls: bool = True,
          path_mapping: dict[str, str] | None = None) -> dict[str, str]:
    """No links, hooks or candidate configuration are executed; bound all copied bytes."""
    if source.is_symlink() or not source.is_dir():
        raise ValueError("A regular source directory is required")
    count = size = 0
    hashes = {}
    for directory, dirs, files, fd in os.fwalk(source, follow_symlinks=False):
        dirs.sort()
        for name in dirs + files:
            if stat.S_ISLNK(os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode):
                raise ValueError("Source links are not admitted")
        count += len(dirs)
        if count > MAX_FILES:
            raise ValueError("Source exceeds directory budget")
        relative = Path(directory).relative_to(source)
        (destination / relative).mkdir(parents=True, exist_ok=True)
        for name in sorted(files):
            handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(handle, "rb") as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError("Only regular source files are admitted")
                count += 1
                if count > MAX_FILES or size + info.st_size > max_bytes:
                    raise ValueError("Source exceeds the file/byte budget")
                content = stream.read(max_bytes - size + 1)
                size += len(content)
                if size > max_bytes:
                    raise ValueError("Source exceeds byte budget")
            target = destination / relative / name
            target.write_bytes(content)
            hashes[(relative / name).as_posix()] = hashlib.sha256(content).hexdigest()
    if not hashes:
        raise ValueError("Empty source cannot produce a completed review")
    # Candidate ignore rules cannot silently suppress a scan of the snapshot.
    if neutralize_controls:
        for name in [".semgrepignore", ".gitignore", "osv-scanner.toml"]:
            for path in sorted(destination.rglob(name)):
                target = path.with_name(path.name + ".disabled.txt")
                suffix = 1
                while target.exists():
                    target = path.with_name(path.name + f".disabled.{suffix}.txt")
                    suffix += 1
                original = path.relative_to(destination).as_posix()
                path.rename(target)
                if path_mapping is not None:
                    path_mapping[original] = target.relative_to(destination).as_posix()
    return hashes


def environment(home: Path) -> dict[str, str]:
    return {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "LANG": "C.UTF-8",
            "SEMGREP_SEND_METRICS": "off", "SEMGREP_ENABLE_VERSION_CHECK": "0",
            "OTEL_SDK_DISABLED": "true", "PYTHONDONTWRITEBYTECODE": "1"}


def execute(command: list[str], env: dict[str, str], cwd: Path, *, offline: bool = False) -> subprocess.CompletedProcess:
    if offline:
        sandbox = shutil.which("sandbox-exec")
        if sys.platform != "darwin" or not sandbox:
            raise ValueError("Offline OS network isolation unavailable; refusing fallback")
        command = [sandbox, "-p", "(version 1)(allow default)(deny network*)", *command]
    process = subprocess.Popen(command, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                               start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=180)
    except BaseException:
        # This exact process group was created above; no name/port based cleanup.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def edit_distance_one(a: str, b: str) -> bool:
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    shorter, longer = sorted((a, b), key=len)
    return any(longer[:i] + longer[i + 1:] == shorter for i in range(len(longer)))


def package_observations(snapshot: Path) -> list[dict]:
    findings = []
    for path in sorted(snapshot.rglob("package.json")):
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise ValueError("Package manifest must be an object")
        for field in ("scripts", "dependencies", "devDependencies"):
            value = data.get(field, {})
            if not isinstance(value, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in value.items()):
                raise ValueError("Package fields must map names to strings")
        for name, command in data.get("scripts", {}).items():
            if name in {"preinstall", "install", "postinstall", "prepare"}:
                findings.append({"rule": "mcp.package-lifecycle", "path": path.relative_to(snapshot).as_posix(), "script": name})
        names = set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
        for name in sorted(names - REVIEWED_NAMES):
            for reference in sorted(REVIEWED_NAMES):
                if edit_distance_one(name, reference):
                    findings.append({"rule": "mcp.name-confusion", "path": path.relative_to(snapshot).as_posix(), "name": name, "similar_to": reference, "status": "heuristic; not proven typosquat"})
    return findings


def advisory_output(stdout: str) -> dict:
    result = json.loads(stdout)
    if not isinstance(result, dict) or not isinstance(result.get("results"), list):
        raise ValueError("OSV returned an incomplete result envelope")
    return result


def source_scan(args) -> dict:
    with tempfile.TemporaryDirectory(prefix="mcp-quality-") as scratch:
        home = Path(scratch)
        snapshot = home / "source"
        path_mapping = {}
        hashes = stage(args.source.absolute(), snapshot, path_mapping=path_mapping)
        report = {"kind": "static-source-package-review", "versions": VERSIONS,
                  "source_sha256": hashes, "staged_path_mapping": path_mapping, "rules_sha256": digest(ROOT / "rules.yaml"),
                  "package_observations": package_observations(snapshot), "checks": {}, "status": "incomplete"}
        env = environment(home)
        for tool, expected in [(args.semgrep, "1.180.0"), (args.osv, "2.6.0")]:
            probe = execute([str(tool), "--version"], env, home, offline=True)
            if probe.returncode or expected not in probe.stdout:
                raise ValueError("Engine version differs from reviewed pin")
        semgrep = execute([str(args.semgrep), "scan", "--config", str(ROOT / "rules.yaml"),
                           "--metrics", "off", "--disable-version-check", "--no-git-ignore",
                           "--json", "--error", "--max-target-bytes", str(MAX_BYTES), str(snapshot)], env, home, offline=True)
        sg = json.loads(semgrep.stdout)
        if not isinstance(sg, dict) or not isinstance(sg.get("results"), list) or not isinstance(sg.get("errors"), list):
            raise ValueError("Semgrep returned an incomplete result envelope")
        report["checks"]["semgrep"] = {"exit_code": semgrep.returncode, "results": sg.get("results", []),
                                         "errors": sg.get("errors", []), "paths": sg.get("paths", {})}
        db = home / "database"
        db_hashes = stage(args.database.absolute(), db, max_bytes=512 * 1024 * 1024, neutralize_controls=False)
        manifest = json.loads((db / "manifest.json").read_text())
        if not isinstance(manifest, dict) or not isinstance(manifest.get("downloaded_at"), str) or not isinstance(manifest.get("files"), dict) or not manifest["files"]:
            raise ValueError("Advisory snapshot needs a date and exact nonempty file manifest")
        date = dt.datetime.fromisoformat(manifest["downloaded_at"].replace("Z", "+00:00"))
        if date.tzinfo is None or not 0 <= (dt.datetime.now(dt.timezone.utc) - date).total_seconds() <= 7 * 86400:
            raise ValueError("Advisory database must have a dated snapshot no older than seven days")
        if set(db_hashes) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("Advisory snapshot includes unmanifested files")
        for name, expected in manifest["files"].items():
            candidate = Path(name)
            if candidate.is_absolute() or ".." in candidate.parts or not isinstance(expected, str) or len(expected) != 64 or db_hashes.get(name) != expected:
                raise ValueError("Advisory database differs from its snapshot manifest")
        env["OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"] = str(db)
        osv = execute([str(args.osv), "scan", "source", "--offline", "--local-db-path", str(db), "--format", "json", "--recursive", str(snapshot)], env, home, offline=True)
        report["checks"]["osv"] = {"exit_code": osv.returncode, "snapshot": manifest, "output": advisory_output(osv.stdout), "errors": osv.stderr if osv.returncode not in {0, 1} else ""}
        if semgrep.returncode in {0, 1} and not sg.get("errors") and osv.returncode in {0, 1}:
            report["status"] = "review-required" if semgrep.returncode or osv.returncode or report["package_observations"] else "no-matches-within-tested-rules"
        return report


def local_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "::1"} or parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise ValueError("Only explicit numeric loopback HTTP URLs without credentials are admitted")
    return url


def conformance(args) -> dict:
    if not args.authorized:
        raise ValueError("Confirm ownership/permission for the local endpoint with --authorized")
    url = local_url(args.url) if args.command == "conformance" else None
    package = ROOT / "node_modules/@modelcontextprotocol/conformance"
    if json.loads((package / "package.json").read_text())["version"] != VERSIONS["conformance"]:
        raise ValueError("Official suite version differs from reviewed pin")
    node = shutil.which("node")
    if not node:
        raise ValueError("Node is unavailable")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    artifacts = args.output.with_suffix(".artifacts")
    artifacts.mkdir(exist_ok=False)
    env = environment(artifacts)
    if args.command == "conformance":
        command = [node, str(package / "dist/index.js"), "server", "--url", url, "--suite", "active"]
    else:
        upstream = ROOT / "test/upstream"
        if digest(upstream / "manifest.json") != TRUSTED_CLIENT_MANIFEST_SHA256:
            raise ValueError("Trusted client manifest differs from reviewed pin")
        manifest = json.loads((upstream / "manifest.json").read_text())
        for name, expected in manifest["files"].items():
            if digest(upstream / name) != expected:
                raise ValueError("Trusted client fixture differs from its reviewed source")
        client = ROOT / "test/client-adapter.ts"
        if digest(client) != TRUSTED_CLIENT_ADAPTER_SHA256:
            raise ValueError("Trusted client adapter differs from reviewed source")
        executable = " ".join(shlex.quote(x) for x in [node, "--import", str(ROOT / "node_modules/tsx/dist/loader.mjs"), str(client)])
        command = [node, str(package / "dist/index.js"), "client", "--command", executable, "--suite", "all"]
    result = execute(command, env, artifacts)
    pagination = None
    if url and result.returncode == 0:
        supplemental = execute([node, str(ROOT / "pagination-cli.mjs"), url], env, artifacts)
        pagination = {"exit_code": supplemental.returncode, "stderr": supplemental.stderr,
                      "result": json.loads(supplemental.stdout) if supplemental.returncode == 0 else None}
    passed = result.returncode == 0 and (pagination is None or pagination["exit_code"] == 0)
    return {"kind": "official-server-conformance" if url else "official-trusted-reference-client-conformance", "version": VERSIONS["conformance"], "url": url,
            "suite": "active" if url else "all",
            "target_contract": "official-synthetic-reference-fixtures",
            "general_server_compliance": "not-evaluated",
            "fixture_expectations": "Fixed upstream tool, prompt and resource names; missing fixture support is not a general MCP violation",
            "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
            "artifacts": str(artifacts), "pagination": pagination, "status": "upstream-pass-reported" if passed else "failed",
            "client_auth_discovery": "not tested by server suite" if url else "see upstream client scenarios", "distinct_server_attempts": 1 if url else 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan-source")
    scan.add_argument("source", type=Path)
    scan.add_argument("--semgrep", type=Path, required=True)
    scan.add_argument("--osv", type=Path, required=True)
    scan.add_argument("--database", type=Path, required=True)
    protocol = sub.add_parser("conformance")
    protocol.add_argument("--url", required=True)
    protocol.add_argument("--authorized", action="store_true")
    client = sub.add_parser("client-conformance", help="Run only the bundled hash-checked official client fixture")
    client.add_argument("--authorized", action="store_true")
    for command in (scan, protocol, client):
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; evidence is never overwritten")
    print((ROOT / "DISCLOSURE.md").read_text(), file=sys.stderr)
    try:
        report = source_scan(args) if args.command == "scan-source" else conformance(args)
    except (ValueError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        report = {"status": "incomplete", "error": str(error), "versions": VERSIONS}
    report["created_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    report["disclosure_sha256"] = digest(ROOT / "DISCLOSURE.md")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({"status": report["status"], "report": str(args.output)}))
    return 2 if report["status"] == "incomplete" else (1 if report["status"] in {"review-required", "failed"} else 0)


if __name__ == "__main__":
    raise SystemExit(main())
