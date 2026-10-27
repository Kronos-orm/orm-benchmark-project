"""Render website summaries and bilingual analysis from one report object; no measurements here."""
from __future__ import annotations
import json

# Registered before measurement. A missing figure is not replaced by a favorable scene.
KEY_SCENES = [
    ('read', dict(projection='entity', tableRows=100000, resultRows=1, access='uniform')),
    ('read', dict(projection='entity', tableRows=100000, resultRows=100, access='uniform')),
    ('write', dict(transactionRows=100)),
]


def number(value):
    return f'{value:,.3f}'


def scene_label(definition, locale='en'):
    p = definition['parameters']
    if locale == 'zh-CN':
        if definition['kind'] == 'read':
            return f"{p['projection']}：{p['tableRows']}行表，每次返回{p['resultRows']}行，{p['access']}访问"
        return f"每事务{p['transactionRows']}行应用赋值主键逐行INSERT"
    if definition['kind'] == 'read':
        return f"{p['projection']}: {p['tableRows']} table rows, {p['resultRows']} returned rows, {p['access']} access"
    return f"{p['transactionRows']} assigned-key row-wise INSERTs / transaction"


def render_summary(report, public, browse):
    c = report['coverage']
    lines = ['# Kronos ORM benchmark / 性能基准报告', '',
             f"Candidate / 候选：`{report['candidateGitSha']}`", '',
             f"Benchmark source SHA-256 / 源码摘要：`{report['benchmarkSourceSha256']}`", '',
             f"Run range / 运行时间（UTC）：{report['runRangeUTC']['start']} — {report['runRangeUTC']['end']}", '',
             f"Scheduled forks / 计划JVM重复：{c['plannedForkRuns']}；PASS：{c['passedForkRuns']}；FAIL：{c['failedForkRuns']}；NOT RUN：{c['notRunForkRuns']}。", '',
             'JVM/MySQL experiment. Each scenario plans five independent JVM forks; within-fork iterations are averaged first. Full scene states, versions, SQL checks and uncertainty are in the detailed analyses.', '',
             'JVM/MySQL实验，每场景计划5个独立JVM，先在fork内汇总iteration。完整场景状态、版本、SQL校验和不确定性见详细分析。', '',
             'Execution scope / 执行范围：' + report.get('executionEnvironment', 'Local controlled JVM/MySQL experiment') + '.', '',
             f"Environment / 环境：{report['environment'].get('os', '')}；JDK {report['environment'].get('jdk', '')}；MySQL {report['environment'].get('mysql', '')}。", '']
    if report['partialReason']:
        lines += ['Completeness limitation / 完整性限制：' + report['partialReason'], '']
    prefix = 'runs/' + report['reportId']
    lines += ['## Open the complete analysis / 按需查看完整分析', '',
              '- [English analysis](' + browse(prefix + '/report-en.md') + ')',
              '- [中文详细分析](' + browse(prefix + '/report-zh-CN.md') + ')',
              '- [All statistics JSON / 完整统计JSON](' + public(prefix + '/analysis/summary.json') + ')',
              '- [Statistics CSV / 统计CSV](' + public(prefix + '/analysis/summary.csv') + ')',
              '- [Portable static Web report / 静态Web报告包](' + report['portableZipUrl'] + ')',
              '- [Commands, source and artifact identity / 命令、源码与制品摘要](' + public(prefix + '/build-manifest.json') + ')', '',
              '## Registered key scenes / 预先指定的关键场景', '',
              'These scenes were selected before measurement. Figures show JVM-fork means and 95% Student t mean intervals; sample counts are printed in the figures.', '',
              '以下场景在测量前固定；图中显示fork均值、95% Student t均值区间及实际样本数。完整矩阵通过上述详细报告按需打开。', '']
    for kind, parameters in KEY_SCENES:
        scene = next(s for s in report['scenarios'] if s['definition']['kind'] == kind and s['definition']['parameters'] == parameters)
        label = scene_label(scene['definition']) + ' / ' + scene_label(scene['definition'], 'zh-CN')
        lines += ['### ' + label, '']
        if 'figure' in scene:
            lines += ['![' + label + '](' + scene['figure']['absoluteUrls']['png'] + ')', '']
        else:
            lines += ['Run states / 运行状态：' + '; '.join(f"{orm}: {value['status']}" for orm, value in scene['frameworks'].items()) + '.', '']
        lines += ['[Scene details and raw references / 场景明细与原始证据](' + scene['absoluteDetailsUrl'] + ')', '']
    lines += ['## Reading the result / 结果解释', '',
              'Latency includes connection/session lifetime and full materialization. Fixed-row sensitivity and JDBC help explain end-to-end costs; they do not isolate ORM CPU. Writes are transactions, not native JDBC-batch throughput. GC/JFR diagnostics are separate.', '',
              '时延包含连接/会话生命周期与完整物化；固定返回行数和JDBC基线用于理解端到端成本，不直接等于ORM纯CPU开销。写入单位是事务，GC/JFR诊断独立于主成绩。', '']
    return '\n'.join(lines)


