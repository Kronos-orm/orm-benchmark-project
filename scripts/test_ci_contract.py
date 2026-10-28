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


if __name__ == '__main__':
    unittest.main()
