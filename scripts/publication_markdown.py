"""Generate Markdown and evidence links from the canonical measured report object."""
from __future__ import annotations
import json

KEY_SCENES=[('read',dict(projection='entity',tableRows=100000,resultRows=1,access='uniform')),('read',dict(projection='entity',tableRows=100000,resultRows=100,access='uniform')),('write',dict(transactionRows=100))]
NAMES={'Jdbc':'JDBC','Kronos':'Kronos','Jpa':'Hibernate','Jimmer':'Jimmer','Ktorm':'Ktorm','Mybatis':'MyBatis-Plus'}

def number(value):return f'{value:,.3f}'

def scene_label(definition,locale='en'):
    p=definition['parameters']
    if definition['kind']=='write':return f"空表首个事务 · {p['transactionRows']} 行" if locale=='zh-CN' else f"First transaction on reset empty table · {p['transactionRows']} rows"
    return f"{p['projection']} · 表 {p['tableRows']:,} 行 · 返回 {p['resultRows']} 行 · {p['access']}" if locale=='zh-CN' else f"{p['projection']} · {p['tableRows']:,} table rows · {p['resultRows']} returned · {p['access']}"

def method_lines(report,zh=False):
    context=report.get('executionContext') or {};settings=json.loads(context['protocolJSON']) if context.get('protocolJSON') else {}
    timing=settings.get('timing',{});read=dict(zip(timing.get('read',[])[::2],timing.get('read',[])[1::2]));write=dict(zip(timing.get('write',[])[::2],timing.get('write',[])[1::2]))
    if zh:
        lines=['- 每个场景有五个独立 JVM fork/block；同一 block 的六个适配器在同一 runner VM 和独立 MySQL 中按固定 seed 随机顺序执行。','- 查询返回完整物化的结果，计入连接/会话生命周期。表规模为 1,000 / 100,000 行，返回量为 1 / 100 行，覆盖 entity / map / scalar 与 hot / uniform 访问。','- 写入测量的是空表首个逐行 INSERT 事务，包含执行和 COMMIT。TRUNCATE、对象准备和结果校验在计时外。','- 先对每个 fork 的全部 measurement 值取均值，再用五个 fork 均值计算均值和 Student t 95% 区间；保留所有样本及失败状态。','- 配对比值为其他框架时延 / Kronos 时延，使用相同 block 的 log-ratio 和 95% 区间。表中的 n 表示独立 fork 数。','- JDK、数据库镜像、JDBC 驱动、连接池和缓存配置随环境证据保存；SQL、结果内容与资源生命周期通过独立正确性校验。']
        if read:lines.append(f"- 读取：{read['-wi']} × {read['-w']} 预热，{read['-i']} × {read['-r']} 测量；单位为 µs/query。")
        if write:lines.append(f"- 写入：{write['-wi']} 次事务预热，{write['-i']} 次 SingleShot 测量，batch size = 1；单位为 µs/transaction。")
    else:
        lines=['- Each scenario uses five independent JVM forks/blocks. All six adapters within a block share one runner VM and dedicated MySQL, in a fixed-seed randomized order.','- Queries fully materialize their result and include connection/session lifetime. Tables contain 1,000 / 100,000 rows; queries return 1 / 100 rows across entity / map / scalar and hot / uniform access.','- Writes time the first row-wise INSERT transaction on a reset empty table, including execution and COMMIT. TRUNCATE, object preparation and result checks occur outside timing.','- All measurement values are averaged within each fork. Five fork means determine the mean and Student t 95% interval; all samples and failure states remain available.','- Paired ratios are other latency / Kronos latency, using matching-block log-ratios and 95% intervals. The table n is the independent fork count.','- Environment evidence records the JDK, database image, driver, pool and caches. Separate correctness checks verify SQL, materialized values and resource lifetime.']
        if read:lines.append(f"- Reads: {read['-wi']} × {read['-w']} warmup, {read['-i']} × {read['-r']} measurement; µs/query.")
        if write:lines.append(f"- Writes: {write['-wi']} warmup transactions, {write['-i']} SingleShot measurements, batch size = 1; µs/transaction.")
    return lines

def render_methodology(report):return '# Measurement method\n\n'+'\n\n'.join(method_lines(report))+'\n\n# 测量方法\n\n'+'\n\n'.join(method_lines(report,True))+'\n'