def render_detailed(report, locale, public, browse):
    zh = locale == 'zh-CN'
    prefix = 'runs/' + report['reportId']
    lines = ['# ' + ('Kronos ORM JVM/MySQL实验详细分析' if zh else 'Kronos ORM JVM/MySQL experiment: detailed analysis'), '',
             ('候选Git SHA：' if zh else 'Candidate Git SHA: ') + '`' + report['candidateGitSha'] + '`', '',
             ('benchmark源码SHA-256：' if zh else 'Benchmark source SHA-256: ') + '`' + report['benchmarkSourceSha256'] + '`', '',
             ('运行时间（UTC）：' if zh else 'Run range (UTC): ') + report['runRangeUTC']['start'] + ' — ' + report['runRangeUTC']['end'], '',
             ('完整性：' if zh else 'Coverage: ') + json.dumps(report['coverage'], sort_keys=True), '']
    if report['partialReason']:
        lines += [('完整性限制：' if zh else 'Completeness limitation: ') + report['partialReason'], '']
    lines += ['## ' + ('环境与证据' if zh else 'Environment and evidence'), '']
    lines += [report.get('executionEnvironment', 'Local controlled JVM/MySQL experiment'), '']
    for key in ['jdk', 'javaVendor', 'os', 'architecture', 'mysql', 'driver', 'pool', 'innodb_buffer_pool_size', 'innodb_flush_log_at_trx_commit', 'sync_binlog', 'transaction_isolation', 'time_zone']:
        if key in report['environment']:
            lines.append(f"- {key}: `{json.dumps(report['environment'][key], ensure_ascii=False)}`")
    lines += [''] + [f'- [{label}]({public(path)})' for label, path in report['downloads'].items()] + ['']
    lines += ['## ' + ('版本与发布日期' if zh else 'Versions and publication dates'), '']
    for component in report['requestedVersions']:
        released = component.get('released', 'as-of 2026-10-27')
        lines.append(f"- {component['name']}: `{component['version']}`; {released}.")
    lines += ['', ('实际解析JAR名称和SHA-256见build manifest；上述为同一版本审计快照中的固定目标。' if zh else 'Resolved JAR names and SHA-256 identities are in the build manifest; these are the fixed targets from the shared version audit.'), '']
    lines += ['## ' + ('统计与单位' if zh else 'Statistics and units'), '']
    lines += ([
        '每个场景以独立JVM fork/block为重复单位，先对同一fork内measurement iterations取均值；图展示全部fork点、均值与Student t 95%区间。原JMH区间保留在原始JSON，不能与fork层区间混称。',
        '比值方向固定为other latency / Kronos latency，按同block成对log-ratio求几何均值和区间，并保留block bootstrap区间。五个block分辨率有限；不确定方向不等于证明相等，多场景属于探索性分析。',
        '读取单位为us/query；写入单位为us/transaction，包含一次COMMIT。按每fork时延倒数折算的操作率/行率不称作独立吞吐或并发实验。',
    ] if zh else [
        'The independent repeat unit is one JVM fork/block. Measurement iterations are averaged within each fork before inference. Figures show all fork points, means and Student t 95% mean intervals. Native JMH intervals remain in raw JSON and are a separate calculation.',
        'Latency ratios use other/Kronos and matched-block log-ratios; geometric means and intervals accompany block-bootstrap intervals. Five blocks give limited precision. Uncertain direction is not proof of equality; multiple-scene comparisons are exploratory.',
        'Read units are us/query. Write units are us/transaction, including COMMIT. Operation/row rates converted from each fork mean are labeled as conversions, not independent throughput or concurrency experiments.',
    ])
    lines += ['', '## ' + ('全部场景' if zh else 'Complete scene matrix'), '']
    for scene in report['scenarios']:
        lines += ['### ' + scene_label(scene['definition'], locale), '']
        for orm, score in scene['frameworks'].items():
            if score['n']:
                ci = score.get('mean95CI')
                interval = f"[{number(ci[0])}, {number(ci[1])}]" if ci else ('样本不足' if zh else 'not estimable')
                if zh:
                    line = f"- **{orm}**：{score['status']}，n={score['n']}个fork；均值{number(score['mean'])} {scene['definition']['primaryUnit']}；95%均值区间{interval}；中位数{number(score['median'])}。"
                else:
                    line = f"- **{orm}**: {score['status']}, n={score['n']} forks; mean {number(score['mean'])} {scene['definition']['primaryUnit']}; 95% mean CI {interval}; median {number(score['median'])}."
            else:
                line = f"- **{orm}**: {score['status']}; fork states `{json.dumps(score['runStatesByBlock'], sort_keys=True)}`."
            lines.append(line)
        if 'figure' in scene:
            lines += ['', '![' + scene_label(scene['definition'], locale) + '](' + scene['figure']['absoluteUrls']['png'] + ')']
        commentary = report.get('commentary', {}).get('scenarios', {}).get(scene['key'], {}).get(locale, [])
        lines += [''] + commentary + ['']
        lines += [('场景明细、配对比值、原始引用：' if zh else 'Scene details, paired ratios and raw references: ') + '[JSON](' + scene['absoluteDetailsUrl'] + ')', '']
    overview = report.get('commentary', {}).get('overview', {}).get(locale, [])
    if overview:
        lines += ['## ' + ('跨场景解释' if zh else 'Cross-scene interpretation'), ''] + overview + ['']
    lines += ['## ' + ('解释边界' if zh else 'Interpretation boundaries'), '']
    lines += ([
        'JDBC基线、1/100行和不同投影刻画端到端成本。行数增量仍包括数据库执行、传输、驱动、映射与分配；单行热缓存总延迟不直接推出ORM纯CPU优劣。JDBC API调用数也不自动等于wire往返。',
        'GC/JFR诊断单独运行，用于支持具体场景的机制推断，不混入主成绩。失败、部分和未运行状态保持可见。结论适用于记录的JVM/MySQL环境与负载；CI虚拟机硬件变化须结合host证据解释。',
    ] if zh else [
        'JDBC, fixed 1/100-row results and projection changes characterize end-to-end costs. Row-count deltas still include database execution, transfer, driver, mapping and allocation. Single hot-row latency does not isolate ORM CPU, and JDBC API calls are not automatically wire round trips.',
        'GC/JFR diagnostics run separately to support scene-specific mechanism inference. Failure, partial and not-run states remain visible. Conclusions apply to the recorded JVM/MySQL setup and workloads; CI VM hardware variation must be interpreted with the host evidence.',
    ])
    lines += ['', '[English analysis](' + browse(prefix + '/report-en.md') + ') · [中文详细分析](' + browse(prefix + '/report-zh-CN.md') + ')', '']
    return '\n'.join(lines)
