#!/usr/bin/env python3
"""Explicit staged runner. No command is executed on import; load authorization is required."""
from __future__ import annotations
import argparse
import datetime as dt
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import random
import statistics
import re
import signal
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORMS = ['Jdbc', 'Kronos', 'Jpa', 'Jimmer', 'Ktorm', 'Mybatis']
JVM_ARGS = ['-Xms1g', '-Xmx1g', '-XX:+UseG1GC', '-Duser.timezone=UTC']
SEED = 2026102704


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def catalog_versions(text):
    import tomllib
    if not text:return []
    versions=tomllib.loads(text)['versions']
    names={'kotlin':'Kotlin','kronos':'Kronos','mysql-jdbc-driver':'MySQL Connector/J','druid':'Druid','hibernate':'Hibernate ORM','jimmer':'Jimmer','ktorm':'Ktorm','mybatisPlus':'MyBatis-Plus','mybatisCore':'MyBatis core','ksp':'KSP','jackson':'Jackson','jacksonAnnotations':'Jackson annotations','jmh':'JMH'}
    return [dict(name=name,version=versions[key]['strictly'] if isinstance(versions[key],dict) else versions[key]) for key,name in names.items()]


def source_files():
    candidates = []
    for path in ROOT.rglob('*'):
        relative = path.relative_to(ROOT)
        if any(part in {'.git', '.gradle', '.idea', 'build', '.kotlin'} for part in relative.parts):
            continue
        if path.is_file() and not path.is_symlink() and (
                (relative.parts[0] == 'config' and path.suffix == '.json')
                or (relative.parts[:2] == ('.github', 'workflows') and path.suffix in {'.yml', '.yaml'})
                or path.suffix in {'.java', '.kt', '.kts', '.toml', '.properties', '.py', '.jfc'} or path.name in {'gradlew', 'gradlew.bat', 'gradle-wrapper.jar', 'gradle.lockfile'}):
            candidates.append(path)
    return sorted(candidates)


def source_digest():
    entries = {str(p.relative_to(ROOT)): digest(p) for p in source_files()}
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest(), entries


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def read_json(path):
    return json.loads(path.read_text())


def safe_environment(java_home):
    # Do not inherit user JVM injection flags or unrelated credentials into child tools.
    allowed = {'HOME', 'PATH', 'TMPDIR', 'LANG', 'LC_ALL', 'USER', 'LOGNAME', 'SHELL'}
    env = {k: v for k, v in os.environ.items() if k in allowed}
    env['JAVA_HOME'] = str(java_home)
    env['PATH'] = str(java_home / 'bin') + ':' + env.get('PATH', '/usr/bin:/bin')
    return env


