#!/usr/bin/env python3
"""Provision only an ephemeral CI-owned container; never run this on the local workstation."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop'])
    parser.add_argument('--image')
    args = parser.parse_args()
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        parser.error('This command is restricted to an explicitly dispatched CI job')
    name = 'benchmark-mysql'
    label = 'org.kotlinorm.benchmark.run=' + os.environ['GITHUB_RUN_ID']
    if args.action == 'stop':
        probe = subprocess.run(['docker', 'inspect', name, '--format', '{{index .Config.Labels "org.kotlinorm.benchmark.run"}}'], capture_output=True, text=True)
        if probe.returncode == 0 and probe.stdout.strip() == os.environ['GITHUB_RUN_ID']:
            subprocess.run(['docker', 'rm', '-f', name], check=True, stdout=subprocess.DEVNULL)
        return
    if not args.image or '@sha256:' not in args.image:
        parser.error('Pin the MySQL image by registry digest')
    if subprocess.run(['docker', 'inspect', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        parser.error('An existing container owns the selected name; nothing was changed')
    private = Path(os.environ['RUNNER_TEMP']) / 'benchmark-private'
    private.mkdir(mode=0o700, exist_ok=False)
    password = secrets.token_urlsafe(32)
    envfile = private / 'mysql.env'
    with os.fdopen(os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as handle:
        handle.write(f'MYSQL_DATABASE=orm_benchmark_040\nMYSQL_USER=orm_benchmark\nMYSQL_PASSWORD={password}\nMYSQL_ROOT_PASSWORD={secrets.token_urlsafe(32)}\n')
    passwordfile = private / 'benchmark-password'
    with os.fdopen(os.open(passwordfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as handle:
        handle.write(password)
    # No secret appears in argv, logs, artifact output, or GITHUB_ENV: only the private file path.
    with Path(os.environ['GITHUB_ENV']).open('a') as handle:
        handle.write('BENCH_DB_PASSWORD_FILE=' + str(passwordfile) + '\n')
    command = ['docker', 'run', '--detach', '--name', name, '--label', label, '--env-file', str(envfile),
               '--publish', '127.0.0.1:13307:3306', args.image,
               '--mysqlx=0', '--skip-name-resolve', '--skip-log-bin', '--innodb-buffer-pool-size=268435456',
               '--innodb-flush-log-at-trx-commit=1', '--sync-binlog=1', '--transaction-isolation=READ-COMMITTED',
               '--character-set-server=utf8mb4', '--collation-server=utf8mb4_bin', '--default-time-zone=+00:00']
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
    env = dict(os.environ, MYSQL_PWD=password)
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        code = subprocess.run(['docker', 'exec', '--env', 'MYSQL_PWD', name, 'mysql', '--protocol=TCP', '-h127.0.0.1', '-uorm_benchmark', '--database=orm_benchmark_040', '--execute=SELECT 1'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        if code == 0:
            print(json.dumps(dict(status='READY', image=args.image, port=13307, storage='fresh ephemeral container volume')))
            return
        time.sleep(2)
    raise RuntimeError('Dedicated CI MySQL did not become ready; no measurements were started')


if __name__ == '__main__':
    main()
