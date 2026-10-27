#!/usr/bin/env python3
"""Resolve a requested Kronos branch/tag/SHA exactly once before the producer starts."""
import json
import os
from pathlib import Path
import re
from urllib.parse import quote
from urllib.request import Request, urlopen

from ci_experiment import GROUPS


ref = os.environ['REQUESTED_KRONOS_REF']
if not ref or ref.startswith('-') or len(ref) > 200 or any(c.isspace() for c in ref):
    raise ValueError('Invalid Kronos ref')
headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}
if os.environ.get('GH_TOKEN'):
    headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
url = 'https://api.github.com/repos/Kronos-orm/Kronos-orm/commits/' + quote(ref, safe='')
with urlopen(Request(url, headers=headers), timeout=60) as response:
    sha = json.load(response)['sha']
if not re.fullmatch('[0-9a-f]{40}', sha):
    raise ValueError('GitHub did not return an immutable commit SHA')
expected = os.environ.get('EXPECTED_KRONOS_SHA', '')
if expected and expected != sha:
    raise ValueError('Resolved branch/tag differs from explicitly approved SHA')
mode = os.environ['BENCHMARK_MODE']
if mode in {'pilot', 'measure'} and not re.fullmatch('[0-9a-f]{40}', expected):
    raise ValueError('Pilot and formal matrix require the exact expected Kronos source SHA')
if mode == 'measure' and not re.fullmatch('[1-9][0-9]*', os.environ.get('PRODUCER_RUN_ID', '')):
    raise ValueError('Formal matrix must reuse a reviewed pilot run; rebuilding changes the reviewed bytes')
image = json.loads(Path('reports/kronos-0.4.0/versions/upstream/mysql-ci-image.json').read_text())
frozen = dict(candidateGitSha=sha, requestedKronosRef=ref, kronosVersion='0.4.0', kotlinVersion='2.4.21',
              benchmarkGitSha=os.environ['GITHUB_SHA'], workflowRunId=os.environ['GITHUB_RUN_ID'],
              workflowRunAttempt=os.environ['GITHUB_RUN_ATTEMPT'], mode=mode,
              javaDistribution='temurin', javaVersion='21.0.10+7', runnerLabel='ubuntu-24.04',
              mysqlImage=image['tag'] + '@' + image['digest'],
              environmentScope='CI runner VMs; paired ORM comparisons share a VM and DB within each case/block')
Path('frozen.json').write_text(json.dumps(frozen, indent=2, sort_keys=True) + '\n')
matrix = dict(include=[dict(group=g, block=b) for g in GROUPS for b in range(1, 6)])
with Path(os.environ['GITHUB_OUTPUT']).open('a') as handle:
    for key, value in dict(sha=sha, mysql_image=frozen['mysqlImage'], matrix=json.dumps(matrix, separators=(',', ':'))).items():
        handle.write(key + '=' + value + '\n')
print('Frozen Kronos source:', sha)