def execute(argv, log, out, env):
    log.parent.mkdir(parents=True, exist_ok=True)
    record = {'argv': [str(a) for a in argv], 'cwd': str(ROOT), 'environmentKeys': sorted(env),
              'started': dt.datetime.now(dt.timezone.utc).isoformat(), 'log': str(log)}
    started = time.monotonic()
    with log.open('w') as handle:
        process = subprocess.Popen([str(a) for a in argv], cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = process.wait()
        except KeyboardInterrupt:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.wait()
            code = 130
    record.update(exitCode=code, elapsedSeconds=time.monotonic() - started,
                  finished=dt.datetime.now(dt.timezone.utc).isoformat())
    with (out / 'commands.jsonl').open('a') as handle:
        handle.write(json.dumps(record, sort_keys=True) + '\n')
    return code


def classpath_manifest(classpath):
    result = {}
    for item in classpath.split(os.pathsep):
        path = Path(item)
        if path.is_file():
            result[item] = digest(path)
        elif path.is_dir():
            entries = {str(p.relative_to(path)): digest(p) for p in sorted(path.rglob('*')) if p.is_file()}
            result[item] = hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()
        else:
            raise RuntimeError('Missing runtime classpath entry: ' + item)
    return result


def make_private_jfc(java_home, target):
    # Copy standard JDK profile settings, disabling environment and system property payloads.
    tree = ET.parse(java_home / 'lib/jfr/profile.jfc')
    root = tree.getroot()
    for name in ['jdk.InitialEnvironmentVariable', 'jdk.InitialSystemProperty']:
        event = next((e for e in root.findall('event') if e.get('name') == name), None)
        if event is None:
            event = ET.SubElement(root, 'event', {'name': name})
        setting = next((s for s in event.findall('setting') if s.get('name') == 'enabled'), None)
        if setting is None:
            setting = ET.SubElement(event, 'setting', {'name': 'enabled'})
        setting.text = 'false'
        setting.attrib.pop('control', None)
    tree.write(target, encoding='utf-8', xml_declaration=True)


def cases(stage):
    if stage == 'profile':
        return [('read', dict(projection='entity', tableRows=100000, resultRows=n, access='uniform')) for n in [1, 100]]
    if stage == 'pilot':
        reads = [('read', dict(projection=p, tableRows=100000, resultRows=n, access='uniform'))
                 for p, n in itertools.product(['entity', 'map', 'scalar'], [1, 100])]
    else:
        reads = [('read', dict(projection=p, tableRows=t, resultRows=n, access=a))
                 for p, t, n, a in itertools.product(['entity', 'map', 'scalar'], [1000, 100000], [1, 100], ['hot', 'uniform'])]
    return reads + [('write', dict(transactionRows=n)) for n in [1, 100]]


def pilot_findings(raw):
    findings = []
    for statusfile in sorted(raw.glob('*.status.json')):
        status = read_json(statusfile)
        item = dict(cell=statusfile.name, status=status['status'])
        if status['status'] == 'PASS':
            target = raw / Path(status['raw']).name
            if digest(target) != status['rawSha256']: raise ValueError('Pilot raw evidence changed')
            result = read_json(target)[0]['primaryMetric']['rawData'][0]
            warmup = [float(v) for v in re.findall(r'# Warmup Iteration\s+\d+:\s+([0-9.eE+-]+)\s+us/op', (raw / statusfile.name.replace('.status.json', '.log')).read_text())]
            item.update(measurementIterations=len(result), meanUS=statistics.mean(result), medianUS=statistics.median(result),
                        sampleCV=statistics.stdev(result) / statistics.mean(result) if len(result) > 1 else None,
                        warmupUS=warmup, rawSha256=status['rawSha256'])
        findings.append(item)
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['build', 'validate', 'pilot', 'measure', 'profile'])
    parser.add_argument('--candidate-repo', required=True, type=Path)
    parser.add_argument('--candidate-sha', required=True)
    parser.add_argument('--private-dir', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--java-home', type=Path, default=Path('/usr/local/Cellar/openjdk@21/21.0.10/libexec/openjdk.jdk/Contents/Home'))
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--profiler', choices=['gc', 'jfr'], default='gc')
    options = parser.parse_args()
    if os.environ.get('BENCH_ALLOW_LOAD') != '1':
        parser.error('Load work is disabled. Set BENCH_ALLOW_LOAD=1 only after the main task explicitly releases local validation resources.')
    if not re.fullmatch('[0-9a-f]{40}', options.candidate_sha):
        parser.error('candidate-sha must be the exact approved 40-character Git SHA')
    repo, private, out = options.candidate_repo.resolve(), options.private_dir.resolve(), options.out.resolve()
    if not repo.is_dir() or not (repo / 'com/kotlinorm').is_dir():
        parser.error('candidate-repo must be the isolated published Maven repository')
    if private == ROOT or ROOT in private.parents:
        parser.error('private-dir must be outside the benchmark repository')
    if not options.java_home.joinpath('bin/java').is_file():
        parser.error('Pinned JDK not found')
    out.mkdir(parents=True, exist_ok=True)
    environment = safe_environment(options.java_home)
    environment['KRONOS_CANDIDATE_REPO'] = str(repo)
    source_sha, sources = source_digest()
    candidate_jars = {str(p.relative_to(repo)): digest(p) for p in sorted((repo / 'com/kotlinorm').rglob('*.jar'))}
    if not candidate_jars:
        parser.error('No candidate JARs in the approved repository')
    provenance = {'candidateGitSha': options.candidate_sha, 'candidateRepository': str(repo), 'candidateJars': candidate_jars,
                  'sourceSha256': source_sha, 'sourceFiles': sources, 'javaHome': str(options.java_home), 'jvmArgs': JVM_ARGS,
                  'seed': SEED, 'benchmarkBaseSha': 'c8cfb23a4e2478def2feb8d579d81b9782d77aa7',
                  'versionCatalogTOML': (ROOT / 'libs.versions.toml').read_text(),
                  'catalogVersions': catalog_versions((ROOT/'libs.versions.toml').read_text())}
    if options.stage == 'build':
        if (out / 'build-manifest.json').exists():
            raise RuntimeError('Preserve the existing run provenance; build into a fresh output directory')
        code = execute([ROOT / 'gradlew', '--no-daemon', '--max-workers=1', '--write-locks', 'clean', 'classes', 'writeRuntimeClasspath'], out / 'build.log', out, environment)
        if code:
            raise SystemExit(code)
        # Lockfile generation is part of provenance, so capture sources after the successful build.
        source_sha, sources = source_digest()
        provenance.update(sourceSha256=source_sha, sourceFiles=sources)
        classpath = (ROOT / 'build/runtime-classpath.txt').read_text().strip()
        runtime = classpath_manifest(classpath)
        approved_hashes = set(candidate_jars.values())
        approved_names = {Path(name).name for name in candidate_jars}
        for path, sha in runtime.items():
            if (Path(path).name in approved_names or 'com.kotlinorm' in Path(path).parts) and path.endswith('.jar') and sha not in approved_hashes:
                raise RuntimeError('Runtime Kronos JAR does not match approved candidate: ' + Path(path).name)
        provenance.update(runtimeClasspath=classpath, runtimeArtifacts=runtime)
        for label, command in {
            'os': ['/usr/bin/sw_vers'], 'architecture': ['/usr/bin/uname', '-m'],
            'cpu-memory': ['/usr/sbin/sysctl', 'machdep.cpu.brand_string', 'hw.memsize', 'hw.physicalcpu', 'hw.logicalcpu'],
            'jdk': [options.java_home / 'bin/java', '-version']
        }.items():
            path = out / ('environment-build-' + label + '.log')
            code = execute(command, path, out, environment)
            provenance.setdefault('environmentCommands', {})[label] = {'exitCode': code, 'output': path.read_text()}
        write_json(out / 'build-manifest.json', provenance)
        with tarfile.open(out / ('source-' + source_sha[:16] + '.tar.gz'), 'w:gz') as archive:
            for path in source_files():
                archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
        return
    built = read_json(out / 'build-manifest.json')
    for key in ['candidateGitSha', 'candidateRepository', 'candidateJars', 'sourceSha256', 'javaHome', 'jvmArgs']:
        if built.get(key) != provenance.get(key):
            raise RuntimeError('Build provenance changed; rebuild before continuing: ' + key)
    classpath = built['runtimeClasspath']
    if classpath_manifest(classpath) != built['runtimeArtifacts']:
        raise RuntimeError('Runtime artifacts changed after build')
    secret_file = private / 'database-secrets.json'
    if secret_file.stat().st_mode & 0o077:
        raise RuntimeError('Private database secret file must have mode 600')
    environment['BENCH_DB_PASSWORD'] = read_json(secret_file)['benchmarkPassword']
    java = options.java_home / 'bin/java'
    validation = out / 'validation'
    if options.stage == 'validate':
        code = execute([java, *JVM_ARGS, '-cp', classpath, 'com.kotlinorm.benchmark.ValidateBenchmark', validation], out / 'validation.log', out, environment)
        if code:
            (out / 'validation-gate.json').unlink(missing_ok=True)
            raise SystemExit(code)
        if read_json(validation / 'PASS.json')['status'] != 'PASS':
            raise RuntimeError('Validation did not produce a PASS marker')
        write_json(out / 'validation-gate.json', {'sourceSha256': source_sha, 'candidateGitSha': options.candidate_sha,
                                                'runtimeArtifacts': built['runtimeArtifacts'], 'environmentSha256': digest(validation / 'environment.json')})
        return
    gate = read_json(out / 'validation-gate.json')
    if gate['sourceSha256'] != source_sha or gate['candidateGitSha'] != options.candidate_sha or gate['runtimeArtifacts'] != built['runtimeArtifacts']:
        raise RuntimeError('Validation gate does not match this executable')
    if options.stage == 'measure':
        if not (out / 'pilot-complete.json').exists() or not (out / 'pilot-review.json').exists():
            raise RuntimeError('Complete the pilot to generate its statistical evidence before the formal matrix')
        review = read_json(out / 'pilot-review.json')
        if review.get('sourceSha256') != source_sha or review.get('candidateGitSha') != options.candidate_sha or review.get('runtimeArtifacts') != built['runtimeArtifacts'] or review.get('validationGateSha256') != digest(out / 'validation-gate.json') or review.get('pilotCompletionSha256') != digest(out / 'pilot/completion.json') or review.get('findings') != pilot_findings(out / 'pilot'):
            raise RuntimeError('Pilot review is missing evidence or refers to another source revision')
    snapshot = out / ('environment-' + options.stage + '.json')
    if execute([java, *JVM_ARGS, '-cp', classpath, 'com.kotlinorm.benchmark.InspectEnvironment', snapshot], out / ('environment-' + options.stage + '.log'), out, environment):
        raise RuntimeError('Could not inspect the dedicated server environment')
    if digest(snapshot) != gate['environmentSha256']:
        raise RuntimeError('Server/JVM configuration differs from the correctness validation gate')
    raw = out / ('profile-' + options.profiler if options.stage == 'profile' else options.stage)
    raw.mkdir(parents=True, exist_ok=True)
    if options.stage == 'profile' and options.profiler == 'jfr':
        make_private_jfc(options.java_home, raw / 'private-safe-profile.jfc')
    blocks = 5 if options.stage == 'measure' else 1
    schedule = []
    for block in range(1, blocks + 1):
        groups = cases(options.stage)
        random.Random(SEED + block).shuffle(groups)
        for kind, params in groups:
            orms = ORMS.copy()
            random.Random(str(SEED) + str(block) + json.dumps(params, sort_keys=True)).shuffle(orms)
            for orm in orms:
                schedule.append(dict(block=block, kind=kind, params=dict(orm=orm, **params)))
    write_json(raw / 'schedule.json', schedule)
    failures = []
    snapshot_stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    recorded_block = None
    for index, item in enumerate(schedule, 1):
        params, block, kind = item['params'], item['block'], item['kind']
        if recorded_block != block:
            for label, command in {'load': ['/usr/bin/uptime'], 'memory': ['/usr/bin/vm_stat'], 'power': ['/usr/bin/pmset', '-g', 'batt'], 'power-settings': ['/usr/bin/pmset', '-g', 'custom'], 'idle-cpu-baseline': ['/usr/bin/top', '-l', '3', '-s', '2', '-n', '10', '-stats', 'pid,command,cpu,mem'], 'thermal': ['/usr/bin/pmset', '-g', 'therm'], 'processes': ['/bin/ps', '-axo', 'pid,pcpu,pmem,comm']}.items():
                execute(command, raw / f'{snapshot_stamp}-block{block}-{label}.log', out, environment)
            recorded_block = block
        name = '-'.join([kind, f'b{block}'] + [f'{k}={v}' for k, v in sorted(params.items())])
        target, status = raw / (name + '.json'), raw / (name + '.status.json')
        if status.exists():
            if options.resume and read_json(status).get('status') == 'PASS':
                continue
            raise RuntimeError('Refusing to overwrite an existing result; use a fresh output directory or resume PASS results: ' + name)
        benchmark = 'com.kotlinorm.benchmark.' + ('ReadBenchmark.query' if kind == 'read' else 'InsertBenchmark.insertTransaction')
        argv = [java, '-cp', classpath, 'org.openjdk.jmh.Main', '^' + re.escape(benchmark) + '$', '-f', '1', '-t', '1', '-foe', 'true',
                '-jvm', java, '-jvmArgs', ' '.join(JVM_ARGS), '-rf', 'json', '-rff', target]
        for key, value in sorted(params.items()):
            argv += ['-p', f'{key}={value}']
        if kind == 'read':
            pilot = options.stage != 'measure'
            argv += ['-bm', 'avgt', '-tu', 'us', '-wi', '2' if pilot else '5', '-w', '1s' if pilot else '2s', '-i', '3' if pilot else '10', '-r', '1s' if pilot else '2s']
        else:
            argv += ['-bm', 'ss', '-tu', 'us', '-wi', '5' if options.stage == 'pilot' else '10', '-i', '5' if options.stage == 'pilot' else '30', '-bs', '1', '-wbs', '1']
        if options.stage == 'profile':
            profiler = 'gc' if options.profiler == 'gc' else f'jfr:dir={raw / name};configName={raw / "private-safe-profile.jfc"}'
            argv += ['-prof', profiler]
        print(f'{options.stage} {index}/{len(schedule)}: {name}', flush=True)
        code = execute(argv, raw / (name + '.log'), out, environment)
        result = dict(item, exitCode=code, status='FAIL', raw=str(target), sourceSha256=source_sha, candidateGitSha=options.candidate_sha)
        try:
            data = read_json(target)
            if code or len(data) != 1 or data[0]['params'] != {k: str(v) for k, v in params.items()} or not data[0]['primaryMetric']['rawData']:
                raise RuntimeError('Missing/inconsistent JMH result')
            result['status'] = 'PASS'
            with target.with_suffix('.csv').open('w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['benchmark', 'block', 'metric', 'forkWithinCommand', 'iteration', 'value', 'unit', 'paramsJSON'])
                metrics = {'primary': data[0]['primaryMetric'], **data[0].get('secondaryMetrics', {})}
                for metric, values in metrics.items():
                    for fork, iterations in enumerate(values.get('rawData') or [], 1):
                        for iteration, value in enumerate(iterations, 1):
                            writer.writerow([benchmark, block, metric, fork, iteration, value, values['scoreUnit'], json.dumps(params, sort_keys=True)])
        except (OSError, ValueError, KeyError, RuntimeError) as failure:
            result['failure'] = type(failure).__name__ + ': ' + str(failure)
            failures.append(name)
        result['logSha256'] = digest(raw / (name + '.log'))
        if result['status'] == 'PASS':
            result['rawSha256'] = digest(target)
            result['csvSha256'] = digest(target.with_suffix('.csv'))
        write_json(status, result)
        if code == 130:
            raise SystemExit(130)
    write_json(raw / 'completion.json', {'status': 'PASS' if not failures else 'PARTIAL', 'failures': failures, 'plannedCases': len(schedule)})
    if options.stage == 'pilot' and not failures:
        write_json(out / 'pilot-complete.json', {'sourceSha256': source_sha, 'status': 'PASS'})
        write_json(out / 'pilot-review.json', dict(sourceSha256=source_sha, candidateGitSha=options.candidate_sha, runtimeArtifacts=built['runtimeArtifacts'], validationGateSha256=digest(out / 'validation-gate.json'), pilotCompletionSha256=digest(raw / 'completion.json'), findings=pilot_findings(raw)))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
