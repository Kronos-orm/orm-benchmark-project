"""Lightweight transport/design tests; no database, JVM, network or performance samples."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import unittest
import secrets
import io
import tarfile
import zipfile
import copy
import os
import shutil
import subprocess
import contextlib
from unittest.mock import patch
from urllib.error import HTTPError

import ci_experiment as ci
import secret_audit as audit
import artifact_transport as transport
import calibration


class ContractTests(unittest.TestCase):
    def test_real_bundle_consumers_do_not_mutate_sealed_files_before_database_access(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); bundle = root / 'bundle'; bundle.mkdir()
            shutil.copytree(ci.ROOT / 'scripts', bundle / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            ci.write_json(bundle / 'build-manifest.json', dict(candidateGitSha='a' * 40))
            seal = ci.seal(bundle); before = audit.files(bundle, '')
            environment = dict(os.environ); environment.pop('PYTHONDONTWRITEBYTECODE', None)
            command = [sys.executable, str(bundle / 'scripts/ci_experiment.py')]
            verified = subprocess.run(command + ['verify', '--bundle', str(bundle), '--seal', seal], env=environment, capture_output=True, text=True)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            existing = root / 'existing-output'; existing.mkdir()
            prefix = subprocess.run(command + ['validate', '--bundle', str(bundle), '--seal', seal, '--out', str(existing)], env=environment, capture_output=True, text=True)
            self.assertNotEqual(prefix.returncode, 0)
            self.assertIn('FileExistsError', prefix.stderr)  # Fail deliberately before host/JVM/DB work.
            for entry in ['ci_mysql.py', 'export_publication.py', 'secret_audit.py', 'artifact_transport.py']:
                checked = subprocess.run([sys.executable, str(bundle / 'scripts' / entry), '--help'], env=environment, capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(audit.files(bundle, ''), before)

    def test_matrix_has_exactly_780_unique_registered_cells(self):
        items = ci.schedule()
        self.assertEqual(len(items), 780)
        self.assertEqual(len({ci.cell_name(item) for item in items}), 780)
        groups = {}
        for item in items:
            key = (item['block'], item['kind'], json.dumps({k: v for k, v in item['params'].items() if k != 'orm'}, sort_keys=True))
            groups.setdefault(key, []).append(item)
        self.assertEqual(len(groups), 130)
        for values in groups.values():
            self.assertEqual({v['params']['orm'] for v in values}, set(ci.ORMS))
            self.assertEqual(len({(v['group'], v['block']) for v in values}), 1)

    def test_shards_partition_the_plan_without_more_forks(self):
        planned = ci.schedule()
        shards = [[i for i in planned if i['group'] == g and i['block'] == b] for g in ci.GROUPS for b in range(1, 6)]
        self.assertEqual(len(shards), 40)
        self.assertEqual(sum(map(len, shards)), 780)
        self.assertTrue(all(len(items) in (6, 24) for items in shards))
        self.assertEqual(planned, ci.schedule())
        orders = {tuple(i['params']['orm'] for i in planned[index:index + 6]) for index in range(0, 780, 6)}
        self.assertGreater(len(orders), 10)

    def test_bundle_rejects_mutation_injection_missing_and_symlinks(self):
        for mutation in ['change', 'extra', 'missing', 'symlink']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                ci.write_json(root / 'build-manifest.json', {'candidateGitSha': 'a' * 40})
                payload = root / 'payload'; payload.write_text('immutable transport fixture')
                seal = ci.seal(root)
                self.assertEqual(ci.verify(root, seal)['candidateGitSha'], 'a' * 40)
                if mutation == 'change': payload.write_text('changed')
                elif mutation == 'extra': (root / 'unexpected').write_text('extra')
                elif mutation == 'missing': payload.unlink()
                else: (root / 'link').symlink_to(payload)
                with self.assertRaises(ValueError): ci.verify(root, seal)

    def test_empty_shards_preserve_all_missing_cells_without_numeric_analysis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); bundle = root / 'bundle'; bundle.mkdir()
            ci.write_json(bundle / 'build-manifest.json', {'candidateGitSha': 'a' * 40, 'benchmarkGitSha': 'a' * 40, 'sourceSha256': 'b' * 64})
            ci.write_json(bundle / 'expected-schedule.json', ci.schedule())
            seal = ci.seal(bundle)
            args = argparse.Namespace(bundle=bundle, seal=seal, shards=root / 'absent', out=root / 'aggregate', gate=None)
            with self.assertRaises(SystemExit): ci.aggregate(args)
            coverage = ci.read_json(args.out / 'ci-coverage.json')
            self.assertEqual(len(coverage['notRun']), 780)
            self.assertEqual(coverage['received'], 0)
            self.assertFalse((args.out / 'analysis/summary.json').exists())
            self.assertFalse(ci.read_json(args.out / 'analysis-unavailable.json')['numericResults'])

    def test_reviewed_bundle_cannot_be_reused_for_another_candidate_or_benchmark(self):
        for field in ['candidateGitSha', 'benchmarkGitSha']:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); bundle = root / 'bundle'; bundle.mkdir()
                manifest = dict(candidateGitSha='a' * 40, benchmarkGitSha='b' * 40, sourceSha256='c' * 64, runtimeSha256='d' * 64)
                ci.write_json(bundle / 'build-manifest.json', manifest)
                seal = ci.seal(bundle)
                frozen = dict(manifest); frozen[field] = 'e' * 40
                ci.write_json(root / 'frozen.json', frozen)
                args = argparse.Namespace(bundle=bundle, frozen=root / 'frozen.json', pilot_review=json.dumps(dict(manifest, bundleSha256=seal)))
                with self.assertRaisesRegex(ValueError, 'another source commit'): ci.reuse(args)

    def fixture(self, root):
        manifest = dict(candidateGitSha='a' * 40, benchmarkGitSha='b' * 40, sourceSha256='c' * 64,
                        bundleSha256='d' * 64, executionWorkflowRunId='123', executionWorkflowRunAttempt='1', executionStage='shard')
        ci.write_json(root / 'build-manifest.json', manifest)
        (root / 'evidence.log').write_text('Non-sensitive transport fixture')
        return manifest

    def test_real_nonce_scan_receipt_rejects_changes_and_foreign_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); manifest = self.fixture(root)
            values = [secrets.token_urlsafe(32), secrets.token_urlsafe(32)]
            audit.audit_directory(root, values)
            receipt = audit.verify_receipt(root, manifest, '123')
            self.assertEqual(receipt['files']['evidence.log'], ci.digest(root / 'evidence.log'))
            self.assertTrue(all(value not in (root / audit.RECEIPT).read_text() for value in values))
            with self.assertRaises(ValueError): audit.verify_receipt(root, manifest, 'another-run')
            with self.assertRaises(ValueError): audit.verify_receipt(root, dict(manifest, executionWorkflowRunAttempt='2'), '123')
            (root / 'evidence.log').write_text('changed after scan')
            with self.assertRaises(ValueError): audit.verify_receipt(root, manifest, '123')

    def test_secret_in_plain_zip_or_tar_blocks_receipt_without_disclosing_value(self):
        for kind in ['plain', 'zip', 'tar']:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); self.fixture(root)
                values = [secrets.token_urlsafe(32), secrets.token_urlsafe(32)]
                if kind == 'plain': (root / 'evidence.log').write_text(values[0])
                elif kind == 'zip':
                    with zipfile.ZipFile(root / 'nested.zip', 'w', zipfile.ZIP_DEFLATED) as archive: archive.writestr('inner.log', values[0])
                else:
                    with tarfile.open(root / 'nested.tar.gz', 'w:gz') as archive:
                        member = tarfile.TarInfo('inner.log'); member.size = len(values[0]); archive.addfile(member, io.BytesIO(values[0].encode()))
                with self.assertRaises(ValueError) as raised: audit.audit_directory(root, values)
                self.assertNotIn(values[0], str(raised.exception))
                self.assertFalse((root / audit.RECEIPT).exists())

    def test_ci_export_chain_requires_coverage_and_exact_audited_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); shard = root / 'source'; shard.mkdir(); manifest = self.fixture(shard)
            audit.audit_directory(shard, [secrets.token_urlsafe(32), secrets.token_urlsafe(32)])
            receipt = audit.verify_receipt(shard, manifest, '123')
            aggregate = root / 'aggregate'; aggregate.mkdir(); ci.write_json(aggregate / 'build-manifest.json', manifest)
            (aggregate / 'validation').mkdir(); (aggregate / 'validation/output.log').write_bytes((shard / 'evidence.log').read_bytes())
            with self.assertRaisesRegex(ValueError, 'Unscanned'): audit.finish_aggregate(aggregate, manifest, {'source': receipt}, {})
            binding = {'validation/output.log': dict(receipt='source', file='evidence.log')}
            audit.finish_aggregate(aggregate, manifest, {'source': receipt}, binding)
            self.assertTrue(audit.verify_aggregate(aggregate))
            (aggregate / 'validation/output.log').write_text('modified')
            with self.assertRaises(ValueError): audit.verify_aggregate(aggregate)

    def test_reruns_require_a_new_run_id(self):
        with patch.dict(os.environ, {'GITHUB_RUN_ATTEMPT': '1'}): transport.require_single_attempt()
        with patch.dict(os.environ, {'GITHUB_RUN_ATTEMPT': '2'}):
            with self.assertRaises(ValueError): transport.require_single_attempt()

    def test_prior_artifacts_pin_successful_source_attempt_ids_and_sha256(self):
        run = dict(conclusion='success', event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, path='.github/workflows/experiment.yml')
        listing = dict(total_count=2, artifacts=[dict(id=index, name=name, digest='sha256:' + 'b' * 64,
                       size_in_bytes=123, expired=False, workflow_run=dict(id=123, head_sha='a' * 40))
                       for index, name in enumerate(['runtime-bundle', 'preflight'], 10)])
        def fetch(path): return run if '/artifacts?' not in path else listing
        pinned = transport.freeze_artifacts('123', 'a' * 40, fetch)
        self.assertEqual(pinned['artifacts']['preflight']['id'], 11)
        for field, value in [('run_attempt', 2), ('conclusion', 'failure'), ('head_sha', 'c' * 40)]:
            changed = dict(run, **{field: value})
            with self.assertRaises(ValueError): transport.freeze_artifacts('123', 'a' * 40, lambda path: changed if '/artifacts?' not in path else listing)
        for field, value in [('expired', True), ('digest', None)]:
            changed = copy.deepcopy(listing); changed['artifacts'][0][field] = value
            with self.assertRaises(ValueError): transport.freeze_artifacts('123', 'a' * 40, lambda path: run if '/artifacts?' not in path else changed)

    def test_zip_digest_size_and_paths_are_verified_before_extraction(self):
        for member in ['safe/file.txt', '../escape.txt']:
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); archive = root / 'artifact.zip'
                with zipfile.ZipFile(archive, 'w') as output: output.writestr(member, 'Transport fixture, no performance values')
                expected = dict(digest='sha256:' + ci.digest(archive), size_in_bytes=archive.stat().st_size)
                if member.startswith('..'):
                    with self.assertRaises(ValueError): transport.extract_verified(archive, root / 'unsafe', expected)
                else:
                    transport.extract_verified(archive, root / 'safe', expected)
                    self.assertTrue((root / 'safe/safe/file.txt').exists())
                with self.assertRaises(ValueError): transport.extract_verified(archive, root / 'bad-hash', dict(expected, digest='sha256:' + '0' * 64))
                with self.assertRaises(ValueError): transport.extract_verified(archive, root / 'bad-size', dict(expected, size_in_bytes=1))

    def test_storage_redirect_does_not_receive_github_authorization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); archive = root / 'artifact.zip'
            with zipfile.ZipFile(archive, 'w') as output: output.writestr('payload.txt', 'Metadata transport fixture')
            item = dict(id=123, digest='sha256:' + ci.digest(archive), size_in_bytes=archive.stat().st_size)
            location = 'https://metadata.blob.core.windows.net/artifact.zip'
            with patch.dict(os.environ, {'GH_TOKEN': secrets.token_urlsafe(32)}), patch('artifact_transport.build_opener') as opener, patch('artifact_transport.urlopen', return_value=io.BytesIO(archive.read_bytes())) as storage:
                opener.return_value.open.side_effect = HTTPError('https://api.github.com/fixture', 302, 'redirect', {'Location': location}, None)
                transport.download_one(item, root / 'download')
                self.assertEqual(storage.call_args.args, (location,))
                self.assertNotIn('headers', storage.call_args.kwargs)
                self.assertTrue((root / 'download/payload.txt').exists())

    def test_diagnostics_emit_only_after_real_receipt_verification(self):
        for tamper in [False, True]:
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); source = root / 'source'; gate = source / 'gate'; gate.mkdir(parents=True)
                manifest = self.fixture(gate); manifest['mode'] = 'pilot'; ci.write_json(gate / 'build-manifest.json', manifest)
                (gate / 'validation').mkdir()
                ci.write_json(gate / 'validation/status.json', {'Jdbc': dict(status='FAIL', type='FixtureException', message='Audited diagnostic fixture')})
                audit.audit_directory(gate, [secrets.token_urlsafe(32), secrets.token_urlsafe(32)])
                if tamper: (gate / 'validation/status.json').write_text('unscanned change')
                run = dict(event='workflow_dispatch', run_attempt=1, path='.github/workflows/experiment.yml', head_sha=manifest['benchmarkGitSha'])
                listing = dict(artifacts=[dict(id=321, name='preflight', digest='sha256:' + 'e' * 64, size_in_bytes=1024, expired=False,
                                             workflow_run=dict(id=123, head_sha=manifest['benchmarkGitSha']))])
                printed = io.StringIO()
                with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(root / 'test-summary.html')}), patch('artifact_transport.api_json', side_effect=lambda path: listing if '/artifacts?' in path else run), patch('artifact_transport.download_one', side_effect=lambda item, target: shutil.copytree(source, target)), contextlib.redirect_stdout(printed):
                    if tamper:
                        with self.assertRaises(ValueError): transport.diagnose_run('123', manifest['candidateGitSha'], root / 'output')
                    else: transport.diagnose_run('123', manifest['candidateGitSha'], root / 'output')
                if tamper: self.assertEqual(printed.getvalue(), '')
                else: self.assertIn('Audited diagnostic fixture', printed.getvalue())


    def test_pilot_diagnostics_require_unchanged_real_audited_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'evidence'; root.mkdir(); self.fixture(root)
            finding = dict(cell='read-b1-fixture.status.json', status='PASS', meanUS=12.5,
                           sampleCV=0.02, warmupUS=[20.0, 13.0], rawSha256='f' * 64)
            ci.write_json(root / 'pilot-review.json', dict(findings=[finding], limitation='Short trial evidence'))
            values = [secrets.token_urlsafe(32), secrets.token_urlsafe(32)]
            audit.audit_directory(root, values)
            printed = io.StringIO()
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(root.parent / (root.name + '-summary.html'))}), contextlib.redirect_stdout(printed):
                audit.emit_audited_pilot(root, '123')
            summary = json.loads(printed.getvalue().split('::', 2)[2])
            self.assertEqual(summary['review']['findings'], [finding])
            self.assertEqual(summary['reviewSha256'], ci.digest(root / 'pilot-review.json'))
            self.assertTrue(all(value not in printed.getvalue() for value in values))
            (root / 'pilot-review.json').write_text('unscanned review')
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed), self.assertRaises(ValueError):
                audit.emit_audited_pilot(root, '123')
            self.assertEqual(printed.getvalue(), '')



    def test_aggregate_notices_share_verified_website_analysis_and_reject_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); shard = root / 'shard'; shard.mkdir()
            manifest = self.fixture(shard); manifest['executionGroup'] = 'entity-1000'; manifest['executionBlock'] = 1
            ci.write_json(shard / 'build-manifest.json', manifest)
            item = next(item for item in ci.schedule() if item['group'] == 'entity-1000')
            key = item['kind'] + ':' + json.dumps({k: v for k, v in item['params'].items() if k != 'orm'}, sort_keys=True)
            (shard / 'measure').mkdir()
            status = dict(manifest, **item, status='PASS', rawSha256='f' * 64)
            ci.write_json(shard / 'measure/fixture.status.json', status)
            audit.audit_directory(shard, [secrets.token_urlsafe(32), secrets.token_urlsafe(32)])
            receipt = audit.verify_receipt(shard, manifest, '123')
            aggregate = root / 'aggregate'; aggregate.mkdir(); (aggregate / 'measure').mkdir(); (aggregate / 'analysis').mkdir()
            ci.write_json(aggregate / 'build-manifest.json', manifest)
            ci.write_json(aggregate / 'measure/schedule.json', [item])
            shutil.copyfile(shard / 'measure/fixture.status.json', aggregate / 'measure/fixture.status.json')
            # Contract-only fixture: the renderer must retain the exact source analysis, never compute a second ranking.
            row = dict(status='PARTIAL', forkMeansUS={'1': 12.5}, n=1, mean=12.5, operationUnit='query')
            summary = dict(coverage=dict(plannedForkRuns=780, passedForkRuns=1), summaries={key: {item['params']['orm']: row}},
                           caseDefinitions={key: dict(kind='read')}, comparisons={key: {}})
            ci.write_json(aggregate / 'analysis/summary.json', summary)
            binding = {'measure/fixture.status.json': dict(receipt='shard-entity-1000-1', file='measure/fixture.status.json')}
            audit.finish_aggregate(aggregate, manifest, {'shard-entity-1000-1': receipt}, binding)
            printed = io.StringIO()
            with patch.dict(os.environ, {'GITHUB_STEP_SUMMARY': str(root / 'summary.html')}), contextlib.redirect_stdout(printed):
                audit.emit_audited_aggregate(aggregate)
            notice = json.loads(printed.getvalue().split('::', 2)[2])
            actual = notice['cases'][key]['orms'][item['params']['orm']]
            self.assertEqual(actual['forkMeansUS'], row['forkMeansUS'])
            self.assertEqual(actual['rawSha256ByBlock'], {str(item['block']): 'f' * 64})
            self.assertEqual(notice['analysisSummarySha256'], ci.digest(aggregate / 'analysis/summary.json'))
            self.assertEqual(notice['receiptSha256']['shard-entity-1000-1'], ci.digest(shard / audit.RECEIPT))
            (aggregate / 'analysis/summary.json').write_text('unverified analysis')
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed), self.assertRaises(ValueError): audit.emit_audited_aggregate(aggregate)
            self.assertEqual(printed.getvalue(), '')


    def test_observer_segments_reassemble_exact_bytes_below_api_limits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); payload = json.dumps(dict(fixture='percent% and unicode\u6d4b\u8bd5' * 400), ensure_ascii=True).encode() + b'\n'
            (root / 'payload-0.json').write_bytes(payload)
            ci.write_json(root / 'index.json', {'payload-0.json': ci.digest(root / 'payload-0.json')})
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed): transport.emit_observation(root, 0)
            parts = []
            for line in printed.getvalue().splitlines():
                message = line.split('::', 2)[2].replace('%0A', '\n').replace('%0D', '\r').replace('%25', '%')
                self.assertLessEqual(len(message.encode()), 3072)
                header, chunk = message.split('\n', 1); parts.append((json.loads(header), chunk))
            self.assertLessEqual(len(parts), 10)
            rebuilt = ''.join(chunk for metadata, chunk in sorted(parts, key=lambda value: value[0]['segmentIndex'])).encode()
            self.assertEqual(rebuilt, payload)
            self.assertEqual(parts[0][0]['payloadSha256'], ci.digest(root / 'payload-0.json'))
            (root / 'payload-0.json').write_text('tampered')
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed), self.assertRaises(ValueError): transport.emit_observation(root, 0)
            self.assertEqual(printed.getvalue(), '')

    def test_observer_freezes_exact_original_source_artifact_and_attempt(self):
        run = dict(event='workflow_dispatch', run_attempt=1, head_sha='b' * 40, path='.github/workflows/experiment.yml', status='completed', conclusion='success')
        artifact = dict(id=1234, name='preflight', digest='sha256:' + 'c' * 64, size_in_bytes=100, expired=False, workflow_run=dict(id=123, head_sha='b' * 40))
        def fetch(path): return dict(artifacts=[artifact]) if '/artifacts?' in path else run
        plan = transport.freeze_observation('123', 'a' * 40, 'b' * 40, 'pilot', fetch)
        self.assertEqual(plan['artifact']['id'], 1234)
        for field, value in [('run_attempt', 2), ('head_sha', 'd' * 40), ('status', 'in_progress')]:
            original = run[field]; run[field] = value
            with self.assertRaises(ValueError): transport.freeze_observation('123', 'a' * 40, 'b' * 40, 'pilot', fetch)
            run[field] = original

    def test_observer_reads_ordered_raw_and_multiline_warmup_from_original_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); original = root / 'original'; gate = original / 'gate'; pilot = original / 'pilot'
            gate.mkdir(parents=True); pilot.mkdir(); (pilot / 'pilot').mkdir()
            manifest = self.fixture(gate); manifest['mode'] = 'pilot'
            ci.write_json(gate / 'build-manifest.json', manifest); ci.write_json(pilot / 'build-manifest.json', manifest)
            ci.write_json(gate / 'validation-gate.json', dict(status='PASS'))
            ci.write_json(pilot / 'completion.json', dict(status='PASS', planned=48))
            findings = []
            for kind, parameters in ci.cases('pilot'):
                for orm in ci.ORMS:
                    name = kind + '-' + orm + '-' + str(len(findings)); folder = pilot / 'pilot'
                    raw = folder / (name + '.json'); ci.write_json(raw, [dict(primaryMetric=dict(rawData=[[3.0, 2.0, 1.0]]))])
                    status = dict(manifest, kind=kind, params=dict(parameters, orm=orm), block=1, status='PASS', raw=str(raw), rawSha256=ci.digest(raw))
                    ci.write_json(folder / (name + '.status.json'), status)
                    count = 2 if kind == 'read' else 5
                    log = '# Warmup Iteration 1: initialization output\n10.0 us/op\n' + ''.join(f'# Warmup Iteration {i}: {10.0/i} us/op\n' for i in range(2, count+1)) + 'Iteration 1: 3.0 us/op\n'
                    (folder / (name + '.log')).write_text(log)
                    findings.append(dict(cell=name + '.status.json', status='PASS', rawSha256=ci.digest(raw)))
            review = dict(candidateGitSha=manifest['candidateGitSha'], sourceSha256=manifest['sourceSha256'], bundleSha256=manifest['bundleSha256'],
                          validationGateSha256=ci.digest(gate / 'validation-gate.json'), pilotCompletionSha256=ci.digest(pilot / 'completion.json'), findings=findings, limitation='Contract fixture')
            ci.write_json(pilot / 'pilot-review.json', review)
            for folder in [gate, pilot]: audit.audit_directory(folder, [secrets.token_urlsafe(32), secrets.token_urlsafe(32)])
            plan = dict(kind='pilot', sourceRunId='123', sourceRunAttempt=1, candidateGitSha=manifest['candidateGitSha'], benchmarkGitSha=manifest['benchmarkGitSha'], artifact=dict(id=10))
            with patch('artifact_transport.download_one', side_effect=lambda item, target: shutil.copytree(original, target)):
                transport.prepare_observation(plan, 0, root / 'observed')
            result = json.loads((root / 'observed/payload-0.json').read_text())
            self.assertEqual(len(result['findings']), 6)
            self.assertEqual(result['findings'][0]['measurementUS'], [3.0, 2.0, 1.0])
            self.assertEqual(result['findings'][0]['warmupObservedFromLog'], [dict(iteration=1, us=10.0), dict(iteration=2, us=5.0)])
            self.assertEqual(result['reviewSha256'], ci.digest(pilot / 'pilot-review.json'))


    def test_calibration_preserves_eight_complete_six_adapter_scenarios(self):
        planned = [row for group in range(8) for row in calibration.scenario(group)]
        self.assertEqual(len(planned), 48)
        self.assertEqual(len({(row['kind'], json.dumps(row['params'], sort_keys=True)) for row in planned}), 48)
        for group in range(8):
            rows = calibration.scenario(group)
            self.assertEqual({row['params']['orm'] for row in rows}, set(ci.ORMS))
            self.assertEqual(len({json.dumps({k:v for k,v in row['params'].items() if k!='orm'}, sort_keys=True) for row in rows}), 1)

    def test_calibration_reports_ordered_trends_and_all_multiline_warmups(self):
        values = [20., 18., 16., 14., 12., 10., 8., 6., 4., 2.]
        actual = calibration.trends(values)
        self.assertGreater(actual['firstHalfOverSecondHalf'], 1)
        self.assertLess(actual['secondHalfNormalizedSlopePerIteration'], 0)
        self.assertEqual(actual['lastOverFirst'], .1)
        log = '# Warmup Iteration 1: initialization\n99.0 us/op\n# Warmup Iteration 2: 55.0 us/op\nIteration 1: 44.0 us/op\n'
        self.assertEqual(calibration.warmups(log), [dict(iteration=1,us=99.),dict(iteration=2,us=55.)])

    def test_calibration_controller_records_complete_raw_audit_and_bounded_payloads_without_database(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); bundle=root/'bundle';bundle.mkdir();gate=root/'gate';gate.mkdir()
            manifest=self.fixture(bundle);manifest.update(mode='pilot',workflowRunId='123',runtimeClasspathRelative=['runtime'])
            gate_manifest=dict(manifest,executionWorkflowRunId='999',executionWorkflowRunAttempt='1',executionStage='validate')
            ci.write_json(gate/'build-manifest.json',gate_manifest)
            ci.write_json(gate/'validation-gate.json',dict(status='PASS',bundleSha256=manifest['bundleSha256'],environment=dict(fixture='environment')))
            calls=[]
            def fake_run(argv, log, directory):
                calls.append([str(value) for value in argv])
                if 'com.kotlinorm.benchmark.InspectEnvironment' in argv:
                    ci.write_json(Path(argv[-1]),dict(fixture='environment'));log.write_text('Contract environment observation');return 0
                target=Path(argv[argv.index('-rff')+1]);params=dict(str(argv[i+1]).split('=',1) for i,value in enumerate(argv[:-1]) if value=='-p')
                values=[100.0-i for i in range(10)]
                ci.write_json(target,[dict(params=params,mode='avgt',primaryMetric=dict(scoreUnit='us/op',rawData=[values]))])
                log.write_text(''.join(f'# Warmup Iteration {i}: {200.0/i} us/op\n' for i in range(1,6))+'Iteration 1: 100.0 us/op\n')
                return 0
            environment=dict(GITHUB_ACTIONS='true',GITHUB_RUN_ID='999',GITHUB_RUN_ATTEMPT='1',GITHUB_SHA='e'*40,JAVA_HOME=str(root/'jdk'))
            output=root/'calibration'
            with patch.dict(os.environ,environment),patch('ci_experiment.verify',return_value=manifest),patch('ci_experiment.run',side_effect=fake_run),patch('ci_experiment.host_snapshot'):
                calibration.execute(bundle,manifest['bundleSha256'],gate,0,output)
                for directory in [gate,output]:audit.audit_directory(directory,[secrets.token_urlsafe(32),secrets.token_urlsafe(32)])
                calibration.summarize(output,gate,root/'observations')
                audit.audit_directory(root/'observations',[secrets.token_urlsafe(32),secrets.token_urlsafe(32)])
            self.assertEqual(len(calls),7)
            self.assertTrue(all(command[command.index('-f')+1]=='1' for command in calls[1:]))
            review=ci.read_json(output/'calibration-review.json');self.assertEqual(len(review['findings']),6)
            self.assertTrue(all(row['status']=='PASS' and len(row['measurementUS'])==10 for row in review['findings']))
            payload=ci.read_json(root/'observations/payload-0.json')
            self.assertEqual(payload['classification'],'CALIBRATION_ONLY_NOT_FORMAL')
            self.assertEqual(payload['identity']['benchmarkGitSha'],manifest['benchmarkGitSha'])
            self.assertEqual(payload['controllerGitSha'],'e'*40)
            self.assertEqual(payload['receiptSha256'],ci.digest(output/audit.RECEIPT))
            printed=io.StringIO()
            with patch.dict(os.environ,environment),contextlib.redirect_stdout(printed):transport.emit_observation(root/'observations',0)
            self.assertTrue(printed.getvalue().startswith('::notice title=Audited observation segment::'))
            review['findings'][0]['warmupObservedFromLog']=[dict(iteration=i,us=1000.0/i) for i in range(1,2001)]
            ci.write_json(output/'calibration-review.json',review)
            audit.audit_directory(output,[secrets.token_urlsafe(32),secrets.token_urlsafe(32)])
            with patch.dict(os.environ,environment):calibration.summarize(output,gate,root/'large-observations')
            compressed=ci.read_json(root/'large-observations/payload-0.json')['finding']
            self.assertNotIn('warmupObservedFromLog',compressed)
            self.assertEqual(compressed['warmupCount'],2000)
            self.assertEqual(len(compressed['warmupFirst3']),3)
            self.assertEqual(len(compressed['warmupLast30']),30)
            self.assertEqual(compressed['logSha256'],review['findings'][0]['logSha256'])



    def test_write_warm2000_is_uniform_and_only_two_complete_scenarios(self):
        planned=[row for group in range(2) for row in calibration.scenario(group,'write-warm2000')]
        self.assertEqual(len(planned),12)
        for group,count in [(0,1),(1,100)]:
            rows=calibration.scenario(group,'write-warm2000')
            self.assertEqual({row['params']['orm'] for row in rows},set(ci.ORMS))
            self.assertTrue(all(row['kind']=='write' and row['params']['transactionRows']==count and row['group']==str(group) for row in rows))
        args=calibration.timing('write','write-warm2000')
        self.assertEqual(args[args.index('-wi')+1],'2000')
        self.assertEqual(args[args.index('-i')+1],'30')
        with self.assertRaises(ValueError):calibration.scenario(2,'write-warm2000')
        with self.assertRaises(ValueError):calibration.timing('read','write-warm2000')

    def formal_fixture(self,root,seal=None):
        import execution_protocol as execution
        settings=json.loads((ci.ROOT/'config/formal.json').read_text())
        if seal:settings['runtime']['bundleSha256']=seal
        archive=root/'controller-source-fixture.tar.gz'
        text=json.dumps(settings,indent=2,sort_keys=True)+'\n';protocol_path='config/formal.json'
        protocol_sha=__import__('hashlib').sha256(text.encode()).hexdigest();files={protocol_path:protocol_sha}
        with tarfile.open(archive,'w:gz') as stream:
            member=tarfile.TarInfo(protocol_path);member.size=len(text.encode());stream.addfile(member,io.BytesIO(text.encode()))
        context=dict(schemaVersion=1,runtime=dict(settings['runtime'],runtimeSha256='f'*64),controller=dict(gitSha='e'*40,sourceFiles=files,sourceTreeSha256=execution.canonical(files),snapshotFile=archive.name,snapshotSha256=execution.sha(archive)),protocolJSON=text,protocolFile=protocol_path,protocolSha256=protocol_sha,measurementRunId=os.environ.get('GITHUB_RUN_ID','123'),measurementRunAttempt='1')
        plan=dict(candidateGitSha=settings['runtime']['candidateGitSha'],benchmarkGitSha=settings['runtime']['benchmarkGitSha'],executionContext=context,executionContextSha256=execution.canonical(context))
        runtime=dict(candidateGitSha=settings['runtime']['candidateGitSha'],benchmarkGitSha=settings['runtime']['benchmarkGitSha'],sourceSha256=settings['runtime']['sourceSha256'],runtimeSha256='f'*64,workflowRunId=settings['runtime']['producerRunId'],workflowRunAttempt='1',runtimeClasspathRelative=['runtime'],runtimeArtifacts={},executionEnvironment='Unit fixture runner VM')
        manifest=execution.bind(runtime,plan,settings['runtime']['bundleSha256']);manifest['executionStage']='shard'
        return runtime,manifest,plan

    def test_formal_context_rejects_controller_protocol_runtime_and_legacy_mismatch(self):
        import execution_protocol as execution
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime,manifest,plan=self.formal_fixture(root)
            self.assertEqual(manifest['benchmarkGitSha'],'1497bd730b6d598879fb09774fe6d48e4c9e2f03')
            self.assertNotEqual(manifest['controllerGitSha'],manifest['benchmarkGitSha'])
            execution.same(manifest,execution.identity(manifest))
            with self.assertRaises(ValueError):execution.same(manifest,runtime)
            for key,value in [('controllerGitSha','d'*40),('protocolSha256','d'*64),('candidateGitSha','d'*40),('sourceSha256','d'*64)]:
                changed=dict(manifest,**{key:value})
                with self.assertRaises(ValueError):execution.identity(changed)
            changed=copy.deepcopy(plan);changed['executionContext']['controller']['sourceTreeSha256']='d'*64
            with self.assertRaises(ValueError):execution.protocol(changed['executionContext'])
            changed=copy.deepcopy(plan);changed['executionContext']['runtime']['candidateGitSha']='d'*40
            with self.assertRaises(ValueError):execution.protocol(changed['executionContext'])

    def test_formal_receipt_requires_context_and_rejects_old_receipts(self):
        import execution_protocol as execution
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime,manifest,plan=self.formal_fixture(root)
            ci.write_json(root/'build-manifest.json',manifest)
            values=[secrets.token_urlsafe(32),secrets.token_urlsafe(32)]
            audit.audit_directory(root,values)
            receipt=audit.verify_receipt(root,manifest,manifest['executionWorkflowRunId'])
            self.assertEqual(receipt['identity']['protocolSha256'],manifest['protocolSha256'])
            ci.write_json(root/'build-manifest.json',dict(runtime,executionWorkflowRunId=manifest['executionWorkflowRunId'],executionWorkflowRunAttempt='1',executionStage='shard',bundleSha256=manifest['bundleSha256']))
            audit.audit_directory(root,values)
            with self.assertRaises(ValueError):audit.verify_receipt(root,manifest,manifest['executionWorkflowRunId'])

    def test_formal_jmh_uses_actual_2000_300_and_fork1_metadata(self):
        import execution_protocol as execution
        with tempfile.TemporaryDirectory() as temporary:
            _,manifest,_=self.formal_fixture(Path(temporary))
            data=dict(forks=1,warmupIterations=2000,measurementIterations=300,warmupBatchSize=1,measurementBatchSize=1,primaryMetric=dict(rawData=[[2.]*300]))
            execution.validate_jmh(manifest,data,'write')
            for key,value in [('forks',5),('warmupIterations',10),('measurementIterations',30),('warmupBatchSize',100)]:
                with self.assertRaises(ValueError):execution.validate_jmh(manifest,dict(data,**{key:value}),'write')
            read=dict(forks=1,warmupIterations=5,measurementIterations=10,warmupTime='2 s',measurementTime='2 s',primaryMetric=dict(rawData=[[2.]*10]))
            execution.validate_jmh(manifest,read,'read')
            with self.assertRaises(ValueError):execution.validate_jmh(manifest,dict(read,warmupTime='1 s'),'read')

    def test_formal_aggregate_calls_controller_analyzer_and_retains_all_300_with_n5(self):
        import execution_protocol as execution
        import analyze_results as analysis
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);bundle=root/'bundle';bundle.mkdir();shards=root/'shards';shards.mkdir()
            runtime,_,_=self.formal_fixture(root)
            ci.write_json(bundle/'build-manifest.json',runtime);ci.write_json(bundle/'expected-schedule.json',ci.schedule())
            with tarfile.open(bundle/'source-fixture.tar.gz','w:gz') as stream:
                content=b'class Fixture {}';member=tarfile.TarInfo('src/Fixture.java');member.size=len(content);stream.addfile(member,io.BytesIO(content))
            seal=ci.seal(bundle);runtime,manifest,plan=self.formal_fixture(root,seal)
            planfile=root/'execution-plan.json';ci.write_json(planfile,plan)
            fork_values={}
            for block in range(1,6):
                shard=shards/f'shard-write-1-{block}';shard.mkdir();ci.write_json(shard/'build-manifest.json',manifest)
                ci.write_json(shard/'host.json',dict(runner=f'fixture-{block}'))
                raw=shard/'measure';raw.mkdir()
                for orm in ci.ORMS:
                    item=dict(kind='write',group='write-1',block=block,params=dict(orm=orm,transactionRows=1));name=ci.cell_name(item)
                    values=[100.+block]*299+[10000.+block]  # Last-point spike must remain in every fork mean.
                    data=dict(forks=1,warmupIterations=2000,measurementIterations=300,warmupBatchSize=1,measurementBatchSize=1,params={k:str(v) for k,v in item['params'].items()},mode='ss',primaryMetric=dict(scoreUnit='us/op',rawData=[values],score=sum(values)/300,scoreError=1.,scoreConfidence=[1.,2.]))
                    ci.write_json(raw/(name+'.json'),[data]);fork_values[block]=sum(values)/300
                    status=dict(item,status='PASS',raw=str(raw/(name+'.json')),rawSha256=ci.digest(raw/(name+'.json')),hostMetadata='../host.json',pairingUnit=f'fixture-{block}',**{k:manifest[k] for k in audit.IDENTITY if k!='executionStage'},**execution.identity(manifest))
                    ci.write_json(raw/(name+'.status.json'),status)
                audit.audit_directory(shard,[secrets.token_urlsafe(32),secrets.token_urlsafe(32)])
            output=root/'aggregate';calls=[]
            def analyze_command(argv,check):
                calls.append(argv);self.assertEqual(Path(argv[1]),ci.ROOT/'scripts/analyze_results.py')
                analysis.analyze_statistics(Path(argv[argv.index('--run')+1]))
            args=argparse.Namespace(bundle=bundle,seal=seal,out=output,shards=shards,gate=None,execution_plan=planfile,expected_context=plan['executionContextSha256'])
            with patch.dict(os.environ,{'GITHUB_RUN_ID':manifest['executionWorkflowRunId'],'GITHUB_RUN_ATTEMPT':'1'}),patch('execution_protocol.verify_controller'),patch('ci_experiment.subprocess.run',side_effect=analyze_command),self.assertRaises(SystemExit):
                ci.aggregate(args)  # 750 intentionally missing cells remain NOT_RUN; no selective score completion.
            self.assertEqual(len(calls),1)
            summary=ci.read_json(output/'analysis/summary.json');row=summary['summaries']['write:{"transactionRows": 1}']['Kronos']
            self.assertEqual(row['n'],5);self.assertEqual(set(row['forkMeansUS']),{'1','2','3','4','5'})
            self.assertAlmostEqual(row['mean'],sum(fork_values.values())/5)
            self.assertEqual(summary['coverage']['passedForkRuns'],30);self.assertEqual(summary['coverage']['notRunForkRuns'],750)
            execution.same(manifest,summary);audit.verify_aggregate(output)
            self.assertEqual(summary['comparisons']['write:{"transactionRows": 1}']['Jdbc']['n'],5)
            status=next((output/'measure').glob('*.status.json'));changed=ci.read_json(status);changed['protocolSha256']='d'*64;ci.write_json(status,changed)
            with self.assertRaises(ValueError):analysis.analyze_statistics(output)


    def test_largest_formal_read_group_context_and_all_stats_fit_api_notice_limits(self):
        import execution_protocol as execution
        import analyze_results as analysis
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);aggregate=root/'aggregate';aggregate.mkdir();(aggregate/'analysis').mkdir();(aggregate/'measure').mkdir()
            runtime,manifest,plan=self.formal_fixture(root)
            # Exercise the real output schema, including source maps larger than the current controller.
            context=copy.deepcopy(plan['executionContext'])
            context['controller']['sourceFiles'].update({f'scripts/capacity-fixture-{i:03}.py':'a'*64 for i in range(80)})
            context['controller']['sourceTreeSha256']=execution.canonical(context['controller']['sourceFiles'])
            plan['executionContext']=context;plan['executionContextSha256']=execution.canonical(context)
            manifest=execution.bind(runtime,plan,manifest['bundleSha256']);manifest['executionStage']='measure-aggregate'
            ci.write_json(aggregate/'build-manifest.json',manifest);ci.write_json(aggregate/'measure/schedule.json',ci.schedule())
            values={i:123.45678901234567+i/10 for i in range(1,6)};statistics=analysis.summarize(list(values.values()));ratio=analysis.paired_ratio(values,{i:v/1.234567890123456 for i,v in values.items()})
            summaries={};definitions={};comparisons={};receipts={};bindings={}
            for item in ci.schedule():
                key=analysis.key_for(item['kind'],item['params']);orm=item['params']['orm']
                definitions[key]=dict(kind=item['kind'],parameters={k:v for k,v in item['params'].items() if k!='orm'},primaryUnit='us/query')
                row=dict(statistics,status='COMPLETE',runStatesByBlock={str(i):'PASS' for i in range(1,6)},forkMeansUS={str(i):v for i,v in values.items()},operationUnit='query',rowsPerOperation=item['params'].get('resultRows',1),derivedSingleThreadOperationsPerSecond=statistics,derivedSingleThreadRowsPerSecond=statistics,derivedRateNote='Reciprocal of each fork mean latency; not an independent throughput or concurrency experiment')
                summaries.setdefault(key,{})[orm]=row
                comparisons.setdefault(key,{})
                if orm!='Kronos':comparisons[key][orm]=ratio
                if item['group']=='entity-1000':
                    status=dict(item,status='PASS',rawSha256='b'*64,**{k:manifest[k] for k in audit.IDENTITY if k!='executionStage'},**execution.identity(manifest))
                    ci.write_json(aggregate/'measure'/(ci.cell_name(item)+'.status.json'),status)
            for block in range(1,6):
                name=f'shard-entity-1000-{block}';shard=root/name;shard.mkdir()
                shard_manifest=dict(manifest,executionGroup='entity-1000',executionBlock=block)
                ci.write_json(shard/'build-manifest.json',shard_manifest)
                ci.write_json(shard/'host.json',dict(RUNNER_NAME='GitHub Actions hosted fixture',ImageVersion='20261027.1',physicalHostIdentity='Unavailable on hosted VM',candidateGitSha=manifest['candidateGitSha'],sourceSha256=manifest['sourceSha256'],bundleSha256=manifest['bundleSha256']))
                (shard/'host-cpu.log').write_text('Architecture: x86_64\nCPU(s): 4\nModel name: Contract CPU model with provider metadata\nThread(s) per core: 2\nCore(s) per socket: 2\n')
                (shard/'host-memory.log').write_text('               total        used        free      shared  buff/cache   available\nMem:     17179869184  2100000000  9000000000   100000000  6079869184 13000000000\nSwap:             0           0           0\n')
                (shard/'host-idle.log').write_text(('procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----\n')+(' 0  0 0 10000000 1000 3000000 0 0 0 0 0 0 1 0 99 0 0\n'*6))
                audit.audit_directory(shard,[secrets.token_urlsafe(32),secrets.token_urlsafe(32)])
                receipts[name]=audit.verify_receipt(shard,manifest,manifest['executionWorkflowRunId'])
                target=aggregate/'hosts'/name;target.mkdir(parents=True)
                for source in shard.glob('host*'):
                    shutil.copyfile(source,target/source.name);bindings[str((target/source.name).relative_to(aggregate))]=dict(receipt=name,file=source.name)
            for status in (aggregate/'measure').glob('*.status.json'):
                # Bind each raw hash-bearing status to an independently scanned source file.
                source=root/'status-source';source.mkdir(exist_ok=True);ci.write_json(source/'build-manifest.json',manifest)
                shutil.copyfile(status,source/status.name);audit.audit_directory(source,[secrets.token_urlsafe(32),secrets.token_urlsafe(32)])
                key='status-'+status.stem;receipts[key]=audit.verify_receipt(source,manifest,manifest['executionWorkflowRunId']);bindings[str(status.relative_to(aggregate))]=dict(receipt=key,file=status.name)
                (source/status.name).unlink()
            ci.write_json(aggregate/'analysis/summary.json',dict(coverage=dict(plannedForkRuns=780,passedForkRuns=780,failedForkRuns=0,notRunForkRuns=0),summaries=summaries,comparisons=comparisons,caseDefinitions=definitions))
            audit.finish_aggregate(aggregate,manifest,receipts,bindings)
            transport_plan=dict(kind='aggregate',sourceRunId=manifest['executionWorkflowRunId'],sourceRunAttempt=1,candidateGitSha=manifest['candidateGitSha'],benchmarkGitSha=manifest['benchmarkGitSha'],expectedControllerGitSha=manifest['controllerGitSha'],artifact=dict(id=1))
            original=root/'original';original.mkdir();shutil.move(aggregate,original/'aggregate')
            with patch('artifact_transport.download_one',side_effect=lambda item,target:shutil.copytree(original,target)):
                transport.prepare_observation(transport_plan,0,root/'observation')
            index=ci.read_json(root/'observation/index.json');self.assertEqual(len(index),5)  # Four cases plus original context.
            notice_count=0
            for slot in range(5):
                printed=io.StringIO()
                with contextlib.redirect_stdout(printed):transport.emit_observation(root/'observation',slot)
                lines=printed.getvalue().splitlines();self.assertLessEqual(len(lines),10);notice_count+=len(lines)
                segments=[]
                for line in lines:
                    message=line.split('::',2)[2].replace('%0A','\n').replace('%0D','\r').replace('%25','%')
                    self.assertLessEqual(len(message.encode()),3072)
                    header,chunk=message.split('\n',1);segments.append((json.loads(header),chunk))
                rebuilt=''.join(chunk for header,chunk in sorted(segments,key=lambda item:item[0]['segmentIndex'])).encode()
                self.assertEqual(__import__('hashlib').sha256(rebuilt).hexdigest(),index[f'payload-{slot}.json'])
                decoded=json.loads(rebuilt)
                if slot<4:
                    case=next(iter(decoded['summary']['cases'].values()))
                    self.assertEqual(len(case['orms']),6)
                    self.assertTrue(all(len(row['forkMeansUS'])==5 and len(row['rawSha256ByBlock'])==5 for row in case['orms'].values()))
                else:self.assertEqual(decoded['executionContextSha256'],manifest['executionContextSha256'])
            self.notice_count=notice_count
            self.assertLessEqual(notice_count,40)


    def test_freeze_accepts_real_workflow_relative_protocol_path_without_building(self):
        import execution_protocol as execution
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);relative=Path('config/formal.json');absolute=ci.ROOT/relative;settings=ci.read_json(absolute)
            transport_plan=dict(repository=transport.REPOSITORY,runId=settings['runtime']['producerRunId'],runAttempt=1,benchmarkGitSha=settings['runtime']['benchmarkGitSha'],artifacts={})
            def prepare_original(plan,seal,candidate,benchmark,out):
                self.assertEqual(benchmark,'1497bd730b6d598879fb09774fe6d48e4c9e2f03');self.assertEqual(candidate,settings['runtime']['candidateGitSha'])
                ci.write_json(out/'runtime-bundle/build-manifest.json',dict(candidateGitSha=candidate,benchmarkGitSha=benchmark,sourceSha256=settings['runtime']['sourceSha256'],workflowRunId=plan['runId'],runtimeSha256='f'*64,mysqlImage='mysql:fixture@sha256:'+'a'*64))
                ci.write_json(out/'runtime-bundle/expected-schedule.json',ci.schedule())
            with patch.dict(os.environ,{'GITHUB_SHA':'e'*40,'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'1','GITHUB_OUTPUT':str(root/'outputs')}),patch('execution_protocol.subprocess.check_output',return_value='e'*40+'\n'),patch('execution_protocol.controller_files',return_value={str(relative):execution.sha(absolute)}),patch('artifact_transport.freeze_artifacts',return_value=transport_plan) as frozen,patch('calibration.prepare',side_effect=prepare_original),contextlib.redirect_stdout(io.StringIO()):
                execution.freeze(relative,execution.sha(absolute),'e'*40,root/'frozen')
            frozen.assert_called_once_with(settings['runtime']['producerRunId'],settings['runtime']['benchmarkGitSha'])
            plan=ci.read_json(root/'frozen/execution-plan.json')
            self.assertEqual(plan['executionContext']['protocolFile'],str(relative))
            execution.verify_snapshot(root/'frozen'/plan['executionContext']['controller']['snapshotFile'],plan['executionContext'])
            outputs=dict(line.split('=',1) for line in (root/'outputs').read_text().splitlines())
            self.assertEqual(len(json.loads(outputs['matrix'])['include']),40)
            with self.assertRaises(ValueError):execution.freeze(root/'external.json','a'*64,'e'*40,root/'rejected')

    def test_complete_audited_markdown_publication_can_auto_refresh_and_rejects_wrong_run(self):
        import execution_protocol as execution
        import analyze_results as analysis
        import export_publication as exporter
        import validate_publication as publication
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);runtime,manifest,plan=self.formal_fixture(root)
            aggregate=root/'aggregate';aggregate.mkdir();manifest['executionStage']='measure-aggregate'
            manifest['versionCatalogTOML']=(ci.ROOT/'libs.versions.toml').read_text()
            ci.write_json(aggregate/'build-manifest.json',manifest);execution.install(aggregate,plan)
            shutil.copyfile(root/plan['executionContext']['controller']['snapshotFile'],aggregate/plan['executionContext']['controller']['snapshotFile'])
            with tarfile.open(aggregate/'source-fixture-jvm.tar.gz','w:gz') as archive:
                content=b'class Fixture {}';member=tarfile.TarInfo('src/Fixture.java');member.size=len(content);archive.addfile(member,io.BytesIO(content))
            ci.write_json(aggregate/'validation/PASS.json',dict(status='PASS'))
            ci.write_json(aggregate/'validation/environment.json',dict(jdk='fixture',mysql='fixture'))
            ci.write_json(aggregate/'validation-gate.json',dict(status='PASS',candidateGitSha=manifest['candidateGitSha'],sourceSha256=manifest['sourceSha256'],**execution.identity(manifest)))
            planned=ci.schedule();ci.write_json(aggregate/'measure/schedule.json',planned)
            commands=[];host_map={};command_groups={}
            for item in planned:
                name=ci.cell_name(item);raw=aggregate/'measure'/(name+'.json');kind=item['kind'];n=10 if kind=='read' else 300
                values=[100.+item['block']]*n
                result=dict(forks=1,params={k:str(v) for k,v in item['params'].items()},mode='avgt' if kind=='read' else 'ss',warmupIterations=5 if kind=='read' else 2000,measurementIterations=n,warmupBatchSize=1,measurementBatchSize=1,warmupTime='2 s',measurementTime='2 s',primaryMetric=dict(scoreUnit='us/op',rawData=[values],score=values[0],scoreError=1.,scoreConfidence=[1.,2.]))
                ci.write_json(raw,[result])
                host=f"hosts/shard-{item['group']}-{item['block']}/host.json";ci.write_json(aggregate/host,dict(runner=item['block']))
                status=dict(item,status='PASS',exitCode=0,raw=str(raw),rawSha256=ci.digest(raw),hostMetadata='../'+host,pairingUnit=item['group']+str(item['block']),**{k:manifest[k] for k in audit.IDENTITY if k!='executionStage'},**execution.identity(manifest))
                ci.write_json(raw.with_name(name+'.status.json'),status);host_map[name+'.status.json']=host
                commands.append(dict(argv=['java','org.openjdk.jmh.Main'],log=str(raw.with_suffix('.log')),started='2026-10-28T00:00:00+00:00',finished='2026-10-28T00:01:00+00:00'))
                command_groups.setdefault(f"shard-{item['group']}-{item['block']}",[]).append(commands[-1])
            ci.write_json(aggregate/'ci-host-map.json',host_map)
            combined=[]
            for name,rows in sorted(command_groups.items()):
                stream=''.join(json.dumps(row)+'\n' for row in rows);(aggregate/'hosts'/name/'commands.jsonl').write_text(stream);combined.append(stream)
            (aggregate/'commands.jsonl').write_text(''.join(combined))
            ci.write_json(aggregate/'ci-coverage.json',dict(planned=780,received=780,notRun=[],shardFailures=[]))
            # Reuse exact deterministic ratio outputs for identical fixture inputs to keep this contract lightweight.
            paired=analysis.paired_ratio;cache={}
            def memoized(a,b):
                key=(tuple(sorted(a.items())),tuple(sorted(b.items())))
                if key not in cache:cache[key]=paired(a,b)
                return copy.deepcopy(cache[key])
            with patch('analyze_results.paired_ratio',side_effect=memoized):analysis.analyze_statistics(aggregate)
            summary=ci.read_json(aggregate/'analysis/summary.json');figures={}
            for i,key in enumerate(summary['caseDefinitions']):
                figures[key]={}
                for extension in ['png','svg','pdf']:
                    relative=f'figures/{i}.{extension}';file=aggregate/'analysis'/relative;file.parent.mkdir(exist_ok=True);file.write_bytes(('Contract figure '+key+extension).encode());figures[key][extension]=relative
            ci.write_json(aggregate/'analysis/figures.json',figures)
            source=root/'audit-source';shutil.copytree(aggregate,source)
            audit.audit_directory(source,[secrets.token_urlsafe(32),secrets.token_urlsafe(32)])
            receipt=audit.verify_receipt(source,manifest,manifest['executionWorkflowRunId'])
            bindings={name:dict(receipt='source',file=name) for name in receipt['files'] if not name.startswith('analysis/')}
            audit.finish_aggregate(aggregate,manifest,{'source':receipt},bindings)
            output=root/'publication'
            exporter.export(aggregate,output,exporter.DEFAULT_BASE,None,'',ci_audits=True)
            planfile=root/'execution-plan.json';ci.write_json(planfile,plan)
            args=(output,aggregate,planfile,plan['executionContextSha256'],manifest['controllerGitSha'],manifest['protocolSha256'],manifest['executionWorkflowRunId'],exporter.DEFAULT_BASE)
            with patch('execution_protocol.verify_controller'):
                self.assertEqual(publication.validate_ci(*args),ci.read_json(output/'publication-files.json')['reportId'])
                with self.assertRaises(ValueError):publication.validate_ci(*args[:6],'999999',args[-1])
                with self.assertRaises(ValueError):publication.validate_ci(*args[:4],'d'*40,*args[5:])
            self.assertFalse((output/'index.html').exists())
            with zipfile.ZipFile(next((output/'runs').glob('*/evidence.zip'))) as archive:
                self.assertTrue(all(not name.endswith(('.html','.css','.js')) for name in archive.namelist()))
            broken=copy.deepcopy(summary);broken['coverage']['passedForkRuns']=779;broken['coverage']['notRunForkRuns']=1
            ci.write_json(aggregate/'analysis/summary.json',broken)
            audit.finish_aggregate(aggregate,manifest,{'source':receipt},bindings)
            with patch('execution_protocol.verify_controller'),self.assertRaisesRegex(ValueError,'all 780'):publication.validate_ci(*args)

    def test_runtime_source_archive_publishes_only_jvm_inputs_without_mutating_original(self):
        import execution_protocol as execution
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);bundle=root/'bundle';bundle.mkdir();out=root/'output';out.mkdir();original=bundle/'source-fixture.tar.gz'
            with tarfile.open(original,'w:gz') as archive:
                for name in ['src/Fixture.java','build.gradle.kts','web/index.html','notes/plan.md']:
                    content=name.encode();member=tarfile.TarInfo(name);member.size=len(content);archive.addfile(member,io.BytesIO(content))
            before=ci.digest(original);execution.runtime_source_snapshot(bundle,out)
            self.assertEqual(ci.digest(original),before)
            record=ci.read_json(out/'runtime-source-manifest.json');self.assertEqual(record['originalArchiveSha256'],before)
            with tarfile.open(out/record['publishedArchive']) as archive:self.assertEqual(set(archive.getnames()),{'src/Fixture.java','build.gradle.kts'})


    def test_automatic_result_update_is_ci_gated_and_only_publisher_can_write(self):
        text=(ci.ROOT/'.github/workflows/measure-sealed.yml').read_text()
        blocks=__import__('re').split(r'(?m)^  ([a-z]+):\n',text.split('jobs:\n',1)[1])
        jobs=dict(zip(blocks[1::2],blocks[2::2]))
        for name,body in jobs.items():
            if name!='publish':self.assertNotIn('contents: write',body)
        publish=jobs['publish'];self.assertIn('needs: [freeze, measure, aggregate]',publish)
        self.assertIn("needs.measure.result == 'success' && needs.aggregate.result == 'success'",publish)
        for required in ['contents: write','branch: result','clean: false','single-commit: false','name: aggregate-reviewed-before-publication','--aggregate measured/aggregate','--expected-run "$GITHUB_RUN_ID"']:
            self.assertIn(required,publish)
        self.assertLess(publish.index('validate_publication.py'),publish.index('JamesIves/github-pages-deploy-action'))
        writers=[path.name for path in (ci.ROOT/'.github/workflows').glob('*.yml') if 'contents: write' in path.read_text()]
        self.assertEqual(writers,['measure-sealed.yml'])
        for workflow in ['measure-sealed.yml','diagnostics.yml','calibration.yml']:
            self.assertIn('branches: [main]',(ci.ROOT/'.github/workflows'/workflow).read_text())

if __name__ == '__main__':
    unittest.main()
