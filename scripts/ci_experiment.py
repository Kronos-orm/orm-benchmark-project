#!/usr/bin/env python3
"""CI transport and execution: producer builds once; every consumer uses sealed bytes."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True  # Sealed runtime consumers must not create __pycache__ entries.
import tarfile
import time

from run_experiment import ORMS, JVM_ARGS, SEED, cases, digest, source_digest, source_files, write_json, read_json, pilot_findings, catalog_versions
from secret_audit import verify_receipt, finish_aggregate, RECEIPT
from artifact_transport import require_single_attempt
import execution_protocol as protocol

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [f'{projection}-{size}' for projection in ['entity', 'map', 'scalar'] for size in [1000, 100000]] + ['write-1', 'write-100']


def group_for(kind, params):
    return f"{params['projection']}-{params['tableRows']}" if kind == 'read' else f"write-{params['transactionRows']}"


def schedule():
    result = []
    for block in range(1, 6):
        scenarios = cases('measure')
        random.Random(SEED + block).shuffle(scenarios)
        for kind, parameters in scenarios:
            orms = ORMS.copy()
            random.Random(str(SEED) + str(block) + json.dumps(parameters, sort_keys=True)).shuffle(orms)
            for orm in orms:
                result.append(dict(block=block, group=group_for(kind, parameters), kind=kind, params=dict(orm=orm, **parameters)))
    assert len(result) == 780
    return result


def cell_name(item):
    return '-'.join([item['kind'], f"b{item['block']}"] + [f'{k}={v}' for k, v in sorted(item['params'].items())])


def seal(directory):
    files = {str(p.relative_to(directory)): digest(p) for p in sorted(directory.rglob('*')) if p.is_file() and p != directory / 'seal.json'}
    write_json(directory / 'seal.json', dict(files=files))
    return digest(directory / 'seal.json')


def verify(directory, expected):
    if digest(directory / 'seal.json') != expected:
        raise ValueError('Bundle seal differs from the producer job output')
    wanted = read_json(directory / 'seal.json')['files']
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and p != directory / 'seal.json'}
    if actual != set(wanted) or any(p.is_symlink() for p in directory.rglob('*')):
        raise ValueError('Unexpected, missing or symbolic-link bundle entry')
    for name, sha in wanted.items():
        path = directory / name
        if path.resolve().is_relative_to(directory.resolve()) is False or digest(path) != sha:
            raise ValueError('Bundle bytes differ: ' + name)
    return read_json(directory / 'build-manifest.json')


def pack(args):
    out = args.out.resolve()
    if out.exists():
        raise ValueError('Producer bundle must use a fresh directory')
    out.mkdir(parents=True)
    frozen = read_json(args.frozen)
    candidate = read_json(args.candidate / 'ci-candidate.json')
    if candidate['sha'] != frozen['candidateGitSha'] or candidate['versions']['version'] != '0.4.0' or candidate['versions']['kotlin'] != '2.4.21':
        raise ValueError('Kronos candidate identity/version differs from resolved ref')
    for name, sha in candidate['files'].items():
        path = (args.candidate / name).resolve()
        if not path.is_relative_to(args.candidate.resolve()) or digest(path) != sha:
            raise ValueError('Candidate payload digest mismatch')
    shutil.copytree(args.candidate, out / 'candidate')
    (out / 'runtime').mkdir()
    runtime, entries = {}, []
    candidate_hashes = set(candidate['files'].values())
    candidate_jar_names = {Path(name).name for name in candidate['files'] if name.endswith('.jar')}
    for index, entry in enumerate(args.classpath.read_text().strip().split(os.pathsep)):
        path = Path(entry)
        if not path.exists():
            raise ValueError('Missing runtime entry: ' + entry)
        if path.is_file() and (path.name in candidate_jar_names or 'com.kotlinorm' in path.parts) and digest(path) not in candidate_hashes:
            raise ValueError('Runtime Kronos artifact is absent from candidate')
        relative = f'runtime/{index:03d}-' + (path.name if path.is_file() else 'classes')
        target = out / relative
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copyfile(path, target)
        entries.append(relative)
        for payload in sorted(target.rglob('*')) if target.is_dir() else [target]:
            if payload.is_file():
                runtime[str(payload.relative_to(out))] = digest(payload)
    for resource in ['META-INF/BenchmarkList', 'META-INF/CompilerHints']:
        if not any((out / entry / resource).is_file() for entry in entries if (out / entry).is_dir()):
            raise ValueError('JMH annotation processor output missing: ' + resource)
    sha, sources = source_digest()
    manifest = dict(frozen, sourceSha256=sha, sourceFiles=sources, runtimeArtifacts=runtime,
                    runtimeClasspathRelative=entries,
                    runtimeSha256=hashlib.sha256(json.dumps(runtime, sort_keys=True).encode()).hexdigest(),
                    candidateJars={k: v for k, v in candidate['files'].items() if k.endswith('.jar')},
                    jvmArgs=JVM_ARGS, seed=SEED, versionCatalogTOML=(ROOT / 'libs.versions.toml').read_text(),
                    catalogVersions=catalog_versions((ROOT/'libs.versions.toml').read_text()),
                    executionEnvironment='GitHub-hosted runner VM; physical host is not controlled or attested')
    write_json(out / 'build-manifest.json', manifest)
    with tarfile.open(out / ('source-' + sha[:16] + '.tar.gz'), 'w:gz') as archive:
        for path in source_files():
            archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    shutil.copytree(ROOT / 'scripts', out / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(ROOT/'config',out/'config')
    write_json(out / 'expected-schedule.json', schedule())
    print(seal(out))


def reuse(args):
    pilot_directory = getattr(args, 'pilot', None)
    stored_review = read_json(pilot_directory / 'pilot-review.json') if pilot_directory and (pilot_directory / 'pilot-review.json').exists() else None
    review = json.loads(args.pilot_review) if args.pilot_review != '{}' else stored_review
    if review is None: raise ValueError('Actual pilot statistical evidence is required')
    manifest = verify(args.bundle, review['bundleSha256'])
    frozen = read_json(args.frozen)
    for key in ['candidateGitSha', 'benchmarkGitSha']:
        if manifest[key] != frozen[key]:
            raise ValueError('Reviewed executable belongs to another source commit: ' + key)
    if manifest.get('workflowRunAttempt') != '1' or frozen.get('workflowRunAttempt') != '1':
        raise ValueError('Reuse cannot mix rerun attempts')
    transport = frozen.get('reuseArtifacts')
    if not transport or transport['runId'] != args.source_run_id or transport['runAttempt'] != 1 or transport['benchmarkGitSha'] != manifest['benchmarkGitSha']:
        raise ValueError('Reuse requires frozen artifact IDs and ZIP SHA256 for the exact original pilot')
    for key in ['candidateGitSha', 'sourceSha256', 'runtimeSha256']:
        if review.get(key) != manifest[key]:
            raise ValueError('Pilot review differs from executable: ' + key)
    if stored_review != review or not review.get('findings') or not review.get('pilotRunUrl'):
        raise ValueError('Pilot statistical evidence differs from the hash-bound original')
    if str(manifest['workflowRunId']) != args.source_run_id:
        raise ValueError('Artifact came from another producer run')
    if manifest.get('mode') != 'pilot':
        raise ValueError('Formal measurement must reuse an executable from a completed pilot run')
    gate, complete = read_json(args.gate / 'validation-gate.json'), read_json(args.pilot / 'completion.json')
    verify_receipt(args.gate, dict(manifest, bundleSha256=review['bundleSha256']), args.source_run_id)
    verify_receipt(args.pilot, dict(manifest, bundleSha256=review['bundleSha256']), args.source_run_id)
    if gate['status'] != 'PASS' or complete['status'] != 'PASS' or gate['bundleSha256'] != review['bundleSha256'] or complete['bundleSha256'] != review['bundleSha256']:
        raise ValueError('The reviewed artifact did not complete correctness and pilot gates')
    if digest(args.gate / 'validation-gate.json') != review['validationGateSha256'] or digest(args.pilot / 'completion.json') != review['pilotCompletionSha256']:
        raise ValueError('Pilot statistical evidence is detached from the correctness/completion gates')
    planned = read_json(args.pilot / 'pilot/schedule.json')
    statuses = sorted((args.pilot / 'pilot').glob('*.status.json'))
    if len(planned) != 48 or len(statuses) != 48:
        raise ValueError('A complete 48-cell pilot is required')
    seen = set()
    for statusfile in statuses:
        status = read_json(statusfile)
        name = cell_name(status)
        if name in seen or status['status'] != 'PASS' or status['bundleSha256'] != review['bundleSha256']:
            raise ValueError('Invalid/duplicate pilot cell')
        seen.add(name)
        raw = statusfile.parent / Path(status['raw']).name
        if digest(raw) != status['rawSha256']:
            raise ValueError('Pilot raw evidence changed')
    if seen != {cell_name(item) for item in planned}:
        raise ValueError('Pilot evidence does not match its planned cells')
    if review['findings'] != pilot_findings(args.pilot / 'pilot'):
        raise ValueError('Pilot statistics differ from the actual hash-checked raw observations')
    print(review['bundleSha256'])


def run(argv, log, out):
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    now = time.monotonic()
    environment = dict(os.environ)
    if 'BENCH_DB_PASSWORD_FILE' in environment:
        secret = Path(environment['BENCH_DB_PASSWORD_FILE'])
        if secret.stat().st_mode & 0o077:
            raise ValueError('CI secret file must have mode 600')
        environment['BENCH_DB_PASSWORD'] = secret.read_text()
    with log.open('w') as handle:
        result = subprocess.run([str(v) for v in argv], env=environment, stdout=handle, stderr=subprocess.STDOUT)
    record = dict(argv=[str(v) for v in argv], started=started, finished=dt.datetime.now(dt.timezone.utc).isoformat(),
                  elapsedSeconds=time.monotonic() - now, exitCode=result.returncode, log=str(log))
    with (out / 'commands.jsonl').open('a') as handle:
        handle.write(json.dumps(record, sort_keys=True) + '\n')
    return result.returncode


def host_snapshot(out, manifest):
    info = {k: os.environ.get(k) for k in ['RUNNER_OS', 'RUNNER_ARCH', 'RUNNER_NAME', 'ImageOS', 'ImageVersion', 'GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_JOB']}
    info.update(physicalHostIdentity='unavailable on hosted VM', candidateGitSha=manifest['candidateGitSha'],
                sourceSha256=manifest['sourceSha256'], bundleSha256=manifest.get('bundleSha256'))
    write_json(out / 'host.json', info)
    for label, argv in {'cpu': ['lscpu'], 'memory': ['free', '-b'], 'os': ['uname', '-a'],
                        'jdk': [Path(os.environ['JAVA_HOME']) / 'bin/java', '-version'],
                        'idle': ['vmstat', '1', '5'], 'processes': ['ps', '-eo', 'pid,pcpu,pmem,comm'],
                        'container': ['docker', 'inspect', 'benchmark-mysql', '--format', '{{json .Config.Cmd}}']}.items():
        run(argv, out / f'host-{label}.log', out)


def execute_stage(args):
    bundle, out = args.bundle.resolve(), args.out.resolve()
    manifest = verify(bundle, args.seal)
    plan = None
    if getattr(args, 'execution_plan', None):
        if args.command not in ['validate', 'shard']: raise ValueError('Formal execution context only applies to validation and registered shards')
        plan = protocol.read_plan(args.execution_plan, getattr(args, 'expected_context', None))
        protocol.verify_controller(plan)
        manifest = protocol.bind(manifest, plan, args.seal)
    manifest['bundleSha256'] = args.seal
    manifest['executionWorkflowRunId'] = os.environ.get('GITHUB_RUN_ID')
    manifest['executionWorkflowRunAttempt'] = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
    manifest['executionStage'] = args.command
    manifest['executionGroup'] = args.group if args.command == 'shard' else None
    manifest['executionBlock'] = args.block if args.command == 'shard' else None
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'build-manifest.json', manifest)
    if plan: protocol.install(out, plan)
    host_snapshot(out, manifest)
    java = Path(os.environ['JAVA_HOME']) / 'bin/java'
    cp = os.pathsep.join(str(bundle / entry) for entry in manifest['runtimeClasspathRelative'])
    if args.command == 'validate':
        code = run([java, *JVM_ARGS, '-cp', cp, 'com.kotlinorm.benchmark.ValidateBenchmark', out / 'validation'], out / 'validation.log', out)
        if code or read_json(out / 'validation/PASS.json')['status'] != 'PASS':
            raise RuntimeError('Correctness/SQL/resource gate failed; measurement disabled')
        write_json(out / 'validation-gate.json', dict(bundleSha256=args.seal, status='PASS',
                    candidateGitSha=manifest['candidateGitSha'], sourceSha256=manifest['sourceSha256'],
                    runtimeArtifacts=manifest['runtimeArtifacts'], environmentSha256=digest(out / 'validation/environment.json'),
                    environment=read_json(out / 'validation/environment.json'), **protocol.identity(manifest)))
        return
    gate = read_json(args.gate / 'validation-gate.json')
    protocol.same(manifest, gate)
    if plan: verify_receipt(args.gate, manifest, manifest['executionWorkflowRunId'])
    if gate['bundleSha256'] != args.seal or gate['status'] != 'PASS':
        raise ValueError('Validation gate belongs to another bundle')
    # The producer job already verifies the same-byte pilot, its actual statistics and correctness gate.
    snapshot = out / 'environment.json'
    if run([java, *JVM_ARGS, '-cp', cp, 'com.kotlinorm.benchmark.InspectEnvironment', snapshot], out / 'environment.log', out):
        raise RuntimeError('Environment inspection failed')
    if read_json(snapshot) != gate['environment']:
        raise ValueError('Server/JVM configuration differs from validation gate')
    if args.command == 'pilot':
        planned = []
        for kind, parameters in cases('pilot'):
            orms = ORMS.copy()
            random.Random(str(SEED) + json.dumps(parameters, sort_keys=True)).shuffle(orms)
            planned += [dict(block=1, kind=kind, params=dict(orm=orm, **parameters)) for orm in orms]
        stage = 'pilot'
    else:
        planned = [item for item in read_json(bundle / 'expected-schedule.json') if item['group'] == args.group and item['block'] == args.block]
        stage = 'measure'
    raw = out / stage; raw.mkdir()
    write_json(raw / 'schedule.json', planned)
    failures = []
    for item in planned:
        kind, params = item['kind'], item['params']; name = cell_name(item)
        target = raw / (name + '.json')
        benchmark = 'com.kotlinorm.benchmark.' + ('ReadBenchmark.query' if kind == 'read' else 'InsertBenchmark.insertTransaction')
        argv = [java, '-cp', cp, 'org.openjdk.jmh.Main', benchmark, '-f', '1', '-foe', 'true', '-t', '1',
                '-jvm', java, '-jvmArgs', ' '.join(JVM_ARGS), '-rf', 'json', '-rff', target]
        for key, value in sorted(params.items()):
            argv += ['-p', f'{key}={value}']
        if plan:
            argv += protocol.timing(manifest, kind)
        elif kind == 'read':
            argv += ['-bm', 'avgt', '-tu', 'us', '-wi', '2' if stage == 'pilot' else '5', '-w', '1s' if stage == 'pilot' else '2s',
                     '-i', '3' if stage == 'pilot' else '10', '-r', '1s' if stage == 'pilot' else '2s']
        else:
            argv += ['-bm', 'ss', '-tu', 'us', '-wi', '5' if stage == 'pilot' else '10', '-i', '5' if stage == 'pilot' else '30', '-bs', '1', '-wbs', '1']
        code = run(argv, raw / (name + '.log'), out)
        status = dict(item, exitCode=code, status='FAIL', raw=str(target), sourceSha256=manifest['sourceSha256'],
                      benchmarkGitSha=manifest['benchmarkGitSha'], executionWorkflowRunId=manifest['executionWorkflowRunId'],
                      executionWorkflowRunAttempt=manifest['executionWorkflowRunAttempt'],
                      candidateGitSha=manifest['candidateGitSha'], bundleSha256=args.seal,
                      pairingUnit=f"{os.environ.get('GITHUB_RUN_ID')}:attempt{manifest['executionWorkflowRunAttempt']}:{args.group}:block{item['block']}", hostMetadata='../host.json')
        status.update(protocol.identity(manifest))
        try:
            data = read_json(target)
            if code or len(data) != 1 or data[0]['params'] != {k: str(v) for k, v in params.items()} or data[0]['primaryMetric']['scoreUnit'] != 'us/op':
                raise ValueError('Invalid JMH result/parameters/unit')
            protocol.validate_jmh(manifest, data[0], kind)
            metric = data[0]['primaryMetric']; iterations = metric['rawData']
            if len(iterations) != 1 or not iterations[0] or any(not math.isfinite(v) or v <= 0 for v in iterations[0]):
                raise ValueError('Expected one JVM fork with finite positive samples')
            with target.with_suffix('.csv').open('w', newline='') as handle:
                writer = csv.writer(handle); writer.writerow(['block', 'iteration', 'microsecondsPerOperation', 'paramsJSON'])
                for index, value in enumerate(iterations[0], 1):
                    writer.writerow([item['block'], index, value, json.dumps(params, sort_keys=True)])
            status.update(status='PASS', rawSha256=digest(target), csvSha256=digest(target.with_suffix('.csv')))
        except (OSError, ValueError, KeyError) as error:
            status['failure'] = type(error).__name__ + ': ' + str(error); failures.append(name)
        status['logSha256'] = digest(raw / (name + '.log'))
        write_json(raw / (name + '.status.json'), status)
    write_json(out / 'completion.json', dict(status='PASS' if not failures else 'PARTIAL', planned=len(planned), failures=failures,
                                            bundleSha256=args.seal, group=args.group, block=args.block))
    if args.command == 'pilot':
        findings = pilot_findings(raw)
        write_json(out / 'pilot-review.json', dict(bundleSha256=args.seal, candidateGitSha=manifest['candidateGitSha'],
                   sourceSha256=manifest['sourceSha256'], runtimeSha256=manifest['runtimeSha256'],
                   validationGateSha256=digest(args.gate / 'validation-gate.json'), pilotCompletionSha256=digest(out / 'completion.json'),
                   pilotRunUrl='https://github.com/' + os.environ.get('GITHUB_REPOSITORY', 'Kronos-orm/orm-benchmark-project') + '/actions/runs/' + str(os.environ.get('GITHUB_RUN_ID')),
                   findings=findings, limitation='Short pilot diagnostics preserve observed warmup and iteration variability; they do not prove steady-state or establish formal rankings'))
    if failures:
        raise SystemExit(1)


def aggregate(args):
    manifest = verify(args.bundle, args.seal)
    plan = None
    if getattr(args, 'execution_plan', None):
        plan = protocol.read_plan(args.execution_plan, getattr(args, 'expected_context', None))
        protocol.verify_controller(plan)
        manifest = protocol.bind(manifest, plan, args.seal)
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    manifest = dict(manifest, bundleSha256=args.seal, executionWorkflowRunId=os.environ.get('GITHUB_RUN_ID'),
                    executionWorkflowRunAttempt=os.environ.get('GITHUB_RUN_ATTEMPT', '1'), executionStage='measure-aggregate')
    if getattr(args, 'frozen', None):
        transport = read_json(args.frozen)
        if any(transport[k] != manifest[k] for k in ['candidateGitSha', 'benchmarkGitSha']): raise ValueError('Aggregate transport plan differs from source')
        manifest['artifactTransport'] = transport['reuseArtifacts']
    write_json(out / 'build-manifest.json', manifest)
    if plan:
        protocol.install(out, plan)
        controller = plan['executionContext']['controller']
        snapshot = args.execution_plan.parent / controller['snapshotFile']
        protocol.verify_snapshot(snapshot, plan['executionContext'])
        shutil.copyfile(snapshot, out / snapshot.name)
    receipts, bindings, host_map = {}, {}, {}
    def audited_copy(source, destination, origin, identifier):
        relative = str(source.relative_to(origin))
        if relative not in receipts[identifier]['files'] or digest(source) != receipts[identifier]['files'][relative]:
            raise ValueError('Unscanned source cannot enter aggregate')
        target = out / destination; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        bindings[str(target.relative_to(out))] = dict(receipt=identifier, file=relative)
    raw = out / 'measure'; raw.mkdir()
    planned = read_json(args.bundle / 'expected-schedule.json')
    write_json(raw / 'schedule.json', planned)
    expected = {cell_name(item): item for item in planned}; seen = set(); failures = []
    for shard in sorted(args.shards.glob('shard-*')):
        metadata = read_json(shard / 'build-manifest.json') if (shard / 'build-manifest.json').exists() else None
        if metadata is None:
            failures.append(dict(shard=shard.name, status='NO_PROVENANCE')); continue
        if metadata['bundleSha256'] != args.seal or metadata['sourceSha256'] != manifest['sourceSha256']:
            raise ValueError('Foreign shard provenance: ' + shard.name)
        protocol.same(manifest, metadata)
        receipts[shard.name] = verify_receipt(shard, manifest, manifest['executionWorkflowRunId'])
        evidence = out / 'hosts' / shard.name; evidence.mkdir(parents=True)
        for file in shard.glob('host*'):
            audited_copy(file, str((evidence / file.name).relative_to(out)), shard, shard.name)
        for file in ['completion.json', 'environment.json', 'environment.log', 'commands.jsonl']:
            if (shard / file).exists(): audited_copy(shard / file, str((evidence / file).relative_to(out)), shard, shard.name)
        if (shard / 'commands.jsonl').exists():
            with (out / 'commands.jsonl').open('a') as handle:
                handle.write((shard / 'commands.jsonl').read_text())
        for statusfile in (shard / 'measure').glob('*.status.json'):
            name = statusfile.name.removesuffix('.status.json'); status = read_json(statusfile)
            if name not in expected or name in seen or any(status.get(k) != expected[name][k] for k in ['kind', 'block', 'params', 'group']):
                raise ValueError('Duplicate or unplanned result cell: ' + name)
            if shard.name != f"shard-{status['group']}-{status['block']}":
                raise ValueError('Result cell came from another runner/block group')
            if status.get('bundleSha256') != args.seal or status.get('candidateGitSha') != manifest['candidateGitSha']:
                raise ValueError('Status provenance mismatch')
            protocol.same(manifest, status)
            seen.add(name)
            host_map[statusfile.name] = str((evidence / 'host.json').relative_to(out))
            for suffix, hashkey in [('.json', 'rawSha256'), ('.csv', 'csvSha256'), ('.log', 'logSha256')]:
                source = shard / 'measure' / (name + suffix)
                if hashkey in status and (not source.is_file() or digest(source) != status[hashkey]):
                    raise ValueError('Raw evidence digest mismatch: ' + name + suffix)
                if source.is_file(): audited_copy(source, 'measure/' + source.name, shard, shard.name)
            audited_copy(statusfile, 'measure/' + statusfile.name, shard, shard.name)
    write_json(out / 'ci-host-map.json', host_map)
    write_json(out / 'ci-coverage.json', dict(planned=780, received=len(seen), notRun=sorted(set(expected) - seen), shardFailures=failures,
                    inference='Within-scenario ORM comparisons pair block and runner VM. Hosted hardware variation limits generalization.'))
    if list(args.bundle.glob('source-*.tar.gz')): protocol.runtime_source_snapshot(args.bundle,out)
    if args.gate and args.gate.exists():
        receipts['gate'] = verify_receipt(args.gate, manifest, manifest['executionWorkflowRunId'])
        for file in args.gate.rglob('*'):
            if file.is_file() and file.name != RECEIPT:
                relative = str(file.relative_to(args.gate))
                audited_copy(file, 'preflight/' + relative, args.gate, 'gate')
                if relative.startswith('validation/') or relative == 'validation-gate.json': audited_copy(file, relative, args.gate, 'gate')
    statuses = [read_json(p) for p in raw.glob('*.status.json')]
    try:
        if any(s['status'] == 'PASS' for s in statuses):
            analyzer = ROOT / 'scripts/analyze_results.py' if plan else args.bundle / 'scripts/analyze_results.py'
            subprocess.run([sys.executable, analyzer, '--run', out], check=True)
        else:
            write_json(out / 'analysis-unavailable.json', dict(status='NO_SUCCESSFUL_FORMAL_MEASUREMENTS', numericResults=False))
    finally:
        finish_aggregate(out, manifest, receipts, bindings)
    if len(seen) != 780 or failures or any(s['status'] != 'PASS' for s in statuses):
        raise SystemExit(1)


def main():
    require_single_attempt()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['pack', 'reuse', 'verify', 'plan', 'validate', 'pilot', 'shard', 'aggregate'])
    parser.add_argument('--bundle', type=Path); parser.add_argument('--seal')
    parser.add_argument('--out', type=Path); parser.add_argument('--candidate', type=Path)
    parser.add_argument('--classpath', type=Path); parser.add_argument('--frozen', type=Path)
    parser.add_argument('--gate', type=Path); parser.add_argument('--group', choices=GROUPS, default=GROUPS[0])
    parser.add_argument('--block', type=int, choices=range(1, 6), default=1)
    parser.add_argument('--pilot-review', default='{}'); parser.add_argument('--shards', type=Path)
    parser.add_argument('--pilot', type=Path); parser.add_argument('--source-run-id')
    parser.add_argument('--execution-plan', type=Path); parser.add_argument('--expected-context')
    args = parser.parse_args()
    if args.command == 'pack': pack(args)
    elif args.command == 'reuse': reuse(args)
    elif args.command == 'verify': print(verify(args.bundle, args.seal)['candidateGitSha'])
    elif args.command == 'plan': print(json.dumps(dict(include=[dict(group=g, block=b) for g in GROUPS for b in range(1, 6)])))
    elif args.command == 'aggregate': aggregate(args)
    else: execute_stage(args)


if __name__ == '__main__':
    main()
