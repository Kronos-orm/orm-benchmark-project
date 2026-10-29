"""Remote-only planned-formal calibration using an existing sealed runtime; never builds JVM code."""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
sys.dont_write_bytecode = True
from types import SimpleNamespace
import ci_experiment as ci
import artifact_transport as transport
import secret_audit as audit


def scenario(index, preset='planned-formal'):
    group_index=index
    if preset not in ['planned-formal', 'write-warm2000']: raise ValueError('Unknown calibration preset')
    if preset=='write-warm2000':
        if index not in range(2): raise ValueError('Write preset has exactly two scenarios')
        index+=6
    if index not in range(8): raise ValueError('Expected one of eight registered pilot scenarios')
    kind, parameters = ci.cases('pilot')[index]
    orms = list(ci.ORMS)
    random.Random(str(ci.SEED) + json.dumps(parameters, sort_keys=True)).shuffle(orms)
    return [dict(kind=kind, block=1, group=str(group_index), params=dict(parameters, orm=orm)) for orm in orms]


def timing(kind, preset='planned-formal'):
    if preset=='write-warm2000' and kind!='write': raise ValueError('Write-only preset cannot time read scenarios')
    return ['-bm', 'avgt', '-tu', 'us', '-wi', '5', '-w', '2s', '-i', '10', '-r', '2s'] if kind == 'read' else ['-bm', 'ss', '-tu', 'us', '-wi', '2000' if preset=='write-warm2000' else '10', '-i', '30', '-bs', '1', '-wbs', '1']


def warmups(text):
    result = []
    import re
    for match in re.finditer(r'# Warmup Iteration\s+(\d+):(.*?)(?=# Warmup Iteration\s+\d+:|\nIteration\s+\d+:|\Z)', text, re.S):
        values = re.findall(r'([0-9.eE+-]+)\s+us/op', match.group(2))
        if values: result.append(dict(iteration=int(match.group(1)), us=float(values[-1])))
    return result


def trends(values):
    midpoint = len(values) // 2; first, last = values[:midpoint], values[midpoint:]
    center = (len(last) - 1) / 2
    slope = sum((i-center)*(v-statistics.mean(last)) for i,v in enumerate(last)) / sum((i-center)**2 for i in range(len(last)))
    result = dict(meanUS=statistics.mean(values), sampleCV=statistics.stdev(values)/statistics.mean(values),
                firstHalfMeanUS=statistics.mean(first), secondHalfMeanUS=statistics.mean(last),
                firstHalfOverSecondHalf=statistics.mean(first)/statistics.mean(last),
                lastOverFirst=values[-1]/values[0], secondHalfSlopeUSPerIteration=slope,
                secondHalfNormalizedSlopePerIteration=slope/statistics.mean(last),
                secondHalfLastOverFirst=last[-1]/last[0], secondHalfSampleCV=statistics.stdev(last)/statistics.mean(last),
                trendScope='Within one fork; descriptive diagnostics, not independent statistical replicates')
    result['first5OverLast5']=statistics.mean(values[:5])/statistics.mean(values[-5:])
    result['last5CV']=statistics.stdev(values[-5:])/statistics.mean(values[-5:])
    if len(values)==30:
        result['consecutive10MeansUS']=[statistics.mean(values[start:start+10]) for start in [0,10,20]]
        result['last10CV']=statistics.stdev(values[-10:])/statistics.mean(values[-10:])
        change=max(abs(left/right-1) for left,right in zip(result['consecutive10MeansUS'],result['consecutive10MeansUS'][1:]))
        variability=result['last10CV']
    else:
        change=abs(result['firstHalfOverSecondHalf']-1);variability=result['last5CV']
    result['diagnosticFlags']=dict(windowChangeOver5Percent=change>.05,lateWindowCVOver10Percent=variability>.10,
                                  meaning='Descriptive flags only; never discard cells, choose retries or certify steady state')
    return result


def prepare(plan, seal, candidate_sha, benchmark_sha, out):
    if os.environ.get('GITHUB_ACTIONS') != 'true': raise ValueError('Calibration runs only on remote CI')
    transport.download_artifacts(plan, out)
    bundle = out / 'runtime-bundle'; original = out / 'approved-preflight'
    manifest = ci.verify(bundle, seal)
    if manifest['candidateGitSha'] != candidate_sha or manifest['benchmarkGitSha'] != benchmark_sha:
        raise ValueError('Original runtime identities differ from explicitly frozen calibration target')
    frozen = out / 'reuse-plan.json'
    ci.write_json(frozen, dict(candidateGitSha=candidate_sha, benchmarkGitSha=benchmark_sha, workflowRunAttempt='1', reuseArtifacts=plan))
    ci.reuse(SimpleNamespace(bundle=bundle, frozen=frozen, source_run_id=plan['runId'], gate=original/'gate', pilot=original/'pilot', pilot_review='{}'))
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as handle:
        handle.write('mysql_image=' + manifest['mysqlImage'] + '\n')


