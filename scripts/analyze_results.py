#!/usr/bin/env python3
"""Rebuild fork-level summaries/plots from formal JMH JSON; pilot/profile never enter scores."""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import random
import statistics as stats
import sys
sys.dont_write_bytecode = True
import execution_protocol as protocol
from urllib.parse import urlsplit, unquote

SEED = 2026102704
ORMS = ['Jdbc', 'Kronos', 'Jpa', 'Jimmer', 'Ktorm', 'Mybatis']
# Two-sided 95% Student t critical values; the registered formal design has df=4.
T95 = {1: 12.706205, 2: 4.302653, 3: 3.182446, 4: 2.776445, 5: 2.570582,
       6: 2.446912, 7: 2.364624, 8: 2.306004, 9: 2.262157, 10: 2.228139}


def load(path):
    return json.loads(path.read_text())


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def key_for(kind, params):
    return kind + ':' + json.dumps({k: v for k, v in params.items() if k != 'orm'}, sort_keys=True)


def summarize(values):
    result = dict(n=len(values), mean=stats.mean(values), median=stats.median(values), independentUnit='JVM fork/block')
    if len(values) >= 2:
        deviation = stats.stdev(values)
        result['sampleSD'] = deviation
        df = len(values) - 1
        if df not in T95:
            raise ValueError('Unregistered sample size: extend documented t critical values before analysis')
        error = T95[df] * deviation / math.sqrt(len(values))
        result['mean95CI'] = [result['mean'] - error, result['mean'] + error]
        result['mean95CIAssumption'] = 'Student t interval over independent fork means; approximately normal fork means'
    return result


def percentile(values, probability):
    index = (len(values) - 1) * probability
    first = int(index)
    fraction = index - first
    return values[first] * (1 - fraction) + values[min(first + 1, len(values) - 1)] * fraction


def paired_ratio(compared, kronos):
    blocks = sorted(compared.keys() & kronos.keys())
    if len(blocks) < 2:
        return dict(status='INSUFFICIENT_PAIRED_BLOCKS', n=len(blocks))
    logs = [math.log(compared[b] / kronos[b]) for b in blocks]
    result = summarize(logs)
    low, high = result.pop('mean95CI')
    rng = random.Random(SEED)
    bootstrap = sorted(math.exp(stats.mean(rng.choices(logs, k=len(logs)))) for _ in range(20000))
    return dict(status='COMPLETE' if len(blocks) == 5 else 'PARTIAL', n=len(blocks), pairedBlocks=blocks,
                geometricMeanLatencyRatio=math.exp(stats.mean(logs)), logRatioT95CI=[math.exp(low), math.exp(high)],
                blockBootstrapPercentile95CI=[percentile(bootstrap, 0.025), percentile(bootstrap, 0.975)],
                ratioDefinition='other latency / Kronos latency; above 1 means lower measured Kronos latency',
                limitation='Five blocks provide limited bootstrap resolution; exploratory comparisons are not universal rankings')


