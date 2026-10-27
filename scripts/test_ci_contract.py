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

import ci_experiment as ci
import secret_audit as audit


class ContractTests(unittest.TestCase):
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
                        bundleSha256='d' * 64, executionWorkflowRunId='123', executionStage='shard')
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


if __name__ == '__main__':
    unittest.main()
