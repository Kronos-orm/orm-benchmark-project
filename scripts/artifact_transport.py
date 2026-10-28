"""Freeze GitHub artifact IDs/digests and verify exact ZIP bytes before extracting a prior pilot."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler
import zipfile

REPOSITORY = 'Kronos-orm/orm-benchmark-project'
API = 'https://api.github.com/repos/' + REPOSITORY


def require_single_attempt():
    attempt = os.environ.get('GITHUB_RUN_ATTEMPT')
    if attempt is not None and attempt != '1':
        raise ValueError('Rerun attempts are excluded from this experiment; dispatch a new run ID to preserve complete independent blocks')


def headers():
    return {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
            'Authorization': 'Bearer ' + os.environ['GH_TOKEN']}


def api_json(path):
    with urlopen(Request(API + path, headers=headers()), timeout=60) as response:
        return json.load(response)


def freeze_artifacts(run_id, benchmark_sha, fetch=api_json):
    if not re.fullmatch('[1-9][0-9]*', str(run_id)): raise ValueError('Invalid source run ID')
    run = fetch('/actions/runs/' + str(run_id))
    if run['conclusion'] != 'success' or run['event'] != 'workflow_dispatch' or run['head_sha'] != benchmark_sha or run['run_attempt'] != 1 or run['path'].split('@')[0] != '.github/workflows/experiment.yml':
        raise ValueError('Reuse requires a successful first-attempt pilot from this exact benchmark workflow/source')
    listing = fetch('/actions/runs/' + str(run_id) + '/artifacts?per_page=100')
    if listing['total_count'] > 100: raise ValueError('Unexpected artifact count for a pilot')
    selected = {}
    for name in ['runtime-bundle', 'preflight']:
        matches = [item for item in listing['artifacts'] if item['name'] == name]
        if len(matches) != 1: raise ValueError('Expected exactly one immutable artifact: ' + name)
        item = matches[0]
        if item['expired'] or str(item['workflow_run']['id']) != str(run_id) or item['workflow_run']['head_sha'] != benchmark_sha or not re.fullmatch('sha256:[0-9a-f]{64}', item.get('digest') or ''):
            raise ValueError('Artifact identity, expiry or SHA256 is invalid')
        selected[name] = {k: item[k] for k in ['id', 'name', 'digest', 'size_in_bytes']}
    return dict(repository=REPOSITORY, runId=str(run_id), runAttempt=1, benchmarkGitSha=benchmark_sha, artifacts=selected)


def extract_verified(archive, target, expected):
    if archive.stat().st_size != expected['size_in_bytes'] or hashlib.sha256(archive.read_bytes()).hexdigest() != expected['digest'].removeprefix('sha256:'):
        raise ValueError('Downloaded artifact ZIP differs from the frozen GitHub SHA256/size')
    if target.exists(): raise ValueError('Artifact destination must be new')
    with zipfile.ZipFile(archive) as source:
        names = set()
        for entry in source.infolist():
            path = Path(entry.filename)
            kind = stat.S_IFMT(entry.external_attr >> 16)
            if entry.filename in names or path.is_absolute() or '..' in path.parts or '\\' in entry.filename or kind not in [0, stat.S_IFREG, stat.S_IFDIR]:
                raise ValueError('Unsafe or duplicate ZIP entry')
            names.add(entry.filename)
        target.mkdir(parents=True)
        source.extractall(target)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, response_headers, newurl): return None


def download_one(item, target):
    with tempfile.TemporaryDirectory(prefix="benchmark-artifact-") as temporary:
        request = Request(API + '/actions/artifacts/' + str(item['id']) + '/zip', headers=headers())
        try:
            build_opener(NoRedirect()).open(request, timeout=60)
            raise ValueError('Expected GitHub signed artifact redirect')
        except HTTPError as response:
            if response.code != 302: raise ValueError('GitHub artifact download failed') from None
            location = response.headers['Location']
        parsed = urlsplit(location)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or not (host.endswith('.blob.core.windows.net') or host.endswith('.actions.githubusercontent.com')):
            raise ValueError('Unexpected artifact storage host')
        archive = Path(temporary) / 'artifact.zip'
        # The signed storage request deliberately receives no GitHub Authorization header.
        with urlopen(location, timeout=120) as source, archive.open('wb') as output:
            shutil.copyfileobj(source, output)
        extract_verified(archive, target, item)


def download_artifacts(plan, output):
    require_single_attempt()
    if plan['repository'] != REPOSITORY or plan['runAttempt'] != 1: raise ValueError('Foreign transport plan')
    for name, destination in [('runtime-bundle', 'runtime-bundle'), ('preflight', 'approved-preflight')]:
        item = plan['artifacts'][name]
        download_one(item, output / destination)


def smoke_current_run(run_id, output):
    require_single_attempt()
    if str(run_id) != os.environ['GITHUB_RUN_ID']: raise ValueError('Smoke only reads this current run metadata artifact')
    listing = api_json('/actions/runs/' + str(run_id) + '/artifacts?per_page=100')
    matches = [item for item in listing['artifacts'] if item['name'] == 'frozen-plan' and not item['expired']]
    if len(matches) != 1: raise ValueError('Expected this run unique frozen-plan artifact')
    item = matches[0]
    if str(item['workflow_run']['id']) != str(run_id) or item['size_in_bytes'] > 8192 or not re.fullmatch('sha256:[0-9a-f]{64}', item.get('digest') or ''):
        raise ValueError('Metadata smoke identity, size or SHA256 invalid')
    download_one(item, output)
    frozen = json.loads((output / 'frozen.json').read_text())
    if str(frozen['workflowRunId']) != str(run_id) or frozen['workflowRunAttempt'] != '1' or frozen['benchmarkGitSha'] != os.environ['GITHUB_SHA']:
        raise ValueError('Metadata payload differs from the expected current run/source')
    receipt = {key: item[key] for key in ['id', 'name', 'digest', 'size_in_bytes']}
    receipt.update(status='PASS', runId=str(run_id), runAttempt=1, purpose='READ_ONLY_SMALL_ARTIFACT_TRANSPORT_SMOKE')
    (output / 'transport-receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, sort_keys=True))


def diagnose_run(run_id, candidate_sha, output):
    """Read only prior evidence whose actual-secret scan receipt passes; never execute its code."""
    from secret_audit import verify_receipt, audited_failure, emit_audited_failure
    require_single_attempt()
    if not re.fullmatch('[1-9][0-9]*', str(run_id)) or not re.fullmatch('[0-9a-f]{40}', candidate_sha or ''):
        raise ValueError('Diagnostics require the exact source run and candidate SHA')
    run = api_json('/actions/runs/' + str(run_id))
    if run['event'] != 'workflow_dispatch' or run['run_attempt'] != 1 or run['path'].split('@')[0] != '.github/workflows/experiment.yml':
        raise ValueError('Foreign diagnostic source')
    listing = api_json('/actions/runs/' + str(run_id) + '/artifacts?per_page=100')
    matches = [item for item in listing['artifacts'] if item['name'] == 'preflight' and not item['expired']]
    if len(matches) != 1: raise ValueError('No unique audited preflight artifact')
    item = matches[0]
    if str(item['workflow_run']['id']) != str(run_id) or item['workflow_run']['head_sha'] != run['head_sha'] or item['size_in_bytes'] > 8 * 1024 * 1024 or not re.fullmatch('sha256:[0-9a-f]{64}', item.get('digest') or ''):
        raise ValueError('Diagnostic artifact provenance/digest/size invalid')
    download_one(item, output)
    gate = output / 'gate'; manifest = json.loads((gate / 'build-manifest.json').read_text())
    if manifest['candidateGitSha'] != candidate_sha or manifest['benchmarkGitSha'] != run['head_sha'] or manifest['mode'] != 'pilot':
        raise ValueError('Diagnostic candidate/benchmark source mismatch')
    verify_receipt(gate, manifest, str(run_id))
    audited = audited_failure(gate, str(run_id))
    summary = dict(sourceRunId=str(run_id), candidateGitSha=candidate_sha, benchmarkGitSha=manifest['benchmarkGitSha'],
                   artifactId=item['id'], artifactZipSha256=item['digest'], receiptSha256=audited['receiptSha256'], failures=audited['failures'])
    (output / 'diagnostic-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    emit_audited_failure(summary)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--plan', type=Path); mode.add_argument('--smoke-run-id'); mode.add_argument('--diagnose-run-id')
    parser.add_argument('--expected-candidate-sha')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.diagnose_run_id:
        diagnose_run(args.diagnose_run_id, args.expected_candidate_sha, args.out.resolve())
    elif args.smoke_run_id:
        smoke_current_run(args.smoke_run_id, args.out.resolve())
    else:
        download_artifacts(json.loads(args.plan.read_text())['reuseArtifacts'], args.out.resolve())
        print('Prior pilot artifacts downloaded by fixed IDs; ZIP SHA256 and safe extraction verified')
