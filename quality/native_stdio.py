#!/usr/bin/env python3
"""Explicitly admitted native stdio baseline in an owned Linux user cgroup."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parent
MAX_OUTPUT = 1024 * 1024


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_source(root: Path, receipt: dict) -> None:
    """All admitted bytes are regular, bounded, immutable and explicitly reviewed."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Regular candidate directory required')
    expected = receipt['files']
    actual = {}
    size = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            if path.is_symlink():
                raise ValueError('Candidate links are not admitted')
        for name in files:
            path = Path(directory) / name
            if not path.is_file():
                raise ValueError('Only regular candidate files admitted')
            size += path.stat().st_size
            if size > 64 * 1024 * 1024 or len(actual) >= 10000:
                raise ValueError('Candidate source budget exceeded')
            actual[path.relative_to(root).as_posix()] = sha(path)
    if actual != expected:
        raise ValueError('Candidate bytes differ from reviewed receipt')
    package = json.loads((root / 'package.json').read_text())
    if package.get('name') != receipt['package'] or package.get('version') != receipt['version']:
        raise ValueError('Candidate package identity mismatch')
    # Dependency-free packages have an exact empty dependency tree. Other candidates
    # need a reviewed immutable installed tree, including its lockfile, in this receipt.
    if any(package.get(key) for key in ('dependencies', 'optionalDependencies', 'peerDependencies')):
        lock = json.loads((root / 'package-lock.json').read_text())
        if lock.get('lockfileVersion') != 3 or not lock.get('packages'):
            raise ValueError('Reviewed npm v3 dependency lock required')
        for name, dependency in lock['packages'].items():
            if name and (dependency.get('link') or not dependency.get('integrity')):
                raise ValueError('Every transitive dependency needs immutable integrity')
    entrypoint = receipt['entrypoint']
    if entrypoint not in actual or Path(entrypoint).suffix not in ('.js', '.mjs', '.cjs'):
        raise ValueError('Reviewed JavaScript entrypoint required')
    if receipt.get('profile') != 'baseline' or receipt.get('admission') != 'reviewed-offline-baseline':
        raise ValueError('Explicit reviewed baseline admission required')


