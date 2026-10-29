"""Shared formal protocol/context guard; runtime and controller sources remain distinct."""
from __future__ import annotations
import sys
sys.dont_write_bytecode = True
import argparse,hashlib,json,os,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FIELDS=('executionContextSha256','controllerGitSha','protocolSha256')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def load(path):return json.loads(path.read_text())
def save(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')

def protocol(context):
    if hashlib.sha256(context['protocolJSON'].encode()).hexdigest()!=context['protocolSha256']:raise ValueError('Static protocol bytes changed')
    result=json.loads(context['protocolJSON'])
    if result['schemaVersion']!=1 or result['classification']!='FORMAL' or (result['blocks'],result['forksPerCell'],result['expectedCells'],result['maxParallel'])!=(5,1,780,8):raise ValueError('Unregistered matrix')
    if context.get('schemaVersion')!=1:raise ValueError('Unknown execution context schema')
    for key,value in result['runtime'].items():
        if context['runtime'].get(key)!=value:raise ValueError('Protocol/runtime context mismatch: '+key)
    controller=context['controller']
    if controller['sourceFiles'].get(context['protocolFile'])!=context['protocolSha256']:raise ValueError('Static protocol is not bound to controller source snapshot')
    if canonical(controller['sourceFiles'])!=controller['sourceTreeSha256']:raise ValueError('Controller source tree digest mismatch')
    if Path(controller['snapshotFile']).name!=controller['snapshotFile'] or not controller['snapshotFile'].startswith('controller-source-') or not re.fullmatch('[0-9a-f]{64}',controller['snapshotSha256']):raise ValueError('Unsafe controller source snapshot')
    for name,digest in controller['sourceFiles'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or not re.fullmatch('[0-9a-f]{64}',digest):raise ValueError('Invalid controller source mapping')
    for kind in ['read','write']:
        values=result['timing'][kind];options=dict(zip(values[::2],values[1::2]));expected={'-bm','-tu','-wi','-i'}|({'-w','-r'} if kind=='read' else {'-bs','-wbs'})
        if len(values)%2 or len(options)!=len(values)//2 or set(options)!=expected or options['-bm']!=('avgt' if kind=='read' else 'ss') or options['-tu']!='us':raise ValueError('Unsupported timing options')
        if any(not re.fullmatch('[1-9][0-9]*',options[key]) for key in ['-wi','-i']):raise ValueError('Invalid iteration count')
        if kind=='read' and any(not re.fullmatch('[1-9][0-9]*s',options[key]) for key in ['-w','-r']):raise ValueError('Invalid duration')
        if kind=='write' and (options['-bs']!='1' or options['-wbs']!='1'):raise ValueError('Expected one transaction per single shot')
    return result

def identity(value):
    formal='executionContextSha256' in value or 'executionContext' in value or value.get('executionClassification')=='FORMAL'
    if not formal:return {}
    if not all(key in value for key in FIELDS):raise ValueError('Partial formal execution identity')
    if value.get('executionClassification')=='FORMAL' and 'executionContext' not in value:raise ValueError('Formal manifest requires its complete context')
    selected={key:value[key] for key in FIELDS}
    if not re.fullmatch('[0-9a-f]{40}',selected['controllerGitSha']) or any(not re.fullmatch('[0-9a-f]{64}',selected[key]) for key in FIELDS if key!='controllerGitSha'):raise ValueError('Malformed context identity')
    if 'executionContext' in value:
        context=value['executionContext'];protocol(context)
        if canonical(context)!=selected['executionContextSha256'] or context['controller']['gitSha']!=selected['controllerGitSha'] or context['protocolSha256']!=selected['protocolSha256']:raise ValueError('Context content differs from identity')
        for key in ['candidateGitSha','benchmarkGitSha','sourceSha256','bundleSha256','runtimeSha256']:
            if key in value and value[key]!=context['runtime'][key]:raise ValueError('Manifest runtime differs from context: '+key)
        for key,context_key in [('executionWorkflowRunId','measurementRunId'),('executionWorkflowRunAttempt','measurementRunAttempt')]:
            if key in value and str(value[key])!=str(context[context_key]):raise ValueError('Manifest execution run differs from context')

    return selected

def same(reference,value):
    if identity(reference)!=identity(value):raise ValueError('Controller/protocol execution context mismatch')

def read_plan(path,expected=None):
    plan=load(path);context=plan['executionContext'];protocol(context)
    if any(plan[key]!=context['runtime'][key] for key in ['candidateGitSha','benchmarkGitSha']):raise ValueError('Plan runtime aliases differ from context')
    if canonical(context)!=plan['executionContextSha256'] or (expected and expected!=plan['executionContextSha256']):raise ValueError('Plan differs from frozen context SHA')
    if context['measurementRunAttempt']!='1' or os.environ.get('GITHUB_RUN_ATTEMPT','1')!='1' or str(context['measurementRunId'])!=str(os.environ.get('GITHUB_RUN_ID',context['measurementRunId'])):raise ValueError('Foreign execution run/attempt')
    return plan

def bind(runtime,plan,seal=None):
    context=plan['executionContext'];settings=protocol(context)
    for key in ['candidateGitSha','benchmarkGitSha','sourceSha256']:
        if runtime[key]!=settings['runtime'][key]:raise ValueError('Runtime source differs: '+key)
    if str(runtime['workflowRunId'])!=settings['runtime']['producerRunId']:raise ValueError('Runtime producer differs')
    if runtime['runtimeSha256']!=context['runtime']['runtimeSha256'] or (seal is not None and seal!=settings['runtime']['bundleSha256']):raise ValueError('Runtime byte identity differs from execution context')
    value=dict(runtime,bundleSha256=settings['runtime']['bundleSha256'],executionContext=context,executionContextSha256=plan['executionContextSha256'],controllerGitSha=context['controller']['gitSha'],protocolSha256=context['protocolSha256'],executionClassification='FORMAL',executionWorkflowRunId=context['measurementRunId'],executionWorkflowRunAttempt='1')
    value.pop('versionAuditSnapshot',None)
    from run_experiment import catalog_versions
    value['catalogVersions']=catalog_versions(value.get('versionCatalogTOML',''))
    identity(value);return value

def install(directory,plan):
    save(directory/'execution-context.json',plan['executionContext']);(directory/'execution-protocol.json').write_text(plan['executionContext']['protocolJSON'])

def timing(manifest,kind):return protocol(manifest['executionContext'])['timing'][kind]

def validate_jmh(manifest,data,kind):
    if not identity(manifest):return
    values=timing(manifest,kind);options=dict(zip(values[::2],values[1::2]))
    if data.get('forks')!=1 or data.get('warmupIterations')!=int(options['-wi']) or data.get('measurementIterations')!=int(options['-i']):raise ValueError('Actual JMH forks/iterations differ from protocol')
    if len(data['primaryMetric']['rawData'])!=1 or len(data['primaryMetric']['rawData'][0])!=int(options['-i']):raise ValueError('Incomplete JMH samples')
    if kind=='write' and (data.get('warmupBatchSize')!=1 or data.get('measurementBatchSize')!=1):raise ValueError('SingleShot batch differs from protocol')
    if kind=='read' and any(data.get(key,'').replace(' ','')!=options[flag] for key,flag in [('warmupTime','-w'),('measurementTime','-r')]):raise ValueError('JMH duration differs from protocol')

def verify_snapshot(path,context):
    controller=context['controller']
    if sha(path)!=controller['snapshotSha256']:raise ValueError('Controller snapshot byte digest changed')
    entries={}
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            if not member.isfile() or member.name in entries or Path(member.name).is_absolute() or '..' in Path(member.name).parts:raise ValueError('Unsafe controller source snapshot entry')
            entries[member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    if entries!=controller['sourceFiles']:raise ValueError('Controller snapshot content differs from source map')

def runtime_source_snapshot(bundle,out):
    originals=list(bundle.glob('source-*.tar.gz'))
    if len(originals)!=1:raise ValueError('Expected one original runtime source archive')
    original=originals[0];target=out/(original.name.removesuffix('.tar.gz')+'-jvm.tar.gz');included={}
    directories={'src','gradle','benchmark-convention','jimmer-benchmark','jpa-benchmark','kronos-benchmark','ktorm-benchmark','mybatis-benchmark'}
    root_files={'build.gradle.kts','settings.gradle.kts','libs.versions.toml','gradle.properties','gradlew','gradlew.bat','gradle.lockfile'}
    with tarfile.open(original) as source,tarfile.open(target,'w:gz') as destination:
        for member in source.getmembers():
            path=Path(member.name)
            if path.is_absolute() or '..' in path.parts or not member.isfile():raise ValueError('Unsafe original source archive')
            if not ((len(path.parts)==1 and path.name in root_files) or (len(path.parts)>1 and path.parts[0] in directories)):continue
            content=source.extractfile(member).read();included[member.name]=hashlib.sha256(content).hexdigest()
            import io
            destination.addfile(member,io.BytesIO(content))
    if not included:raise ValueError('Original archive contains no JVM source/build inputs')
    save(out/'runtime-source-manifest.json',dict(originalArchiveSha256=sha(original),publishedArchive=target.name,publishedArchiveSha256=sha(target),includedFiles=included,scope='JVM source and build inputs; original immutable runtime provenance remains unchanged'))

def controller_files():
    names=subprocess.check_output(['git','ls-files','--','.github/workflows','scripts','config','README.md'],cwd=ROOT,text=True).splitlines()
    return {name:sha(ROOT/name) for name in sorted(names)}

def verify_controller(plan):
    expected=plan['executionContext']['controller'];head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if head!=expected['gitSha'] or os.environ.get('GITHUB_SHA',head)!=head or controller_files()!=expected['sourceFiles']:raise ValueError('Executing controller source differs')

def prepare(plan_path,out,expected=None):
    from calibration import prepare as prepare_runtime
    plan=read_plan(plan_path,expected);verify_controller(plan);settings=protocol(plan['executionContext'])
    prepare_runtime(plan['reuseArtifacts'],settings['runtime']['bundleSha256'],settings['runtime']['candidateGitSha'],settings['runtime']['benchmarkGitSha'],out)
    bind(load(out/'runtime-bundle/build-manifest.json'),plan)
    if sha(out/'runtime-bundle/expected-schedule.json')!=settings['caseScheduleSha256']:raise ValueError('Original schedule differs')

def freeze(protocol_path,expected_protocol,expected_controller,out):
    protocol_path=protocol_path.resolve()
    protocol_path.relative_to(ROOT)  # Reject external paths before reading protocol bytes.
    from calibration import prepare as prepare_runtime
    from artifact_transport import freeze_artifacts,require_single_attempt
    require_single_attempt()
    if sha(protocol_path)!=expected_protocol:raise ValueError('Protocol differs from explicitly expected SHA')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if head!=expected_controller or os.environ['GITHUB_SHA']!=expected_controller:raise ValueError('Controller differs from explicitly expected SHA')
    text=protocol_path.read_text();settings=json.loads(text);transport=freeze_artifacts(settings['runtime']['producerRunId'],settings['runtime']['benchmarkGitSha']);out.mkdir(parents=True,exist_ok=False)
    prepare_runtime(transport,settings['runtime']['bundleSha256'],settings['runtime']['candidateGitSha'],settings['runtime']['benchmarkGitSha'],out/'verified-original')
    runtime=load(out/'verified-original/runtime-bundle/build-manifest.json');schedule=out/'verified-original/runtime-bundle/expected-schedule.json'
    if sha(schedule)!=settings['caseScheduleSha256']:raise ValueError('Registered original schedule differs')
    files=controller_files();archive=out/('controller-source-'+head[:16]+'.tar.gz')
    with tarfile.open(archive,'w:gz') as stream:
        for name in files:stream.add(ROOT/name,arcname=name,recursive=False)
    context=dict(schemaVersion=1,runtime=dict(settings['runtime'],runtimeSha256=runtime['runtimeSha256']),controller=dict(gitSha=head,sourceFiles=files,sourceTreeSha256=canonical(files),snapshotFile=archive.name,snapshotSha256=sha(archive)),protocolJSON=text,protocolFile=str(protocol_path.relative_to(ROOT)),protocolSha256=sha(protocol_path),measurementRunId=os.environ['GITHUB_RUN_ID'],measurementRunAttempt='1')
    protocol(context);plan=dict(candidateGitSha=runtime['candidateGitSha'],benchmarkGitSha=runtime['benchmarkGitSha'],workflowRunAttempt='1',reuseArtifacts=transport,executionContext=context,executionContextSha256=canonical(context));bind(runtime,plan);save(out/'execution-plan.json',plan)
    matrix=dict(include=[dict(group=group,block=block) for group in sorted({item['group'] for item in load(schedule)}) for block in range(1,6)])
    if len(matrix['include'])!=40:raise ValueError('Expected forty paired shards')
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as handle:
        for key,value in dict(context_sha=plan['executionContextSha256'],matrix=json.dumps(matrix,separators=(',',':')),seal=settings['runtime']['bundleSha256'],mysql_image=runtime['mysqlImage']).items():handle.write(key+'='+value+'\n')
    print('Frozen execution context '+plan['executionContextSha256'])

def inspect_original_schema(protocol_path,out):
    from artifact_transport import freeze_observation,download_one
    from secret_audit import verify_receipt
    settings=load(protocol_path);origin=settings['runtime']
    plan=freeze_observation(origin['producerRunId'],origin['candidateGitSha'],origin['benchmarkGitSha'],'pilot')
    download_one(plan['artifact'],out)
    pilot=out/'pilot';manifest=load(pilot/'build-manifest.json')
    if any(manifest[key]!=origin[key] for key in ['candidateGitSha','benchmarkGitSha','sourceSha256','bundleSha256']):raise ValueError('Original schema probe source mismatch')
    verify_receipt(pilot,manifest,origin['producerRunId'])
    headers={}
    for kind in ['read','write']:
        statuses=sorted((pilot/'pilot').glob(kind+'-*.status.json'))
        if not statuses:raise ValueError('Original schema probe missing workload')
        status=load(statuses[0]);raw=pilot/'pilot'/Path(status['raw']).name
        if sha(raw)!=status['rawSha256']:raise ValueError('Original schema probe raw hash mismatch')
        data=load(raw)[0]
        keys=['jmhVersion','mode','forks','warmupIterations','warmupTime','warmupBatchSize','measurementIterations','measurementTime','measurementBatchSize']
        header={key:data[key] for key in keys}
        if header['forks']!=1 or header['jmhVersion']!='1.37' or header['warmupBatchSize']!=1 or header['measurementBatchSize']!=1:raise ValueError('Unexpected actual JMH header schema')
        if (header['warmupIterations'],header['measurementIterations'])!=((2,3) if kind=='read' else (5,5)):raise ValueError('Original pilot iteration evidence differs')
        if kind=='read' and (header['warmupTime'].replace(' ',''),header['measurementTime'].replace(' ',''))!=('1s','1s'):raise ValueError('Actual time representation changed')
        headers[kind]=dict(header=header,rawSha256=sha(raw))
    message=json.dumps(dict(originalRunId=origin['producerRunId'],runtimeBenchmarkGitSha=origin['benchmarkGitSha'],candidateGitSha=origin['candidateGitSha'],artifact=plan['artifact'],receiptSha256=sha(pilot/'secret-audit.json'),headers=headers),sort_keys=True)
    if len(message.encode())>3000:raise ValueError('Header schema diagnostic exceeds safe API limit')
    print('::notice title=Audited original JMH header schema::'+message.replace('%','%25'))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['freeze','prepare','inspect-schema']);parser.add_argument('--protocol',type=Path);parser.add_argument('--expected-protocol');parser.add_argument('--expected-controller');parser.add_argument('--plan',type=Path);parser.add_argument('--expected-context');parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    if args.action=='freeze':freeze(args.protocol,args.expected_protocol,args.expected_controller,args.out)
    elif args.action=='prepare':prepare(args.plan,args.out,args.expected_context)
    else:inspect_original_schema(args.protocol,args.out)
