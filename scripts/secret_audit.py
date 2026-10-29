"""Hash-bound receipts made while real CI database credentials still exist. No secret is exported."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import zipfile
import html
import sys
sys.dont_write_bytecode = True
import execution_protocol as protocol

RECEIPT = 'secret-audit.json'
IDENTITY = ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256', 'executionWorkflowRunId', 'executionWorkflowRunAttempt', 'executionStage']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def files(root, exclude):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink(): raise ValueError('Audit rejects symbolic links')
        if path.is_file() and path != root / exclude:
            result[str(path.relative_to(root))] = sha(path)
    return result


def scan(content, needles):
    if any(needle in content for needle in needles):
        raise ValueError('Credential found in evidence; content and credential withheld; upload blocked')
    stream = io.BytesIO(content)
    if zipfile.is_zipfile(stream):
        with zipfile.ZipFile(stream) as archive:
            for name in archive.namelist(): scan(archive.read(name), needles)
    else:
        stream.seek(0)
        try:
            archive = tarfile.open(fileobj=stream, mode='r:*')
        except tarfile.ReadError:
            return
        with archive:
            for member in archive.getmembers():
                if member.isfile(): scan(archive.extractfile(member).read(), needles)


def audit_directory(root, values):
    target = root / RECEIPT
    target.unlink(missing_ok=True)
    if not values or any(not isinstance(v, str) or not v for v in values):
        raise ValueError('Real generated credentials are required for the audit')
    manifest = json.loads((root / 'build-manifest.json').read_text())
    identity = {key: manifest[key] for key in IDENTITY}
    identity.update(protocol.identity(manifest))
    entries = files(root, RECEIPT)
    for relative in entries: scan((root / relative).read_bytes(), [v.encode() for v in values])
    cells = []
    for path in sorted(root.rglob('*.status.json')):
        status = json.loads(path.read_text())
        if any(status.get(k) != manifest[k] for k in ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256', 'executionWorkflowRunId', 'executionWorkflowRunAttempt']):
            raise ValueError('Cell identity differs from audited execution')
        protocol.same(manifest, status)
        cells.append({k: status[k] for k in ['kind', 'params', 'block', 'status']})
    receipt = dict(schemaVersion=1, status='PASS', identity=identity, files=entries, cells=cells,
                   executionGroup=manifest.get('executionGroup'), executionBlock=manifest.get('executionBlock'),
                   credentialKinds=['benchmarkPassword', 'rootPassword'], scope='Exact bytes and archive members before artifact upload')
    serialized = json.dumps(receipt, indent=2, sort_keys=True) + '\n'
    scan(serialized.encode(), [v.encode() for v in values])
    target.write_text(serialized)


def verify_receipt(root, manifest, execution_run=None):
    receipt = json.loads((root / RECEIPT).read_text())
    if receipt.get('schemaVersion') != 1 or receipt.get('status') != 'PASS' or receipt.get('credentialKinds') != ['benchmarkPassword', 'rootPassword']:
        raise ValueError('Missing or invalid real-credential scan receipt')
    for key in ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256']:
        if receipt['identity'][key] != manifest[key]: raise ValueError('Secret audit provenance mismatch: ' + key)
    protocol.same(manifest, receipt['identity'])
    if execution_run is not None and str(receipt['identity']['executionWorkflowRunId']) != str(execution_run):
        raise ValueError('Secret audit belongs to another execution run')
    expected_attempt = str(manifest.get('executionWorkflowRunAttempt', manifest.get('workflowRunAttempt', '')))
    if expected_attempt != '1' or str(receipt['identity'].get('executionWorkflowRunAttempt')) != expected_attempt:
        raise ValueError('Secret audit belongs to a different or unsupported execution attempt')
    if files(root, RECEIPT) != receipt['files']:
        raise ValueError('Evidence changed after real-secret scan; upload/export blocked')
    return receipt


def audited_failure(root, execution_run=None):
    """Only data covered by a passing real-credential receipt can become public diagnostics."""
    manifest = json.loads((root / 'build-manifest.json').read_text())
    verify_receipt(root, manifest, execution_run)
    status_file = root / 'validation/status.json'
    failures = {}
    if status_file.exists():
        statuses = json.loads(status_file.read_text())
        failures = {key: {field: str(value.get(field, ''))[:1500] for field in ['type', 'message']}
                    for key, value in statuses.items() if isinstance(value, dict) and value.get('status') == 'FAIL'}
    for status_file in sorted(root.rglob('*.status.json')):
        value = json.loads(status_file.read_text())
        if value.get('status') == 'FAIL': failures[status_file.name] = dict(type='JmhCellFailure', message=str(value.get('failure', 'JMH command failed'))[:1500])
    if not failures and not (root / 'validation/status.json').exists() and (root / 'validation.log').exists():
        lines = (root / 'validation.log').read_text().splitlines()
        failures['auditedExceptionLines'] = [line[:1500] for line in lines if any(tag in line for tag in ['Exception', 'Error', 'Caused by'])][-12:]
        if not failures['auditedExceptionLines']: failures = {}
    return dict(identity={key: manifest[key] for key in IDENTITY}, receiptSha256=sha(root / RECEIPT), failures=failures)


def emit_audited_failure(summary):
    if not summary['failures']: return
    text = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    annotation = text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::notice title=Audited preflight failure::' + annotation)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as handle:
            handle.write('<h3>Hash-verified, real-secret-audited failure</h3><pre>' + html.escape(text) + '</pre>\n')



def emit_audited_pilot(root, execution_run=None):
    """Expose actual trial evidence through the API only after byte-for-byte receipt verification."""
    review_file = root / 'pilot-review.json'
    if not review_file.exists(): return
    manifest = json.loads((root / 'build-manifest.json').read_text())
    verify_receipt(root, manifest, execution_run)
    summary = dict(identity={key: manifest[key] for key in IDENTITY}, receiptSha256=sha(root / RECEIPT),
                   reviewSha256=sha(review_file), review=json.loads(review_file.read_text()))
    text = json.dumps(summary, ensure_ascii=False, sort_keys=True)
    annotation = text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print('::notice title=Audited pilot diagnostics::' + annotation)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as handle:
            handle.write('<h3>Actual audited pilot diagnostics</h3><pre>' + html.escape(text) + '</pre>\n')


def finish_aggregate(root, manifest, receipts, bindings):
    record = dict(schemaVersion=1, identity=dict({k: manifest[k] for k in ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256', 'executionWorkflowRunId', 'executionWorkflowRunAttempt']}, **protocol.identity(manifest)),
                  receipts=receipts, bindings=bindings, files=files(root, 'audit-provenance.json'))
    save(root / 'audit-provenance.json', record)
    verify_aggregate(root)


def verify_aggregate(root):
    record = json.loads((root / 'audit-provenance.json').read_text())
    manifest = json.loads((root / 'build-manifest.json').read_text())
    if record.get('schemaVersion') != 1 or record['files'] != files(root, 'audit-provenance.json'):
        raise ValueError('CI aggregate changed after audited derivation')
    protocol.same(manifest, record['identity'])
    for key, value in record['identity'].items():
        if manifest[key] != value: raise ValueError('CI audit index identity mismatch')
    for identifier, receipt in record['receipts'].items():
        if receipt['status'] != 'PASS' or receipt['credentialKinds'] != ['benchmarkPassword', 'rootPassword']:
            raise ValueError('Aggregate contains an invalid scan receipt')
        protocol.same(manifest, receipt['identity'])
        for key in ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256']:
            if receipt['identity'][key] != manifest[key]: raise ValueError('Foreign receipt')
        if str(receipt['identity']['executionWorkflowRunId']) != str(manifest['executionWorkflowRunId']):
            raise ValueError('Receipt came from another measurement run')
        if str(receipt['identity'].get('executionWorkflowRunAttempt')) != '1' or str(manifest['executionWorkflowRunAttempt']) != '1':
            raise ValueError('Receipt belongs to another or unsupported measurement attempt')
    for relative, origin in record['bindings'].items():
        expected = record['receipts'][origin['receipt']]['files'][origin['file']]
        if record['files'].get(relative) != expected: raise ValueError('Copied evidence is not covered by a real-secret receipt')
    required = set()
    for relative in record['files']:
        if relative.startswith(('hosts/', 'validation/', 'preflight/')) or (relative.startswith('measure/') and relative != 'measure/schedule.json') or relative == 'validation-gate.json':
            required.add(relative)
    if not required.issubset(record['bindings']): raise ValueError('Unscanned CI evidence cannot be exported')
    # The concatenated command stream is derived only from already audited shard command files.
    command_sources = sorted(k for k in record['bindings'] if k.startswith('hosts/') and k.endswith('/commands.jsonl'))
    if (root / 'commands.jsonl').exists() and (root / 'commands.jsonl').read_bytes() != b''.join((root / k).read_bytes() for k in command_sources):
        raise ValueError('Aggregate commands do not match audited source streams')
    return record


def emit_audited_aggregate(root):
    """Publish compact per-workload statistics from the same verified website analysis."""
    record = verify_aggregate(root)
    coverage_file = root / 'ci-coverage.json'
    coverage = None
    if coverage_file.exists():
        full = json.loads(coverage_file.read_text())
        coverage = dict(planned=full['planned'], received=full['received'], notRun=len(full['notRun']),
                        shardFailures=len(full['shardFailures']), detailSha256=sha(coverage_file))
    common = dict(identity=record['identity'], auditProvenanceSha256=sha(root / 'audit-provenance.json'),
                  coverage=coverage, independentSampleUnit='JVM fork/block; iterations are averaged within fork')
    summary_file = root / 'analysis/summary.json'
    if not summary_file.exists():
        print('::notice title=Audited aggregate completeness::' + json.dumps(dict(common, numericResults=False), sort_keys=True))
        return
    summary = json.loads(summary_file.read_text())
    common.update(analysisSummarySha256=sha(summary_file), analysisCoverage=summary['coverage'])
    grouped = {}
    for item in json.loads((root / 'measure/schedule.json').read_text()):
        key = item['kind'] + ':' + json.dumps({k: v for k, v in item['params'].items() if k != 'orm'}, sort_keys=True)
        grouped.setdefault(item['group'], set()).add(key)
    statuses = {}
    for path in sorted((root / 'measure').glob('*.status.json')):
        status = json.loads(path.read_text())
        key = status['kind'] + ':' + json.dumps({k: v for k, v in status['params'].items() if k != 'orm'}, sort_keys=True)
        statuses[(key, status['params']['orm'], str(status['block']))] = status
    selected_fields = ['status', 'runStatesByBlock', 'forkMeansUS', 'operationUnit', 'rowsPerOperation', 'n', 'mean', 'median', 'sampleSD', 'mean95CI', 'mean95CIAssumption']
    for group, keys in sorted(grouped.items()):
        cases = {}
        for key in sorted(keys):
            orms = {}
            for orm, values in summary['summaries'][key].items():
                row = {field: values[field] for field in selected_fields if field in values}
                row['rawSha256ByBlock'] = {block: status['rawSha256'] for (case, name, block), status in statuses.items()
                                          if case == key and name == orm and 'rawSha256' in status}
                orms[orm] = row
            cases[key] = dict(definition=summary['caseDefinitions'][key], orms=orms, comparisons=summary['comparisons'][key])
        receipts, hosts = {}, {}
        for name, receipt in record['receipts'].items():
            if receipt.get('executionGroup') != group: continue
            receipts[name] = hashlib.sha256((json.dumps(receipt, indent=2, sort_keys=True) + '\n').encode()).hexdigest()
            host_file = root / 'hosts' / name / 'host.json'
            if host_file.exists():
                hosts[name] = dict(sha256=sha(host_file), metadata=json.loads(host_file.read_text()))
                for label in ['cpu', 'memory', 'idle']:
                    evidence = host_file.parent / ('host-' + label + '.log')
                    if evidence.exists():
                        text = evidence.read_text()
                        if label == 'cpu': text = '\n'.join(line for line in text.splitlines() if line.startswith(('Architecture:', 'CPU(s):', 'Model name:', 'Thread(s) per core:', 'Core(s) per socket:')))
                        hosts[name][label] = dict(sha256=sha(evidence), observed=text)

        text = json.dumps(dict(common, group=group, cases=cases, receiptSha256=receipts, hosts=hosts), sort_keys=True)
        annotation = text.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::notice title=Audited aggregate ' + group + '::' + annotation)
        if os.environ.get('GITHUB_STEP_SUMMARY'):
            with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as handle:
                handle.write('<h3>Audited aggregate ' + html.escape(group) + '</h3><pre>' + html.escape(text) + '</pre>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['audit', 'verify-aggregate'])
    parser.add_argument('directories', type=Path, nargs='+')
    args = parser.parse_args()
    if args.command == 'verify-aggregate':
        for root in args.directories: emit_audited_aggregate(root)
        return
    private = Path(os.environ['BENCH_DB_PASSWORD_FILE'])
    if private.stat().st_mode & 0o077: raise ValueError('Generated secret file must have mode600')
    if (private.parent / 'mysql.env').stat().st_mode & 0o077: raise ValueError('Generated server credentials must have mode600')
    values = dict(line.split('=', 1) for line in (private.parent / 'mysql.env').read_text().splitlines())
    benchmark = private.read_text()
    if values['MYSQL_PASSWORD'] != benchmark: raise ValueError('Generated credential sources disagree')
    selected = [root for root in args.directories if root.is_dir()]
    if not selected: raise ValueError('No evidence directories to audit')
    try:
        for root in selected: audit_directory(root, [benchmark, values['MYSQL_ROOT_PASSWORD']])
    except BaseException:
        for root in selected: (root / RECEIPT).unlink(missing_ok=True)
        raise
    print('Real-credential scan passed; hash-bound receipts written; secret values withheld')
    for root in selected:
        emit_audited_failure(audited_failure(root, os.environ.get('GITHUB_RUN_ID')))
        emit_audited_pilot(root, os.environ.get('GITHUB_RUN_ID'))


if __name__ == '__main__': main()