def analyze_statistics(run):
    """Validate and summarize actual raw observations without importing a plotting runtime."""
    run = run.resolve()
    schedule = load(run / 'measure/schedule.json')
    manifest = load(run / 'build-manifest.json')
    protocol.identity(manifest)
    groups, provenance, status_by_case, hosts = {}, {}, {}, {}
    planned = {(item['kind'], json.dumps(item['params'], sort_keys=True), item['block']) for item in schedule}
    if len(planned) != len(schedule):
        raise ValueError('Duplicate case/block in the formal schedule')
    seen = set()
    for item in schedule:
        key, orm = key_for(item['kind'], item['params']), item['params']['orm']
        groups.setdefault(key, {}).setdefault(orm, {})
    for statusfile in sorted((run / 'measure').glob('*.status.json')):
        status = load(statusfile)
        protocol.same(manifest, status)
        if status.get('sourceSha256') != manifest['sourceSha256'] or status.get('candidateGitSha') != manifest['candidateGitSha']:
            raise ValueError('Raw status provenance differs from this build manifest: ' + str(statusfile))
        identifier = (status['kind'], json.dumps(status['params'], sort_keys=True), status['block'])
        if identifier not in planned or identifier in seen:
            raise ValueError('Unplanned or duplicate raw status record: ' + str(statusfile))
        seen.add(identifier)
        key, orm = key_for(status['kind'], status['params']), status['params']['orm']
        status_by_case[(key, orm, status['block'])] = status['status']
        host_map = load(run / 'ci-host-map.json') if (run / 'ci-host-map.json').exists() else {}
        host_relative = host_map.get(statusfile.name, status.get('hostMetadata'))
        if host_relative:
            host_path = (run / host_relative).resolve()
            if not host_path.is_relative_to(run):
                raise ValueError('Host evidence must stay inside the experiment directory')
            hosts[(key, orm, status['block'])] = (status.get('pairingUnit'), hashlib.sha256(host_path.read_bytes()).hexdigest(), host_relative)
        if status['status'] != 'PASS':
            continue
        # Raw files stay siblings of their status record, including in a downloaded publication.
        path = statusfile.parent / unquote(Path(urlsplit(status['raw']).path).name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != status.get('rawSha256'):
            raise ValueError('Raw JSON changed after execution: ' + str(path))
        data = load(path)
        if len(data) != 1 or data[0]['primaryMetric']['scoreUnit'] != 'us/op':
            raise ValueError('Expected one microsecond latency result: ' + str(path))
        if data[0]['params'] != {k: str(v) for k, v in status['params'].items()} or data[0]['mode'] != ('avgt' if status['kind'] == 'read' else 'ss'):
            raise ValueError('JMH parameters or mode differ from the registered cell')
        protocol.validate_jmh(manifest, data[0], status['kind'])
        metric = data[0]['primaryMetric']
        if len(metric['rawData']) != 1:
            raise ValueError('Each command must contain one independent JVM fork')
        iterations = metric['rawData'][0]
        if not iterations or any(not math.isfinite(v) or v <= 0 for v in iterations):
            raise ValueError('Nonfinite or nonpositive latency')
        block = status['block']
        if block in groups[key][orm]:
            raise ValueError('Duplicate independent block result')
        groups[key][orm][block] = stats.mean(iterations)
        provenance[str(path)] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                     jmhScore=metric['score'], jmhScoreError=metric['scoreError'],
                                     jmhScoreConfidence=metric['scoreConfidence'], jmhUnit=metric['scoreUnit'])
    if manifest.get('executionEnvironment'):
        for key, orms in groups.items():
            for block in range(1, 6):
                paired = [hosts.get((key, orm, block)) for orm in ORMS if block in orms.get(orm, {})]
                if paired and (None in paired or any(not pair[0] for pair in paired) or len({pair[:2] for pair in paired}) != 1):
                    raise ValueError('ORM comparison would pair different runner hosts or missing host evidence')
    if not any(blocks for orms in groups.values() for blocks in orms.values()):
        raise ValueError('No successful formal measurements; no numeric report or empty plots were generated')
    directory = run / 'analysis'; directory.mkdir(parents=True, exist_ok=True)
    summaries, comparisons = {}, {}
    csvrows = []
    for key, orms in groups.items():
        summaries[key], comparisons[key] = {}, {}
        for orm in ORMS:
            blocks = orms.get(orm, {})
            run_states = {b: status_by_case.get((key, orm, b), 'NOT_RUN') for b in range(1, 6)}
            state = 'COMPLETE' if set(blocks) == {1, 2, 3, 4, 5} else 'PARTIAL' if blocks else 'FAILED' if 'FAIL' in run_states.values() else 'NOT_RUN'
            parameters = json.loads(key.split(':', 1)[1])
            rows_per_operation = parameters['resultRows'] if key.startswith('read:') else parameters['transactionRows']
            summary = dict(status=state, runStatesByBlock=run_states, forkMeansUS=blocks,
                           operationUnit='query' if key.startswith('read:') else 'transaction', rowsPerOperation=rows_per_operation)
            if blocks:
                summary.update(summarize(list(blocks.values())))
                summary['derivedSingleThreadOperationsPerSecond'] = summarize([1e6 / value for value in blocks.values()])
                summary['derivedSingleThreadRowsPerSecond'] = summarize([rows_per_operation * 1e6 / value for value in blocks.values()])
                summary['derivedRateNote'] = 'Reciprocal of each fork mean latency; not an independent throughput or concurrency experiment'
            summaries[key][orm] = summary
            ci = summary.get('mean95CI', [None, None])
            csvrows.append(dict(case=key, orm=orm, status=state, n=len(blocks), meanUS=summary.get('mean'), medianUS=summary.get('median'),
                                sdUS=summary.get('sampleSD'), low95US=ci[0], high95US=ci[1]))
            if orm != 'Kronos' and blocks and orms.get('Kronos'):
                comparisons[key][orm] = paired_ratio(blocks, orms['Kronos'])
    deltas = {}
    for key, orms in groups.items():
        if not key.startswith('read:'):
            continue
        params = json.loads(key.split(':', 1)[1])
        if params['resultRows'] != 100:
            continue
        single = key_for('read', dict(params, resultRows=1))
        if single not in groups:
            continue
        for orm, blocks in orms.items():
            common = sorted(blocks.keys() & groups[single].get(orm, {}).keys())
            if common:
                values = [blocks[b] - groups[single][orm][b] for b in common]
                deltas[key + ':' + orm] = dict(summarize(values), additionalRows=99,
                    meaning='End-to-end incremental cost includes DB execution, transfer, driver, mapping and allocation; not isolated ORM CPU time')
    case_definitions = {key: dict(kind=key.split(':', 1)[0], parameters=json.loads(key.split(':', 1)[1]),
                                  primaryUnit='us/query' if key.startswith('read:') else 'us/transaction') for key in groups}
    coverage = dict(plannedForkRuns=len(schedule), passedForkRuns=sum(v == 'PASS' for v in status_by_case.values()),
                    failedForkRuns=sum(v == 'FAIL' for v in status_by_case.values()), notRunForkRuns=len(schedule) - len(status_by_case),
                    scenarioStates={state: sum(row['status'] == state for row in csvrows) for state in ['COMPLETE', 'PARTIAL', 'FAILED', 'NOT_RUN']})
    dump(directory / 'summary.json', dict(caseDefinitions=case_definitions, coverage=coverage, independentSampleUnit='JVM fork/block', plannedIndependentReplicates=5, candidateGitSha=manifest['candidateGitSha'], sourceSha256=manifest['sourceSha256'],
                                        summaries=summaries, comparisons=comparisons, rowCountSensitivity=deltas,
                                        rawProvenance=provenance, hostPairing={str(k): v for k, v in hosts.items()},
                                        **protocol.identity(manifest), **({'executionContext': manifest['executionContext']} if 'executionContext' in manifest else {}),
                                        executionEnvironment=manifest.get('executionEnvironment', 'Local controlled JVM/MySQL experiment'),
                                        generatedAt=dt.datetime.now(dt.timezone.utc).isoformat()))
    with (directory / 'summary.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csvrows[0]))
        writer.writeheader(); writer.writerows(csvrows)
    return dict(run=run,manifest=manifest,groups=groups,summaries=summaries,directory=directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    computed = analyze_statistics(args.run)
    run,manifest,groups,summaries,directory = (computed[key] for key in ['run','manifest','groups','summaries','directory'])
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figures = directory / 'figures'; figures.mkdir(exist_ok=True)
    commands = [json.loads(line) for line in (run / 'commands.jsonl').read_text().splitlines() if line.strip()]
    measured_commands = [entry for entry in commands if '/measure/' in entry.get('log', '')]
    time_range = min(entry['started'] for entry in measured_commands) + ' to ' + max(entry['finished'] for entry in measured_commands) if measured_commands else 'See commands.jsonl for recorded execution times'
    figurelinks = []
    figure_index = {}
    for index, (key, orms) in enumerate(groups.items(), 1):
        measured = [orm for orm in ORMS if orms.get(orm)]
        if not measured:
            continue
        kind, serialized = key.split(':', 1)
        params = json.loads(serialized)
        caption = ', '.join(f'{k}={v}' for k, v in sorted(params.items()))
        fig, ax = plt.subplots(figsize=(10, 5.4))
        for y, orm in enumerate(measured):
            values = list(orms[orm].values())
            color = '#245987' if orm == 'Kronos' else '#5c6268'
            jitter = [(i - (len(values) - 1) / 2) * 0.055 for i in range(len(values))]
            ax.scatter(values, [y + offset for offset in jitter], s=25, color=color, alpha=0.75)
            s = summaries[key][orm]
            if 'mean95CI' in s:
                low, high = s['mean95CI']
                ax.errorbar(s['mean'], y, xerr=[[s['mean'] - low], [high - s['mean']]], fmt='D', color=color, capsize=4, markersize=5)
            else:
                ax.scatter(s['mean'], y, marker='D', color=color, s=28)
        ax.set_yticks(range(len(measured)), [f'{orm} (n={len(orms[orm])})' for orm in measured]); ax.invert_yaxis()
        ax.set_ylabel('Framework / typed JDBC baseline')
        ax.set_xlabel('Query latency (us/query)' if kind == 'read' else 'Transaction latency (us/transaction)')
        ax.set_title(('Materialized range query' if kind == 'read' else 'Assigned-key row-wise INSERT transaction') + '\n' + caption)
        ax.grid(axis='x', alpha=0.2)
        ax.spines[['top', 'right']].set_visible(False)
        fig.text(0.04, 0.045, 'Source: formal JMH raw JSON; dots = JVM fork means; diamonds = mean with 95% Student t CI. Partial groups show available data.', fontsize=8)
        fig.text(0.04, 0.015, 'Run range (UTC): ' + time_range, fontsize=7)
        fig.tight_layout(rect=(0, 0.08, 1, 1))
        stem = f'{index:02d}-{kind}'
        for extension in ['png', 'svg', 'pdf']:
            fig.savefig(figures / (stem + '.' + extension), dpi=170)
        plt.close(fig)
        figurelinks.append((caption, 'figures/' + stem + '.png'))
        figure_index[key] = {extension: 'figures/' + stem + '.' + extension for extension in ['png', 'svg', 'pdf']}
    dump(directory / 'figures.json', figure_index)
    report = ['# JVM/MySQL 实验分析', '', '候选 SHA：`' + manifest['candidateGitSha'] + '`。源码 SHA-256：`' + manifest['sourceSha256'] + '`。', '',
              '运行环境：' + manifest.get('executionEnvironment', 'Local controlled JVM/MySQL experiment'), '',
              '统计单位是独立 JVM fork/block；同一 JVM 的 measurement iterations 先取均值。图中展示 fork 点与均值的 95% Student t 区间，原 JMH 置信区间保存在 summary.json。', '',
              '按每个 fork 时延倒数折算的单线程操作率不是独立吞吐或并发实验。1→100 行增量包含数据库、传输、驱动与映射成本，不能直接称为 ORM CPU 差异。JFR/GC 诊断不进入主成绩。', '',
              '具体机制、运行状态、限制和复现命令应结合 validation、commands.jsonl 与 profile 单独解释。']
    for title, link in figurelinks:
        report += ['', '## ' + title, '', '![' + title + '](' + link + ')']
    (directory / 'analysis.md').write_text('\n'.join(report) + '\n')
    print('Rebuilt numeric summaries and scientific plots from formal raw JSON:', directory)


if __name__ == '__main__':
    main()
