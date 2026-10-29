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


def freeze_observation(run_id, candidate_sha, benchmark_sha, kind, fetch=api_json, controller_sha=None):
    """Freeze one original evidence artifact; observer source identity remains separate."""
    if not re.fullmatch('[1-9][0-9]*', str(run_id)) or any(not re.fullmatch('[0-9a-f]{40}', value or '') for value in [candidate_sha, benchmark_sha]):
        raise ValueError('Observation requires exact run, candidate and benchmark source identities')
    if kind not in ['pilot', 'aggregate']: raise ValueError('Unknown observation kind')
    run = fetch('/actions/runs/' + str(run_id))
    workflow_sha=controller_sha or benchmark_sha
    allowed=['.github/workflows/experiment.yml'] if kind=='pilot' else ['.github/workflows/experiment.yml','.github/workflows/measure-sealed.yml']
    if controller_sha and not re.fullmatch('[0-9a-f]{40}',controller_sha): raise ValueError('Expected exact controller source SHA')
    if run['event'] != 'workflow_dispatch' or run['run_attempt'] != 1 or run['head_sha'] != workflow_sha or run['path'].split('@')[0] not in allowed:
        raise ValueError('Foreign or rerun observation source')
    if run['path'].split('@')[0]=='.github/workflows/measure-sealed.yml' and not controller_sha: raise ValueError('Independent formal controller SHA is mandatory')
    if run['status'] != 'completed': raise ValueError('Wait for the original evidence to finish')
    listing = fetch('/actions/runs/' + str(run_id) + '/artifacts?per_page=100')
    name = 'preflight' if kind == 'pilot' else 'aggregate-reviewed-before-publication'
    matches = [item for item in listing['artifacts'] if item['name'] == name and not item['expired']]
    if len(matches) != 1: raise ValueError('No unique original observation artifact')
    item = matches[0]
    if str(item['workflow_run']['id']) != str(run_id) or item['workflow_run']['head_sha'] != workflow_sha or not re.fullmatch('sha256:[0-9a-f]{64}', item.get('digest') or '') or item['size_in_bytes'] > 256 * 1024 * 1024:
        raise ValueError('Original observation artifact identity/digest/size invalid')
    return dict(sourceRunId=str(run_id), sourceRunAttempt=1, candidateGitSha=candidate_sha, benchmarkGitSha=benchmark_sha,
                sourceConclusion=run['conclusion'], workflowSourceGitSha=workflow_sha, expectedControllerGitSha=controller_sha, kind=kind, artifact={key: item[key] for key in ['id', 'name', 'digest', 'size_in_bytes']})


