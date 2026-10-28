#!/usr/bin/env python3
"""Export measured results to the established result/readme.md website contract. Never deploys."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import quote, urlsplit, unquote
import zipfile
import sys
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = 'https://raw.githubusercontent.com/Kronos-orm/orm-benchmark-project/result'
ORMS = ['Jdbc', 'Kronos', 'Jpa', 'Jimmer', 'Ktorm', 'Mybatis']


def load(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def absolute(base, path):
    parsed = urlsplit(base)
    if parsed.scheme != 'https' or not parsed.netloc or any(c.isspace() for c in base) or parsed.query or parsed.fragment:
        raise ValueError('Publication base must be an absolute HTTPS directory URL without query/fragment')
    return base.rstrip('/') + '/' + quote(str(path), safe='/')


def locate_raw(statusfile, raw):
    # A status can reference only its sibling raw file; a JSON path cannot export arbitrary files.
    return statusfile.parent / unquote(Path(urlsplit(raw).path).name)


def scan_secrets(directory, values):
    needles = [v.encode() for v in values if isinstance(v, str) and v]
    for path in directory.rglob('*'):
        if not path.is_file():
            continue
        content = path.read_bytes()
        if any(value in content for value in needles):
            raise ValueError('Private credential found in publication file; value withheld: ' + str(path.relative_to(directory)))
        if path.name.endswith('.tar.gz'):
            with tarfile.open(path) as archive:
                for member in archive.getmembers():
                    if not member.isfile():
                        continue
                    with archive.extractfile(member) as handle:
                        content = handle.read()
                        if any(value in content for value in needles):
                            raise ValueError('Private credential found in source archive; value withheld: ' + member.name)


def export(run, output, base, secret_file, partial_reason, browse_base=None, ci_audits=False):
    if browse_base is None:
        parsed = urlsplit(base)
        parts = parsed.path.strip('/').split('/')
        browse_base = 'https://github.com/' + '/'.join(parts[:2]) + '/blob/' + parts[2] if parsed.netloc == 'raw.githubusercontent.com' and len(parts) == 3 else base
    absolute(browse_base, 'readme.md')
    if output.exists():
        raise ValueError('Refusing to replace an existing publication directory')
    if ci_audits:
        from secret_audit import verify_aggregate
        verify_aggregate(run)
        secrets = {}
    else:
        if secret_file is None or secret_file.stat().st_mode & 0o077:
            raise ValueError('Generated experiment secret file with mode600 is required')
        secrets = load(secret_file)
        if not isinstance(secrets.get('benchmarkPassword'), str) or not secrets['benchmarkPassword']:
            raise ValueError('Real experiment credential is required; dummy credentials are not supported')
    summary = load(run / 'analysis/summary.json')
    manifest = load(run / 'build-manifest.json')
    gate = load(run / 'validation-gate.json')
    if load(run / 'validation/PASS.json').get('status') != 'PASS':
        raise ValueError('Correctness/SQL validation did not pass')
    for key in ['sourceSha256', 'candidateGitSha']:
        if summary[key] != manifest[key] or gate[key] != manifest[key]:
            raise ValueError('Candidate/source identity differs between analysis, build and validation')
    coverage = summary['coverage']
    if not coverage['passedForkRuns']:
        raise ValueError('No measured fork data; a publication cannot be generated')
    if ci_audits and (coverage['failedForkRuns'] or coverage['notRunForkRuns']) and not partial_reason:
        partial_reason = f"CI recorded {coverage['failedForkRuns']} failed and {coverage['notRunForkRuns']} not-run cells; complete planned coverage and raw states remain visible."
    if (coverage['failedForkRuns'] or coverage['notRunForkRuns']) and not partial_reason:
        raise ValueError('Incomplete experiments require a concrete partial-reason explanation')
    figures = load(run / 'analysis/figures.json')
    report_id = manifest['candidateGitSha'][:12] + '-' + str(manifest.get('executionWorkflowRunId', 'local')) + '-a' + str(manifest.get('executionWorkflowRunAttempt', 1)) + '-' + manifest['sourceSha256'][:12] + '-' + digest(run / 'analysis/summary.json')[:10]
    prefix = 'runs/' + report_id
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix='benchmark-publication-', dir=output.parent)
    stage = Path(temporary.name) / 'publication'; stage.mkdir()
    def copy(source, relative):
        if source.is_symlink() or not source.is_file():
            raise ValueError('Missing/unsafe evidence file: ' + str(source))
        destination = stage / relative; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return relative
    def public(path):
        return absolute(base, path)
    def browse(path):
        return absolute(browse_base, path)
    try:
        copy(ROOT / 'report-web/index.html', 'index.html')
        copy(ROOT / 'report-web/report.css', 'assets/report.css')
        copy(ROOT / 'report-web/report.js', 'assets/report.js')
        for relative in ['build-manifest.json', 'commands.jsonl', 'validation-gate.json']:
            copy(run / relative, prefix + '/' + relative)
        if ci_audits:
            for relative in ['audit-provenance.json', 'ci-host-map.json']:
                copy(run / relative, prefix + '/' + relative)
        if (run / 'ci-coverage.json').is_file():
            copy(run / 'ci-coverage.json', prefix + '/ci-coverage.json')
        for source in sorted((run / 'hosts').rglob('*')):
            if source.is_file() and source.name != 'host-processes.log':
                copy(source, prefix + '/' + str(source.relative_to(run)))
        for source in sorted((run / 'validation').glob('*')):
            if source.is_file() and source.suffix in {'.json', '.log'}:
                copy(source, prefix + '/validation/' + source.name)
        copy(run / 'analysis/summary.json', prefix + '/analysis/summary.json')
        copy(run / 'analysis/summary.csv', prefix + '/analysis/summary.csv')
        copy(run / 'measure/schedule.json', prefix + '/measure/schedule.json')
        if (run / 'measure/completion.json').exists():
            copy(run / 'measure/completion.json', prefix + '/measure/completion.json')
        snapshots = [p for p in run.glob('source-*.tar.gz') if p.is_file()]
        if len(snapshots) != 1:
            raise ValueError('Expected exactly one source snapshot for this build')
        source_snapshot = copy(snapshots[0], prefix + '/' + snapshots[0].name)
        raw_records = {}
        for statusfile in sorted((run / 'measure').glob('*.status.json')):
            status = load(statusfile)
            if status['sourceSha256'] != manifest['sourceSha256'] or status['candidateGitSha'] != manifest['candidateGitSha']:
                raise ValueError('Raw status identity mismatch')
            key = status['kind'] + ':' + json.dumps({k: v for k, v in status['params'].items() if k != 'orm'}, sort_keys=True)
            entry = {'block': status['block'], 'status': status['status']}
            entry['statusPath'] = copy(statusfile, prefix + '/measure/' + statusfile.name)
            original = locate_raw(statusfile, status['raw'])
            if original.exists():
                if status['status'] == 'PASS' and digest(original) != status['rawSha256']:
                    raise ValueError('Raw JSON changed after measurement')
                entry['rawPath'] = copy(original, prefix + '/measure/' + original.name)
                for extension in ['.log', '.csv']:
                    sibling = original.with_suffix(extension)
                    if sibling.is_file():
                        checksum = status.get('logSha256' if extension == '.log' else 'csvSha256')
                        if checksum and digest(sibling) != checksum:
                            raise ValueError('Recorded evidence checksum mismatch')
                        entry['logPath' if extension == '.log' else 'csvPath'] = copy(sibling, prefix + '/measure/' + sibling.name)
            else:
                log = statusfile.with_name(statusfile.name.removesuffix('.status.json') + '.log')
                if log.is_file():
                    entry['logPath'] = copy(log, prefix + '/measure/' + log.name)
            entry['path'] = entry.get('rawPath', entry['statusPath'])
            entry['absoluteUrls'] = {k: public(v) for k, v in entry.items() if k.endswith('Path') or k == 'path'}
            raw_records.setdefault((key, status['params']['orm']), []).append(entry)
        # Global resource snapshots contain the CPU/power/thermal evidence. Process inventories stay local.
        for source in sorted((run / 'measure').glob('*.log')):
            if any(source.name.endswith('-' + label + '.log') for label in ['load', 'memory', 'power', 'power-settings', 'idle-cpu-baseline', 'thermal']):
                copy(source, prefix + '/measure/' + source.name)
        diagnostic_index = []
        for directory in [run / 'profile-gc', run / 'profile-jfr']:
            if directory.is_dir():
                for source in sorted(directory.rglob('*')):
                    if source.is_file() and not source.is_symlink():
                        relative = str(source.relative_to(run))
                        item = dict(localRunRelativePath=relative, sha256=digest(source), bytes=source.stat().st_size, included=False)
                        if source.suffix in {'.json', '.csv', '.log', '.jfc'}:
                            item['path'] = copy(source, prefix + '/' + relative); item['absoluteUrl'] = public(item['path']); item['included'] = True
                        diagnostic_index.append(item)
        write(stage / prefix / 'diagnostics-index.json', diagnostic_index)
        environment = load(run / 'validation/environment.json')
        commands = [json.loads(line) for line in (run / 'commands.jsonl').read_text().splitlines() if line.strip()]
        measured_commands = [c for c in commands if '/measure/' in c.get('log', '') and any(str(a).endswith('org.openjdk.jmh.Main') for a in c['argv'])]
        if not measured_commands:
            raise ValueError('Formal measurement command timestamps are missing')
        time_range = dict(start=min(c['started'] for c in measured_commands), end=max(c['finished'] for c in measured_commands))
        scenarios = []
        for key, definition in summary['caseDefinitions'].items():
            identifier = definition['kind'] + '-' + hashlib.sha256(key.encode()).hexdigest()[:14]
            scenario = dict(id=identifier, key=key, definition=definition, frameworks={}, details=prefix + '/cases/' + identifier + '.json')
            for orm in ORMS:
                value = dict(summary['summaries'][key][orm])
                value['n'] = len(value['forkMeansUS'])
                value['raw'] = sorted(raw_records.get((key, orm), []), key=lambda item: item['block'])
                scenario['frameworks'][orm] = value
            if key in figures:
                scenario['figure'] = {}
                for extension in ['png', 'svg', 'pdf']:
                    source = run / 'analysis' / figures[key][extension]
                    scenario['figure'][extension] = copy(source, prefix + '/figures/' + source.name)
                scenario['figure']['absoluteUrls'] = {k: public(v) for k, v in scenario['figure'].items()}
            write(stage / scenario['details'], dict(scenario, comparisons=summary.get('comparisons', {}).get(key, {}),
                                                  rowCountSensitivity={k: v for k, v in summary.get('rowCountSensitivity', {}).items() if k.startswith(key + ':')}))
            scenario['absoluteDetailsUrl'] = public(scenario['details'])
            scenarios.append(scenario)
        if len({s['id'] for s in scenarios}) != len(scenarios):
            raise ValueError('Scenario identifier collision')
        methodology = (ROOT / 'reports/kronos-0.4.0/reporting/statistical-interpretation.md').read_text()
        methodology = methodology.replace('状态：测量前规则，2026-10-27。用于约束后续报告，不包含跑分结果。', '本报告采用的统计与解释协议；协议登记日期：2026-10-27。')
        (stage / prefix / 'methodology.md').write_text(methodology)
        downloads = {'English analysis (Markdown)': prefix + '/report-en.md', '中文详细分析 (Markdown)': prefix + '/report-zh-CN.md', 'Statistics JSON': prefix + '/analysis/summary.json',
                     'Statistics CSV': prefix + '/analysis/summary.csv', 'Methodology': prefix + '/methodology.md',
                     'Commands': prefix + '/commands.jsonl', 'Build manifest': prefix + '/build-manifest.json',
                     'Source snapshot': source_snapshot, 'Diagnostics index': prefix + '/diagnostics-index.json'}
        if ci_audits: downloads['Real-secret scan receipts and derivation hashes'] = prefix + '/audit-provenance.json'
        commentary = load(run / 'analysis/commentary.json') if (run / 'analysis/commentary.json').is_file() else {}
        if commentary:
            copy(run / 'analysis/commentary.json', prefix + '/analysis/commentary.json')
        provenance_links = {'Kronos source / Kronos源码': 'https://github.com/Kronos-orm/Kronos-orm/tree/' + manifest['candidateGitSha']}
        if manifest.get('benchmarkGitSha'): provenance_links['Benchmark source / 基准源码'] = 'https://github.com/Kronos-orm/orm-benchmark-project/tree/' + manifest['benchmarkGitSha']
        for key, label in [('workflowRunId', 'Producer run / 构建运行'), ('executionWorkflowRunId', 'Measurement run / 测量运行')]:
            if manifest.get(key): provenance_links[label] = 'https://github.com/Kronos-orm/orm-benchmark-project/actions/runs/' + str(manifest[key]) + '/attempts/' + str(manifest.get('executionWorkflowRunAttempt' if key.startswith('execution') else 'workflowRunAttempt', 1))
        report = dict(schemaVersion=1, commentary=commentary, reportId=report_id, candidateGitSha=manifest['candidateGitSha'], benchmarkSourceSha256=manifest['sourceSha256'],
                      provenanceLinks=provenance_links,
                      runRangeUTC=time_range, coverage=coverage, partialReason=partial_reason, environment=environment,
                      executionEnvironment=manifest.get('executionEnvironment', 'Local controlled JVM/MySQL experiment'),
                      requestedVersions=[{k: c[k] for k in ['name', 'version', 'released', 'release', 'pom'] if k in c} for c in manifest.get('versionAuditSnapshot', {}).get('components', [])],
                      resolvedArtifacts=[dict(file=Path(k).name, sha256=v) for k, v in manifest['runtimeArtifacts'].items() if k.endswith('.jar')],
                      downloads=downloads, absoluteDownloadUrls={k: public(v) for k, v in downloads.items()},
                      portableZipUrl=public(prefix + '/report.zip'), scenarios=scenarios)
        from publication_markdown import render_summary, render_detailed
        (stage / 'readme.md').write_text(render_summary(report, public, browse))
        english = render_detailed(report, 'en', public, browse)
        (stage / prefix / 'report-en.md').write_text(english)
        (stage / prefix / 'report-zh-CN.md').write_text(render_detailed(report, 'zh-CN', public, browse))
        (stage / prefix / 'report.md').write_text(english)
        # The browser index is compact; raw references are loaded per scene from its details JSON.
        compact = dict(report, detailLevel='index', scenarios=[
            dict(scene, frameworks={orm: {k: v for k, v in score.items() if k != 'raw'} for orm, score in scene['frameworks'].items()})
            for scene in scenarios
        ])
        write(stage / 'data/report.json', compact)
        write(stage / prefix / 'report.json', dict(report, detailLevel='complete'))
        if not ci_audits: scan_secrets(stage, list(secrets.values()))
        file_index = {str(p.relative_to(stage)): dict(sha256=digest(p), bytes=p.stat().st_size) for p in sorted(stage.rglob('*')) if p.is_file()}
        write(stage / 'publication-files.json', dict(schemaVersion=1, reportId=report_id, publicBase=base.rstrip('/'), browseBase=browse_base.rstrip('/'), files=file_index))
        archive_path = stage / prefix / 'report.zip'
        members = [p for p in sorted(stage.rglob('*')) if p.is_file()]
        archive_time = dt.datetime.fromisoformat(summary['generatedAt'].replace('Z', '+00:00')).astimezone(dt.timezone.utc)
        timestamp = (archive_time.year, archive_time.month, archive_time.day, archive_time.hour, archive_time.minute, archive_time.second // 2 * 2)
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in members:
                entry = zipfile.ZipInfo(str(path.relative_to(stage)), date_time=timestamp)
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        archive_path.with_suffix('.zip.sha256').write_text(digest(archive_path) + '  report.zip\n')
        from validate_publication import validate
        validate(stage)
        stage.rename(output)
        print('Exported a reviewed local publication bundle; no push or deployment occurred: ' + str(output))
    finally:
        temporary.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    scan_mode = parser.add_mutually_exclusive_group(required=True)
    scan_mode.add_argument('--secret-file', type=Path, help='Real generated experiment database-secrets.json; never the original user backup')
    scan_mode.add_argument('--ci-audits', action='store_true', help='Verify all real-secret receipts and aggregate derivation hashes; no passwords are transported')
    parser.add_argument('--public-base', default=DEFAULT_BASE)
    parser.add_argument('--partial-reason', default='')
    parser.add_argument('--browse-base', help='Absolute rendered-Markdown base; inferred for the GitHub raw default')
    args = parser.parse_args()
    export(args.run.resolve(), args.out.resolve(), args.public_base, args.secret_file.resolve() if args.secret_file else None, args.partial_reason, args.browse_base, args.ci_audits)


if __name__ == '__main__':
    main()