def run(args) -> int:
    if not args.authorized or os.name != 'posix' or not Path('/sys/fs/cgroup/cgroup.controllers').exists():
        raise ValueError('Explicit authorization and qualified Linux cgroup required')
    receipt = json.loads(args.receipt.read_text())
    if args.source.is_symlink():
        raise ValueError('Candidate root links are not admitted')
    source = args.source.resolve()
    verify_source(source, receipt)
    if args.node.resolve() != Path('/usr/bin/node').resolve():
        raise ValueError('Verified node must be the candidate runtime /usr/bin/node')
    for path, expected in ((args.bwrap, args.bwrap_sha256), (args.node, args.node_sha256),
                           (args.runner, args.runner_sha256)):
        if sha(path) != expected:
            raise ValueError('Sandbox/runtime/runner pin differs')
    if args.artifacts.exists():
        raise ValueError('New owned artifacts directory required')
    args.artifacts.mkdir(parents=True)
    unit = 'mcp-quality-' + uuid.uuid4().hex
    sandbox = [str(args.bwrap.resolve()), '--unshare-all', '--die-with-parent', '--new-session',
               '--ro-bind', '/usr', '/usr', '--symlink', 'usr/bin', '/bin',
               '--symlink', 'usr/lib', '/lib', '--symlink', 'usr/lib64', '/lib64',
               '--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--dir', '/home',
               '--ro-bind', str(source), '/candidate', '--chdir', '/candidate', '--clearenv',
               '--setenv', 'HOME', '/home', '--setenv', 'PATH', '/usr/bin',
               '--setenv', 'LANG', 'C.UTF-8', '/usr/bin/node',
               '/candidate/' + receipt['entrypoint']]
    parameters = args.artifacts / 'parameters.json'
    parameters.write_text(json.dumps({'profile': 'baseline', 'server': {
        'command': sandbox[0], 'args': sandbox[1:], 'env': {'PATH': '/usr/bin', 'LANG': 'C.UTF-8'}}}))
    command = ['systemd-run', '--user', '--wait', '--pipe', '--collect', '--unit=' + unit,
               '-p', 'MemoryMax=536870912', '-p', 'MemorySwapMax=0', '-p', 'TasksMax=32',
               '-p', 'RuntimeMaxSec=180', '-p', 'KillMode=control-group',
               str(args.node.resolve()), '--max-old-space-size=128', str(args.runner.resolve()), str(parameters)]
    identity = {'unit': unit, 'launcher_pid': None, 'launcher_start_ticks': None,
                'intent_at_unix': time.time(), 'receipt_sha256': sha(args.receipt),
                'scope': 'native stdio handshake/ping/tools-list; no tools/call', 'candidate_identity': receipt['identity']}
    (args.artifacts / 'ownership.json').write_text(json.dumps(identity, indent=2))
    selector = selectors.DefaultSelector()
    process = None
    cleanup_verified = False
    cleanup_errors = []
    report = None
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        identity.update(launcher_pid=process.pid, started_at_unix=time.time(),
                        launcher_start_ticks=Path(f'/proc/{process.pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
        (args.artifacts / 'ownership.json').write_text(json.dumps(identity, indent=2))
        output = {process.stdout: bytearray(), process.stderr: bytearray()}
        for stream in output:
            selector.register(stream, selectors.EVENT_READ)
        deadline = time.monotonic() + 190
        while selector.get_map():
            if time.monotonic() > deadline:
                raise TimeoutError('Owned protocol run exceeded deadline')
            for key, _ in selector.select(timeout=1):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                else:
                    output[key.fileobj].extend(chunk)
                    if sum(map(len, output.values())) > MAX_OUTPUT:
                        raise ValueError('Owned output budget exceeded')
        code = process.wait(timeout=5)
        (args.artifacts / 'runner-stderr.txt').write_bytes(output[process.stderr])
        if code not in (0, 1):
            raise ValueError('Runner failed; no candidate acceptance')
        report = json.loads(output[process.stdout])
        report.update(identity=receipt['identity'], receipt_sha256=sha(args.receipt))
    finally:
        selector.close()
        try:
            subprocess.run(['systemctl', '--user', 'stop', unit], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            cleanup_errors.append('stop: ' + str(error))
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired) as error:
                cleanup_errors.append('launcher terminate: ' + str(error))
                try:
                    process.kill()
                    process.wait(timeout=5)
                except (OSError, subprocess.TimeoutExpired) as error:
                    cleanup_errors.append('launcher kill: ' + str(error))
        state_text = ''
        try:
            state = subprocess.run(['systemctl', '--user', 'show', unit, '--property=ActiveState',
                                    '--property=ControlGroup'], capture_output=True, text=True, timeout=10, check=False)
            state_text = state.stdout.strip()
            cleanup_verified = state.returncode == 0 and 'ActiveState=active' not in state.stdout and 'ActiveState=activating' not in state.stdout
            groups = [line.split('=', 1)[1] for line in state.stdout.splitlines() if line.startswith('ControlGroup=')]
            if groups and groups[0]:
                group = (Path('/sys/fs/cgroup') / groups[0].lstrip('/')).resolve()
                if not group.is_relative_to('/sys/fs/cgroup') or group.name != unit + '.service':
                    cleanup_verified = False
                elif group.exists():
                    cleanup_verified = cleanup_verified and all(not file.read_text().strip() for file in group.rglob('cgroup.procs'))
            cleanup_verified = cleanup_verified and (process is None or process.poll() is not None)
        except (OSError, subprocess.TimeoutExpired) as error:
            cleanup_errors.append('reconciliation: ' + str(error))
        identity.update(finished_at_unix=time.time(), cleanup_verified=cleanup_verified,
                        cleanup_state=state_text, cleanup_errors=cleanup_errors)
        (args.artifacts / 'ownership.json').write_text(json.dumps(identity, indent=2))
        if not cleanup_verified:
            raise RuntimeError('Owned unit cleanup not verified')
    # Acceptance is visible only after the exact owned unit and launcher are reconciled.
    (args.artifacts / 'report.json').write_text(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    def cancel(signum, frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, cancel)
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('receipt', 'source', 'artifacts', 'bwrap', 'node', 'runner'):
        parser.add_argument('--' + option, type=Path, required=True)
    for option in ('bwrap-sha256', 'node-sha256', 'runner-sha256'):
        parser.add_argument('--' + option, required=True)
    parser.add_argument('--authorized', action='store_true')
    raise SystemExit(run(parser.parse_args()))