def execute(bundle, seal, gate, index, out, preset='planned-formal'):
    if os.environ.get('GITHUB_ACTIONS') != 'true': raise ValueError('Calibration runs only on remote CI')
    transport.require_single_attempt(); original = ci.verify(bundle, seal)
    protocol=dict(preset=preset, write=timing('write',preset), scope='write-only' if preset=='write-warm2000' else 'read-and-write')
    if preset=='planned-formal': protocol['read']=timing('read')
    protocol_sha=__import__('hashlib').sha256(json.dumps(protocol,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    manifest = dict(original, bundleSha256=seal, executionStage='calibration', executionWorkflowRunId=os.environ['GITHUB_RUN_ID'],
                    executionWorkflowRunAttempt=os.environ['GITHUB_RUN_ATTEMPT'], executionGroup=str(index), executionBlock=1,
                    controllerGitSha=os.environ['GITHUB_SHA'], controllerFileSha256=ci.digest(Path(__file__)),
                    classification='CALIBRATION_ONLY_NOT_FORMAL', originalProducerRunId=original['workflowRunId'],
                    calibrationProtocol=protocol, protocolSha256=protocol_sha)
    out.mkdir(parents=True, exist_ok=False); ci.write_json(out/'build-manifest.json',manifest)
    ci.host_snapshot(out,manifest)
    java = Path(os.environ['JAVA_HOME'])/'bin/java'; cp = os.pathsep.join(str(bundle/entry) for entry in original['runtimeClasspathRelative'])
    snapshot=out/'environment.json'
    if ci.run([java,*ci.JVM_ARGS,'-cp',cp,'com.kotlinorm.benchmark.InspectEnvironment',snapshot],out/'environment.log',out): raise ValueError('Calibration environment inspection failed')
    validation=ci.read_json(gate/'validation-gate.json')
    if validation['status']!='PASS' or validation['bundleSha256']!=seal or ci.read_json(snapshot)!=validation['environment']: raise ValueError('Calibration environment differs from the correctness gate')
    planned=scenario(index,preset); raw=out/'calibration';raw.mkdir();ci.write_json(raw/'schedule.json',planned)
    findings=[];failures=[]
    for item in planned:
        kind,params=item['kind'],item['params'];name=ci.cell_name(item);target=raw/(name+'.json');log=raw/(name+'.log')
        benchmark='com.kotlinorm.benchmark.'+('ReadBenchmark.query' if kind=='read' else 'InsertBenchmark.insertTransaction')
        argv=[java,'-cp',cp,'org.openjdk.jmh.Main',benchmark,'-f','1','-foe','true','-t','1','-jvm',java,'-jvmArgs',' '.join(ci.JVM_ARGS),'-rf','json','-rff',target]
        for key,value in sorted(params.items()): argv+=['-p',f'{key}={value}']
        argv+=timing(kind,preset);code=ci.run(argv,log,out)
        status=dict(item,exitCode=code,status='FAIL',raw=str(target),**{key:manifest[key] for key in audit.IDENTITY if key!='executionStage'},
                    controllerGitSha=manifest['controllerGitSha'],protocolSha256=protocol_sha,classification='CALIBRATION_ONLY_NOT_FORMAL')
        finding=dict(cell=name,params=params,status='FAIL')
        try:
            data=ci.read_json(target)
            if code or len(data)!=1 or data[0]['params']!={key:str(value) for key,value in params.items()} or data[0]['primaryMetric']['scoreUnit']!='us/op' or data[0]['mode']!=('avgt' if kind=='read' else 'ss'): raise ValueError('Calibration JMH mode/parameters/unit mismatch')
            samples=data[0]['primaryMetric']['rawData']
            if len(samples)!=1 or len(samples[0])!=(10 if kind=='read' else 30) or any(not math.isfinite(value) or value<=0 for value in samples[0]): raise ValueError('Expected complete positive planned-formal measurements from one fork')
            observed=warmups(log.read_text())
            if len(observed)!=(5 if kind=='read' else 2000 if preset=='write-warm2000' else 10): raise ValueError('Incomplete observed planned-formal warmup evidence')
            with target.with_suffix('.csv').open('w',newline='') as handle:
                writer=csv.writer(handle);writer.writerow(['iteration','microsecondsPerOperation'])
                writer.writerows(enumerate(samples[0],1))
            status.update(status='PASS',rawSha256=ci.digest(target),csvSha256=ci.digest(target.with_suffix('.csv')))
            finding.update(status='PASS',rawSha256=status['rawSha256'],measurementUS=samples[0],warmupObservedFromLog=observed,**trends(samples[0]))
            finding['lastWarmupOverMeasuredMean']=observed[-1]['us']/finding['meanUS']
        except (ValueError,OSError,KeyError) as error:
            status['failure']=type(error).__name__+': '+str(error);finding['failure']=status['failure'];failures.append(name)
        status['logSha256']=ci.digest(log);finding['logSha256']=status['logSha256'];ci.write_json(raw/(name+'.status.json'),status);findings.append(finding)
    ci.verify(bundle,seal)
    ci.write_json(out/'calibration-review.json',dict(classification='CALIBRATION_ONLY_NOT_FORMAL',identity={key:manifest[key] for key in audit.IDENTITY},
        controllerGitSha=manifest['controllerGitSha'],originalProducerRunId=original['workflowRunId'],protocol=manifest['calibrationProtocol'],protocolSha256=protocol_sha,findings=findings,
        limitation='One fork per adapter/scenario diagnoses planned warmup and iteration trends; no formal rankings or five-block inference'))
    ci.write_json(out/'completion.json',dict(status='PASS' if not failures else 'PARTIAL',planned=6,failures=failures,classification='CALIBRATION_ONLY_NOT_FORMAL'))
    if failures: raise SystemExit(1)


def summarize(out, gate, observations):
    manifest=ci.read_json(out/'build-manifest.json');audit.verify_receipt(out,manifest,os.environ['GITHUB_RUN_ID'])
    gate_manifest=ci.read_json(gate/'build-manifest.json');audit.verify_receipt(gate,gate_manifest,os.environ['GITHUB_RUN_ID'])
    review=ci.read_json(out/'calibration-review.json');observations.mkdir(parents=True,exist_ok=False);index={}
    ci.write_json(observations/'build-manifest.json',manifest)
    notice_count=0
    for slot,original_finding in enumerate(review['findings']):
        finding=dict(original_finding)
        observed=finding.get('warmupObservedFromLog',[])
        if len(observed)>50:
            finding.pop('warmupObservedFromLog')
            finding.update(warmupCount=len(observed),warmupFirst3=observed[:3],warmupLast30=observed[-30:],
                           warmupSequenceSha256=__import__('hashlib').sha256(json.dumps(observed,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
                           fullWarmupEvidence='Complete sequence retained in audited calibration-review.json and logSha256-bound raw log')
        payload=dict(classification='CALIBRATION_ONLY_NOT_FORMAL',identity=review['identity'],controllerGitSha=review['controllerGitSha'],
                     originalProducerRunId=review['originalProducerRunId'],protocol=review['protocol'],protocolSha256=review['protocolSha256'],finding=finding,
                     reviewSha256=ci.digest(out/'calibration-review.json'),receiptSha256=ci.digest(out/audit.RECEIPT),
                     gateReceiptSha256=ci.digest(gate/audit.RECEIPT),environmentSha256=ci.digest(out/'environment.json'),
                     limitation=review['limitation'])
        path=observations/f'payload-{slot}.json';ci.write_json(path,payload);index[path.name]=ci.digest(path)
        segments=math.ceil(path.stat().st_size/2500)
        if segments>10: raise ValueError('Calibration payload exceeds ten notices per step')
        notice_count+=segments
    if notice_count>40: raise ValueError('Calibration summaries exceed the per-job notice budget')
    ci.write_json(observations/'index.json',index)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['freeze','prepare','run','summarize'])
    parser.add_argument('--run-id');parser.add_argument('--candidate-sha');parser.add_argument('--benchmark-sha');parser.add_argument('--seal')
    parser.add_argument('--preset',choices=['planned-formal','write-warm2000'],default='planned-formal')
    parser.add_argument('--plan',type=Path);parser.add_argument('--bundle',type=Path);parser.add_argument('--gate',type=Path);parser.add_argument('--group',type=int);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--observations',type=Path)
    args=parser.parse_args()
    if args.action=='freeze':
        transport.require_single_attempt();plan=transport.freeze_artifacts(args.run_id,args.benchmark_sha)
        ci.write_json(args.out,dict(reuseArtifacts=plan,expectedCandidateSha=args.candidate_sha,expectedBenchmarkSha=args.benchmark_sha,expectedSeal=args.seal,preset=args.preset))
    elif args.action=='prepare':
        frozen=ci.read_json(args.plan);prepare(frozen['reuseArtifacts'],frozen['expectedSeal'],frozen['expectedCandidateSha'],frozen['expectedBenchmarkSha'],args.out)
    elif args.action=='run':
        try: execute(args.bundle.resolve(),args.seal,args.gate,args.group,args.out.resolve(),args.preset)
        except Exception as error:
            if args.out.is_dir(): ci.write_json(args.out/'controller-failure.json',dict(type=type(error).__name__,message=str(error)))
            raise SystemExit('Calibration controller failed; inspect hash-audited evidence')
    else: summarize(args.out,args.gate,args.observations)

if __name__=='__main__':main()
