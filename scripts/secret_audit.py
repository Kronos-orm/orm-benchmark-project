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

RECEIPT = 'secret-audit.json'
IDENTITY = ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256', 'executionWorkflowRunId', 'executionStage']


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
    entries = files(root, RECEIPT)
    for relative in entries: scan((root / relative).read_bytes(), [v.encode() for v in values])
    cells = []
    for path in sorted(root.rglob('*.status.json')):
        status = json.loads(path.read_text())
        if any(status.get(k) != manifest[k] for k in ['candidateGitSha', 'sourceSha256', 'bundleSha256']):
            raise ValueError('Cell identity differs from audited execution')
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
    if execution_run is not None and str(receipt['identity']['executionWorkflowRunId']) != str(execution_run):
        raise ValueError('Secret audit belongs to another execution run')
    if files(root, RECEIPT) != receipt['files']:
        raise ValueError('Evidence changed after real-secret scan; upload/export blocked')
    return receipt


def finish_aggregate(root, manifest, receipts, bindings):
    record = dict(schemaVersion=1, identity={k: manifest[k] for k in ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256', 'executionWorkflowRunId']},
                  receipts=receipts, bindings=bindings, files=files(root, 'audit-provenance.json'))
    save(root / 'audit-provenance.json', record)
    verify_aggregate(root)


def verify_aggregate(root):
    record = json.loads((root / 'audit-provenance.json').read_text())
    manifest = json.loads((root / 'build-manifest.json').read_text())
    if record.get('schemaVersion') != 1 or record['files'] != files(root, 'audit-provenance.json'):
        raise ValueError('CI aggregate changed after audited derivation')
    for key, value in record['identity'].items():
        if manifest[key] != value: raise ValueError('CI audit index identity mismatch')
    for identifier, receipt in record['receipts'].items():
        if receipt['status'] != 'PASS' or receipt['credentialKinds'] != ['benchmarkPassword', 'rootPassword']:
            raise ValueError('Aggregate contains an invalid scan receipt')
        for key in ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256']:
            if receipt['identity'][key] != manifest[key]: raise ValueError('Foreign receipt')
        if str(receipt['identity']['executionWorkflowRunId']) != str(manifest['executionWorkflowRunId']):
            raise ValueError('Receipt came from another measurement run')
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['audit', 'verify-aggregate'])
    parser.add_argument('directories', type=Path, nargs='+')
    args = parser.parse_args()
    if args.command == 'verify-aggregate':
        for root in args.directories: verify_aggregate(root)
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


if __name__ == '__main__': main()