def render_summary(report,public,browse):
    c=report['coverage'];prefix='runs/'+report['reportId'];environment=report['environment']
    lines=['# ORM benchmark · 性能对比','',f"JVM · MySQL · {len(report['scenarios'])} scenarios · 6 adapters · 5 independent blocks",'',
           '[English analysis]('+browse(prefix+'/report-en.md')+') · [中文详细分析]('+browse(prefix+'/report-zh-CN.md')+') · [Statistics JSON]('+public(prefix+'/analysis/summary.json')+') · [Raw evidence]('+report['evidenceZipUrl']+')','',
           '## Overview','',f"Completed fork runs: **{c['passedForkRuns']} / {c['plannedForkRuns']}**. Failed: {c['failedForkRuns']}; not run: {c['notRunForkRuns']}. Figures show fork means and 95% mean intervals.",'',
           '## 实验概览','',f"已完成 **{c['passedForkRuns']} / {c['plannedForkRuns']}** 个 fork；失败 {c['failedForkRuns']}，未运行 {c['notRunForkRuns']}。图中展示独立 fork 均值与 95% 均值区间。",'',
           f"JDK: `{environment.get('jdk','')}` · MySQL: `{environment.get('mysql','')}`",'',
           '## Key scenarios · 关键场景','']
    if report.get('partialReason'):lines += [report['partialReason'],'']
    for kind,parameters in KEY_SCENES:
        scene=next(scene for scene in report['scenarios'] if scene['definition']['kind']==kind and scene['definition']['parameters']==parameters)
        label=scene_label(scene['definition']);lines += ['### '+label,'']
        if scene.get('figure'):lines += ['!['+label+']('+scene['figure']['absoluteUrls']['png']+')','']
        lines += ['[Data and raw references · 明细]('+scene['absoluteDetailsUrl']+')','']
    lines += ['## Method · 方法','',
              'All adapters use the same SQL workload, data, driver and pool settings. Complete result checks run before measurement. Measurements are averaged within each fork; paired comparisons use the same block.','',
              '各适配器使用相同 SQL 工作量、数据、驱动与连接池配置，测量前完整核对结果。先在 fork 内汇总，再按同一 block 配对比较。','',
              '[Method and parameters]('+public(prefix+'/methodology.md')+') · [CSV]('+public(prefix+'/analysis/summary.csv')+')','']
    return '\n'.join(lines)

def render_detailed(report,locale,public,browse):
    zh=locale=='zh-CN';prefix='runs/'+report['reportId']
    lines=['# '+('ORM 性能对比详细报告' if zh else 'ORM benchmark: detailed results'),'']
    lines += ['## '+('测量条件' if zh else 'Measurement conditions'),'']+method_lines(report,zh)+['']
    lines += ['| '+('环境项 | 配置' if zh else 'Environment | Configuration')+' |','| --- | --- |']
    for key in ['jdk','javaVendor','os','architecture','mysql','driver','pool','innodb_buffer_pool_size','innodb_flush_log_at_trx_commit','sync_binlog','transaction_isolation','time_zone']:
        if key in report['environment']:lines.append('| '+key+' | `'+json.dumps(report['environment'][key],ensure_ascii=False).replace('|','\\|')+'` |')
    lines += ['','## '+('依赖版本' if zh else 'Dependency versions'),'','| Component | Version |','| --- | --- |']
    lines += [f"| {component['name']} | {component['version']} |" for component in report['requestedVersions']]
    lines += ['','## '+('完整场景' if zh else 'Scenario comparisons'),'']
    for scene in report['scenarios']:
        lines += ['### '+scene_label(scene['definition'],locale),'',('单位：' if zh else 'Unit: ')+scene['definition']['primaryUnit'],'',
                  '| '+('框架 | 均值 | 95% CI | n | 配对时延比（其他/Kronos）' if zh else 'Adapter | Mean | 95% CI | n | Paired latency ratio (other/Kronos)')+' |','| --- | ---: | ---: | ---: | ---: |']
        for orm in NAMES:
            score=scene['frameworks'][orm];interval=score.get('mean95CI');ratio=scene.get('comparisons',{}).get(orm,{})
            latency=number(score['mean']) if score['n'] else score['status'];ci='['+', '.join(number(value) for value in interval)+']' if interval else '—'
            pair='1.000 (reference)' if orm=='Kronos' and score['n'] else (number(ratio['geometricMeanLatencyRatio'])+' ['+', '.join(number(value) for value in ratio['logRatioT95CI'])+']' if 'geometricMeanLatencyRatio' in ratio else '—')
            lines.append(f"| {NAMES[orm]} | {latency} | {ci} | {score['n']} | {pair} |")
        links=['[JSON]('+scene['absoluteDetailsUrl']+')']
        if scene.get('figure'):links += ['['+extension.upper()+']('+scene['figure']['absoluteUrls'][extension]+')' for extension in ['png','svg','pdf']]
        lines += ['',' · '.join(links),'']+report.get('commentary',{}).get('scenarios',{}).get(scene['key'],{}).get(locale,[])+['']
    lines += report.get('commentary',{}).get('overview',{}).get(locale,[])
    lines += ['','## '+('运行与复现证据' if zh else 'Run and reproduction evidence'),'','UTC: '+report['runRangeUTC']['start']+' — '+report['runRangeUTC']['end'],'',
              ('完整性：' if zh else 'Coverage: ')+json.dumps(report['coverage'],sort_keys=True),'',
              ' · '.join('['+label+']('+url+')' for label,url in report.get('provenanceLinks',{}).items()),'']
    lines += ['- ['+label+']('+public(path)+')' for label,path in report['downloads'].items()]
    lines += ['','[English analysis]('+browse(prefix+'/report-en.md')+') · [中文详细分析]('+browse(prefix+'/report-zh-CN.md')+')','']
    return '\n'.join(lines)
