#!/usr/bin/env python3
"""Verify the website Markdown URL contract and an immutable static-report bundle without a DB."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import itertools
import statistics
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit, unquote
import zipfile
import sys
sys.dont_write_bytecode = True
import execution_protocol as protocol


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_file(root, relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or '\\' in relative or urlsplit(relative).scheme:
        raise ValueError('Invalid artifact path')
    file = root / relative
    if file.is_symlink() or not file.is_file():
        raise ValueError('Missing artifact: ' + relative)
    return file


def validate(root, expected_public_base=None):
    if root.is_symlink():
        raise ValueError('Publication root must be an actual directory')
    root = root.resolve()
    if any(path.suffix.lower() in {'.html','.css','.js'} for path in root.rglob('*') if path.is_file()):
        raise ValueError('Publication must contain Markdown, figures and evidence data')
    if any(path.is_symlink() for path in root.rglob('*')):
        raise ValueError('Publication tree contains a symlink')
    manifest = json.loads(safe_file(root, 'publication-files.json').read_text())
    if manifest.get('schemaVersion') != 1:
        raise ValueError('Unsupported publication manifest')
    base = manifest['publicBase'].rstrip('/')
    if expected_public_base and base != expected_public_base.rstrip('/'):
        raise ValueError('Publication base differs from the website deployment target')
    if not base.startswith('https://'):
        raise ValueError('Expected absolute HTTPS publication base')
    for relative, expected in manifest['files'].items():
        file = safe_file(root, relative)
        if digest(file) != expected['sha256'] or file.stat().st_size != expected['bytes']:
            raise ValueError('Publication file checksum differs: ' + relative)
    for file in root.rglob('*.md'):
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', file.read_text()):
            if not target.startswith('https://'):
                raise ValueError('Website Markdown contains a non-absolute link: ' + str(file.relative_to(root)))
            for link_base in {base, manifest.get('browseBase', base)}:
                if target.startswith(link_base + '/'):
                    relative = unquote(target[len(link_base) + 1:])
                    safe_file(root, relative)
    root_markdown = safe_file(root, 'readme.md').read_text()
    if len(re.findall(r'!\[[^\]]*\]\([^)]+\)', root_markdown)) > 3 or 'English analysis' not in root_markdown or '中文详细分析' not in root_markdown:
        raise ValueError('Website entry must remain a compact bilingual summary with at most three registered figures')
    report = json.loads(safe_file(root, 'data/report.json').read_text())
    if report.get('schemaVersion') != 1 or report['reportId'] != manifest['reportId'] or not report['scenarios']:
        raise ValueError('Report data identity/schema mismatch')
    protocol.identity(report)
    for relative in report['downloads'].values():
        safe_file(root, relative)
    expected_scenes = {('read', json.dumps(dict(projection=p, tableRows=t, resultRows=n, access=a), sort_keys=True))
                       for p, t, n, a in itertools.product(['entity', 'map', 'scalar'], [1000, 100000], [1, 100], ['hot', 'uniform'])}
    expected_scenes |= {('write', json.dumps(dict(transactionRows=n), sort_keys=True)) for n in [1, 100]}
    actual_scenes = {(s['definition']['kind'], json.dumps(s['definition']['parameters'], sort_keys=True)) for s in report['scenarios']}
    if actual_scenes != expected_scenes or len(actual_scenes) != len(report['scenarios']):
        raise ValueError('Publication scene matrix differs from the registered design')
    observed = {'PASS': 0, 'FAIL': 0}
    expected_frameworks = {'Jdbc', 'Kronos', 'Jpa', 'Jimmer', 'Ktorm', 'Mybatis'}
    for scenario in report['scenarios']:
        if set(scenario['frameworks']) != expected_frameworks:
            raise ValueError('Framework coverage differs from the shared comparison design')
        detail = json.loads(safe_file(root, scenario['details']).read_text())
        if detail['definition'] != scenario['definition'] or detail['id'] != scenario['id']:
            raise ValueError('On-demand scenario identity differs from browser index')
        for orm, score in scenario['frameworks'].items():
            complete = detail['frameworks'][orm]
            if {k: v for k, v in complete.items() if k != 'raw'} != score:
                raise ValueError('On-demand details differ from summary statistics')
            if score['n'] != len(score['forkMeansUS']):
                raise ValueError('Independent sample count differs: ' + orm)
            means = {}
            observed_blocks = {}
            for raw in complete['raw']:
                if raw['status'] not in observed or raw['block'] not in range(1, 6):
                    raise ValueError('Invalid fork state or block')
                if raw['block'] in observed_blocks:
                    raise ValueError('Duplicate fork block reference')
                observed_blocks[raw['block']] = raw['status']
                observed[raw['status']] += 1
                for key, value in raw.items():
                    if key.endswith('Path') or key == 'path':
                        safe_file(root, value)
                status = json.loads(safe_file(root, raw['statusPath']).read_text())
                protocol.same(report,status)
                if status['status'] != raw['status'] or status['block'] != raw['block']:
                    raise ValueError('Raw state/block differs from its displayed reference')
                if status['sourceSha256'] != report['benchmarkSourceSha256'] or status['candidateGitSha'] != report['candidateGitSha']:
                    raise ValueError('Raw fork identity differs from report')
                if raw['status'] == 'PASS':
                    file = safe_file(root, raw['rawPath'])
                    if status['exitCode'] != 0 or digest(file) != status['rawSha256']:
                        raise ValueError('Measured JSON hash/exit code differs')
                    measured = json.loads(file.read_text())
                    expected_params = {k: str(v) for k, v in dict(scenario['definition']['parameters'], orm=orm).items()}
                    expected_mode = 'avgt' if scenario['definition']['kind'] == 'read' else 'ss'
                    if len(measured) != 1 or measured[0]['params'] != expected_params or measured[0]['mode'] != expected_mode or measured[0]['forks'] != 1:
                        raise ValueError('Measured workload parameters differ')
                    protocol.validate_jmh(report,measured[0],scenario['definition']['kind'])
                    metric = measured[0]['primaryMetric']
                    if metric['scoreUnit'] != 'us/op' or len(metric['rawData']) != 1:
                        raise ValueError('Measured units/fork count differ')
                    values = metric['rawData'][0]
                    if not values or any(not math.isfinite(v) or v <= 0 for v in values):
                        raise ValueError('Invalid measured latency')
                    if raw['block'] in means:
                        raise ValueError('Duplicate measured block')
                    means[raw['block']] = statistics.mean(values)
            expected_states = {str(block): observed_blocks.get(block, 'NOT_RUN') for block in range(1, 6)}
            if score['runStatesByBlock'] != expected_states:
                raise ValueError('Displayed block states differ from evidence')
            derived_state = 'COMPLETE' if set(means) == {1, 2, 3, 4, 5} else 'PARTIAL' if means else 'FAILED' if 'FAIL' in observed_blocks.values() else 'NOT_RUN'
            if score['status'] != derived_state:
                raise ValueError('Displayed scene state differs from measured coverage')
            recorded = {int(k): v for k, v in score['forkMeansUS'].items()}
            if set(means) != set(recorded) or any(not math.isclose(means[b], recorded[b], rel_tol=1e-12, abs_tol=1e-10) for b in means):
                raise ValueError('Displayed independent fork means differ from raw JSON')
            if means:
                if not math.isclose(score['mean'], statistics.mean(means.values()), rel_tol=1e-12, abs_tol=1e-10) or not math.isclose(score['median'], statistics.median(means.values()), rel_tol=1e-12, abs_tol=1e-10):
                    raise ValueError('Displayed mean/median differs from raw JSON')
                if len(means) > 1:
                    critical = {1: 12.706205, 2: 4.302653, 3: 3.182446, 4: 2.776445}[len(means) - 1]
                    error = critical * statistics.stdev(means.values()) / math.sqrt(len(means))
                    interval = [score['mean'] - error, score['mean'] + error]
                    if len(score['mean95CI']) != 2 or any(not math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-10) for a, b in zip(interval, score['mean95CI'])):
                        raise ValueError('Displayed confidence interval differs from raw fork means')
        if scenario.get('figure'):
            for extension in ['png', 'svg', 'pdf']:
                safe_file(root, scenario['figure'][extension])
    key_scenes = {('read', json.dumps(dict(projection='entity', tableRows=100000, resultRows=n, access='uniform'), sort_keys=True)) for n in [1, 100]}
    key_scenes.add(('write', json.dumps(dict(transactionRows=100), sort_keys=True)))
    expected_images = {s['figure']['absoluteUrls']['png'] for s in report['scenarios'] if (s['definition']['kind'], json.dumps(s['definition']['parameters'], sort_keys=True)) in key_scenes and s.get('figure')}
    actual_images = set(re.findall(r'!\[[^\]]*\]\(([^)]+)\)', root_markdown))
    if actual_images != expected_images:
        raise ValueError('Website key figures differ from the scenes registered before measurement')
    coverage = report['coverage']
    if coverage['plannedForkRuns'] != len(expected_scenes) * len(expected_frameworks) * 5:
        raise ValueError('Planned fork coverage differs from the registered design')
    if coverage['passedForkRuns'] != observed['PASS'] or coverage['failedForkRuns'] != observed['FAIL'] or coverage['notRunForkRuns'] != coverage['plannedForkRuns'] - sum(observed.values()):
        raise ValueError('Displayed run coverage differs from raw states')
    if (coverage['failedForkRuns'] or coverage['notRunForkRuns']) and not report.get('partialReason'):
        raise ValueError('Incomplete report lacks its stated limitation')
    archive = safe_file(root, 'runs/' + report['reportId'] + '/evidence.zip')
    checksum = archive.with_suffix('.zip.sha256')
    if checksum.read_text().split()[0] != digest(archive):
        raise ValueError('Portable archive checksum differs')
    with zipfile.ZipFile(archive) as package:
        if package.testzip() is not None:
            raise ValueError('Portable archive CRC differs')
        for name in package.namelist():
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts or '\\' in name:
                raise ValueError('Unsafe portable archive member')
        if set(package.namelist()) != set(manifest['files']) | {'publication-files.json'}:
            raise ValueError('Portable archive contains unreviewed or missing files')
        if package.read('publication-files.json') != (root / 'publication-files.json').read_bytes():
            raise ValueError('Portable archive manifest differs')
        for relative, expected in manifest['files'].items():
            if hashlib.sha256(package.read(relative)).hexdigest() != expected['sha256']:
                raise ValueError('Portable archive member differs: ' + relative)
    permitted = set(manifest['files']) | {'publication-files.json', str(archive.relative_to(root)), str(checksum.relative_to(root))}
    for path in root.rglob('*'):
        if path.is_symlink() or (path.is_file() and str(path.relative_to(root)) not in permitted):
            raise ValueError('Unreviewed file or symlink in publication')
    for expected in ['readme.md','data/report.json']:
        safe_file(root, expected)
    return report['reportId']


def validate_ci(root,aggregate,plan_path,expected_context,expected_controller,expected_protocol,expected_run,public_base):
    """Authorize automatic result refresh only from complete same-run audited formal evidence."""
    import ci_experiment as ci
    from secret_audit import verify_aggregate
    if not re.fullmatch('[0-9a-f]{40}',expected_controller or '') or not re.fullmatch('[0-9a-f]{64}',expected_protocol or '') or not re.fullmatch('[0-9a-f]{64}',expected_context or '') or not re.fullmatch('[1-9][0-9]*',str(expected_run)):
        raise ValueError('Automatic publication requires exact controller/protocol/context/run identities')
    plan=protocol.read_plan(plan_path,expected_context);protocol.verify_controller(plan);context=plan['executionContext']
    if context['controller']['gitSha']!=expected_controller or context['protocolSha256']!=expected_protocol or str(context['measurementRunId'])!=str(expected_run):raise ValueError('Publication target differs from this formal workflow run')
    manifest=json.loads((aggregate/'build-manifest.json').read_text())
    if manifest.get('executionClassification')!='FORMAL' or manifest.get('executionContext')!=context:raise ValueError('Publication aggregate is not the frozen formal execution')
    record=verify_aggregate(aggregate);protocol.same(manifest,record['identity'])
    summary=json.loads((aggregate/'analysis/summary.json').read_text());protocol.same(manifest,summary)
    coverage=summary['coverage'];expected_coverage=dict(plannedForkRuns=780,passedForkRuns=780,failedForkRuns=0,notRunForkRuns=0)
    if any(coverage.get(key)!=value for key,value in expected_coverage.items()):raise ValueError('Automatic publication requires all 780 formal fork runs to pass')
    if any(row.get('status')!='COMPLETE' or row.get('n')!=5 for case in summary['summaries'].values() for row in case.values()):raise ValueError('Automatic publication requires five independent blocks per adapter/case')
    ci_coverage=json.loads((aggregate/'ci-coverage.json').read_text())
    if ci_coverage['planned']!=780 or ci_coverage['received']!=780 or ci_coverage['notRun'] or ci_coverage['shardFailures']:raise ValueError('Incomplete shard coverage cannot refresh result')
    settings=protocol.protocol(context)
    if digest(aggregate/'measure/schedule.json')!=settings['caseScheduleSha256']:raise ValueError('Publication schedule differs from frozen runtime')
    expected={ci.cell_name(item):item for item in json.loads((aggregate/'measure/schedule.json').read_text())};seen=set()
    for path in (aggregate/'measure').glob('*.status.json'):
        status=json.loads(path.read_text());name=path.name.removesuffix('.status.json');protocol.same(manifest,status)
        if name in seen or name not in expected or status['status']!='PASS' or status['exitCode']!=0 or any(status[key]!=expected[name][key] for key in ['kind','params','block','group']):raise ValueError('Unplanned, failed or duplicate publication cell')
        seen.add(name)
    if len(expected)!=780 or seen!=set(expected):raise ValueError('Publication is missing expected formal cells')
    report_id=validate(root,public_base);prefix='runs/'+report_id+'/'
    report=json.loads((root/'data/report.json').read_text());protocol.same(manifest,report)
    if report['coverage']!=coverage or report['candidateGitSha']!=manifest['candidateGitSha'] or report['benchmarkSourceSha256']!=manifest['sourceSha256']:raise ValueError('Displayed report differs from canonical aggregate')
    required=['build-manifest.json','analysis/summary.json','audit-provenance.json','execution-context.json','execution-protocol.json','commands.jsonl','validation-gate.json']
    for relative in required:
        expected=digest(aggregate/relative) if relative=='audit-provenance.json' else record['files'][relative]
        if digest(safe_file(root,prefix+relative))!=expected:raise ValueError('Published evidence differs from audited aggregate: '+relative)
    figure_index=json.loads((aggregate/'analysis/figures.json').read_text())
    for scene in report['scenarios']:
        key=scene['key']
        if scene['definition']!=summary['caseDefinitions'][key] or scene['frameworks']!=summary['summaries'][key] or scene.get('comparisons',{})!=summary['comparisons'].get(key,{}):raise ValueError('Displayed scenario statistics differ from canonical analysis')
        detail=json.loads(safe_file(root,scene['details']).read_text())
        for score in detail['frameworks'].values():
            for raw in score['raw']:
                for name,relative in raw.items():
                    if name.endswith('Path') or name=='path':
                        if not relative.startswith(prefix):raise ValueError('Evidence reference escapes this immutable report run')
                        original=relative[len(prefix):]
                        if original not in record['files'] or digest(safe_file(root,relative))!=record['files'][original]:raise ValueError('Published raw reference is not covered by the aggregate receipt chain')
        if scene.get('figure'):
            for extension in ['png','svg','pdf']:
                if digest(safe_file(root,scene['figure'][extension]))!=digest(aggregate/'analysis'/figure_index[key][extension]):raise ValueError('Published figure differs from canonical analysis')
    protocol.verify_snapshot(aggregate/context['controller']['snapshotFile'],context)
    return report_id


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--expected-public-base')
    parser.add_argument('--aggregate',type=Path);parser.add_argument('--execution-plan',type=Path)
    parser.add_argument('--expected-context');parser.add_argument('--expected-controller');parser.add_argument('--expected-protocol');parser.add_argument('--expected-run')
    args = parser.parse_args()
    report_id=validate_ci(args.directory,args.aggregate,args.execution_plan,args.expected_context,args.expected_controller,args.expected_protocol,args.expected_run,args.expected_public_base) if args.aggregate else validate(args.directory,args.expected_public_base)
    print('PASS: Markdown contract, raw evidence, complete formal identity and portable archive; report '+report_id)