def prepare_observation(plan, group_index, output):
    """Read original data only: never import or execute any code from a downloaded bundle."""
    from secret_audit import verify_receipt, verify_aggregate, emit_audited_aggregate
    require_single_attempt()
    if not 0 <= group_index < 8: raise ValueError('Expected one of eight observation groups')
    if output.exists(): raise ValueError('Preserve prior observer evidence')
    output.mkdir(parents=True)
    extracted = output / 'original'
    download_one(plan['artifact'], extracted)
    common = dict(original=plan, observerGitSha=os.environ.get('GITHUB_SHA'), observerRunId=os.environ.get('GITHUB_RUN_ID'))
    payloads = []
    if plan['kind'] == 'pilot':
        gate, pilot = extracted / 'gate', extracted / 'pilot'
        gate_manifest = json.loads((gate / 'build-manifest.json').read_text())
        manifest = json.loads((pilot / 'build-manifest.json').read_text())
        for directory, identity in [(gate, gate_manifest), (pilot, manifest)]:
            if any(str(identity[key]) != str(plan[value]) for key, value in [('candidateGitSha', 'candidateGitSha'), ('benchmarkGitSha', 'benchmarkGitSha'), ('executionWorkflowRunId', 'sourceRunId'), ('executionWorkflowRunAttempt', 'sourceRunAttempt')]):
                raise ValueError('Original pilot manifest differs from frozen observation plan')
            if identity['mode'] != 'pilot': raise ValueError('Expected real pilot evidence')
            verify_receipt(directory, identity, plan['sourceRunId'])
        if any(manifest[key] != gate_manifest[key] for key in ['sourceSha256', 'bundleSha256']): raise ValueError('Pilot and correctness bytes differ')
        review_file = pilot / 'pilot-review.json'; review = json.loads(review_file.read_text())
        if any(review[key] != manifest[key] for key in ['candidateGitSha', 'sourceSha256', 'bundleSha256']): raise ValueError('Review identity differs')
        if review['validationGateSha256'] != hashlib.sha256((gate / 'validation-gate.json').read_bytes()).hexdigest() or review['pilotCompletionSha256'] != hashlib.sha256((pilot / 'completion.json').read_bytes()).hexdigest():
            raise ValueError('Pilot review markers changed')
        groups = {}
        findings = []
        for row in review['findings']:
            status_file = pilot / 'pilot' / row['cell']; status = json.loads(status_file.read_text())
            group = status['kind'] + ':' + json.dumps({key: value for key, value in status['params'].items() if key != 'orm'}, sort_keys=True)
            enriched = dict(row)
            if row['status'] == 'PASS':
                raw = status_file.parent / Path(status['raw']).name
                if hashlib.sha256(raw.read_bytes()).hexdigest() != row['rawSha256']: raise ValueError('Pilot raw identity changed')
                metric = json.loads(raw.read_text())[0]['primaryMetric']
                enriched['measurementUS'] = metric['rawData'][0]
                log = status_file.with_name(status_file.name.replace('.status.json', '.log')).read_text()
                observed = []
                for match in re.finditer(r'# Warmup Iteration\s+(\d+):(.*?)(?=# Warmup Iteration\s+\d+:|\nIteration\s+\d+:|\Z)', log, re.S):
                    values = re.findall(r'([0-9.eE+-]+)\s+us/op', match.group(2))
                    if values: observed.append(dict(iteration=int(match.group(1)), us=float(values[-1])))
                enriched['warmupObservedFromLog'] = observed
            groups.setdefault(group, []).append(enriched); findings.append(row)
        if len(findings) != 48 or len(groups) != 8: raise ValueError('Expected complete original 48-cell/eight-scenario pilot')
        key = sorted(groups)[group_index]
        payloads.append(dict(common, group=key, manifestIdentity={key: manifest[key] for key in ['candidateGitSha', 'benchmarkGitSha', 'sourceSha256', 'bundleSha256', 'executionWorkflowRunId', 'executionWorkflowRunAttempt']},
                             reviewSha256=hashlib.sha256(review_file.read_bytes()).hexdigest(), receiptSha256=hashlib.sha256((pilot / 'secret-audit.json').read_bytes()).hexdigest(),
                             gateReceiptSha256=hashlib.sha256((gate / 'secret-audit.json').read_bytes()).hexdigest(), findings=groups[key], limitation=review['limitation']))
    else:
        aggregate = extracted / 'aggregate'; record = verify_aggregate(aggregate)
        if plan.get('expectedControllerGitSha') and record['identity'].get('controllerGitSha') != plan['expectedControllerGitSha']: raise ValueError('Aggregate belongs to another execution controller')
        if any(str(record['identity'][key]) != str(plan[value]) for key, value in [('candidateGitSha', 'candidateGitSha'), ('benchmarkGitSha', 'benchmarkGitSha'), ('executionWorkflowRunId', 'sourceRunId'), ('executionWorkflowRunAttempt', 'sourceRunAttempt')]):
            raise ValueError('Original aggregate identity differs from frozen observation plan')
        # Reuse the existing canonical summary renderer; capture its verified JSON instead of publishing oversized notices.
        import contextlib, io
        captured = io.StringIO()
        saved_summary = os.environ.pop('GITHUB_STEP_SUMMARY', None)
        try:
            with contextlib.redirect_stdout(captured): emit_audited_aggregate(aggregate)
        finally:
            if saved_summary is not None: os.environ['GITHUB_STEP_SUMMARY'] = saved_summary
        groups = [json.loads(line.split('::', 2)[2]) for line in captured.getvalue().splitlines() if line.startswith('::notice title=Audited aggregate ')]
        if len(groups) != 8: raise ValueError('Expected eight canonical workload groups')
        selected = sorted(groups, key=lambda value: value['group'])[group_index]
        if not selected.get('cases'):
            payloads.append(dict(common, summary=selected))
        else:
            for key, case in sorted(selected['cases'].items()):
                payloads.append(dict(common, summary=dict(selected, cases={key: case})))
        manifest=json.loads((aggregate/'build-manifest.json').read_text())
        if group_index==0 and manifest.get('executionContext'):
            payloads.append(dict(common, executionContext=manifest['executionContext'], executionContextSha256=manifest['executionContextSha256']))

    index = {}
    for slot, payload in enumerate(payloads):
        path = output / f'payload-{slot}.json'; path.write_text(json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n')
        index[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    counts=[((output/name).stat().st_size+2499)//2500 for name in index]
    if any(count>10 for count in counts) or sum(counts)>40: raise ValueError('Observer summary exceeds per-step/job notice budget')
    (output / 'index.json').write_text(json.dumps(index, sort_keys=True) + '\n')
    print('Verified original artifact, source/run/attempt and real-secret receipt chain; observation payloads ready')


def emit_observation(output, slot):
    """At most ten <3KiB structured-text notices per step, with end-to-end reassembly SHA256."""
    if (output / 'build-manifest.json').exists():
        from secret_audit import verify_receipt
        verify_receipt(output, json.loads((output / 'build-manifest.json').read_text()), os.environ.get('GITHUB_RUN_ID'))
    index = json.loads((output / 'index.json').read_text()); name = f'payload-{slot}.json'
    if name not in index: return
    data = (output / name).read_bytes()
    payload_sha = hashlib.sha256(data).hexdigest()
    if payload_sha != index[name]: raise ValueError('Observer payload changed before segment emission')
    text = data.decode('ascii'); chunks = [text[offset:offset+2500] for offset in range(0, len(text), 2500)]
    if len(chunks) > 10: raise ValueError('Split this workload further before emitting more than ten notices in one step')
    for part, chunk in enumerate(chunks):
        metadata = dict(payloadSha256=payload_sha, segmentIndex=part, segmentCount=len(chunks), slot=slot)
        message = json.dumps(metadata, sort_keys=True, separators=(',', ':')) + '\n' + chunk
        if len(message.encode()) > 3 * 1024: raise ValueError('Observer annotation exceeds 3KiB')
        escaped = message.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print('::notice title=Audited observation segment::' + escaped)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze-observation-run-id'); mode.add_argument('--observe-plan', type=Path); mode.add_argument('--emit-observation', type=Path);
    mode.add_argument('--plan', type=Path); mode.add_argument('--smoke-run-id'); mode.add_argument('--diagnose-run-id')
    parser.add_argument('--expected-candidate-sha'); parser.add_argument('--expected-benchmark-sha'); parser.add_argument('--expected-controller-sha')
    parser.add_argument('--observation-kind', choices=['pilot', 'aggregate']); parser.add_argument('--group-index', type=int); parser.add_argument('--slot', type=int)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.freeze_observation_run_id:
        args.out.write_text(json.dumps(freeze_observation(args.freeze_observation_run_id, args.expected_candidate_sha, args.expected_benchmark_sha, args.observation_kind, controller_sha=args.expected_controller_sha), sort_keys=True, separators=(',', ':')) + '\n')
    elif args.observe_plan:
        prepare_observation(json.loads(args.observe_plan.read_text()), args.group_index, args.out.resolve())
    elif args.emit_observation:
        emit_observation(args.emit_observation, args.slot)
    elif args.diagnose_run_id:
        diagnose_run(args.diagnose_run_id, args.expected_candidate_sha, args.out.resolve())
    elif args.smoke_run_id:
        smoke_current_run(args.smoke_run_id, args.out.resolve())
    else:
        download_artifacts(json.loads(args.plan.read_text())['reuseArtifacts'], args.out.resolve())
        print('Prior pilot artifacts downloaded by fixed IDs; ZIP SHA256 and safe extraction verified')
