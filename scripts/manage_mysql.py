#!/usr/bin/env python3
"""Manage only this experiment's isolated MySQL instance; never the user's 3306 instance."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import subprocess
import time

MYSQL = Path('/usr/local/mysql/bin')
DATABASE = 'orm_benchmark_040'
PORT = 13307
MARKER = 'kronos-040-benchmark-instance-v1'


def private_write(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)
    os.chmod(path, 0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['initialize', 'start', 'stop', 'status'])
    parser.add_argument('--private-dir', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('BENCH_ALLOW_LOAD') != '1':
        parser.error('Wait for explicit main-task release before enabling load work with BENCH_ALLOW_LOAD=1')
    private = args.private_dir.resolve()
    benchmark_root = Path(__file__).resolve().parents[1]
    if private == benchmark_root or benchmark_root in private.parents:
        parser.error('Private directory must be outside the benchmark repository')
    private.mkdir(parents=True, exist_ok=True); os.chmod(private, 0o700)
    data, sock, pidfile = private / 'mysql-data', private / 'mysql.sock', private / 'mysql.pid'
    marker, secretfile = private / 'instance.json', private / 'database-secrets.json'
    if args.action == 'initialize':
        if marker.exists() or data.exists() or secretfile.exists():
            parser.error('Refusing to initialize an existing instance directory')
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', PORT)) == 0:
                parser.error('Port 13307 is occupied; no process was changed')
        data.mkdir(mode=0o700)
        with (private / 'initialize.log').open('w') as log:
            result = subprocess.run([MYSQL / 'mysqld', '--no-defaults', '--initialize-insecure', '--datadir=' + str(data)], stdout=log, stderr=subprocess.STDOUT)
        os.chmod(private / 'initialize.log', 0o600)
        if result.returncode:
            raise SystemExit('Initialization failed; inspect the private log; the partial datadir was preserved')
        config = dict(marker=MARKER, datadir=str(data), socket=str(sock), port=PORT, database=DATABASE, initialized=True, provisioned=False)
        private_write(marker, json.dumps(config, indent=2) + '\n')
        private_write(secretfile, json.dumps(dict(rootPassword=secrets.token_urlsafe(30), benchmarkPassword=secrets.token_urlsafe(30))) + '\n')
        print('Initialized an isolated datadir; no existing database was touched.')
        return
    if not marker.exists() or json.loads(marker.read_text()).get('marker') != MARKER:
        parser.error('Instance ownership marker missing or invalid')
    config = json.loads(marker.read_text())
    if config['datadir'] != str(data) or config['port'] != PORT or config['socket'] != str(sock):
        parser.error('Instance ownership/endpoint mismatch')
    if args.action == 'status':
        running = False
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text().strip()), 0); running = True
            except ProcessLookupError:
                pass
        print(json.dumps(dict(ownedInstance=True, port=PORT, running=running, provisioned=config['provisioned'])))
        return
    values = json.loads(secretfile.read_text())
    rootdefaults = private / 'root-client.cnf'
    private_write(rootdefaults, '[client]\nuser=root\npassword=' + values['rootPassword'] + '\nsocket=' + str(sock) + '\n')
    if args.action == 'stop':
        if not pidfile.exists():
            raise SystemExit('No owned PID file; nothing stopped')
        # mysqladmin authenticates through this dedicated socket, not TCP or the global PID list.
        result = subprocess.run([MYSQL / 'mysqladmin', '--defaults-file=' + str(rootdefaults), '--protocol=SOCKET', 'shutdown'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode:
            raise SystemExit('Owned instance shutdown failed; no global kill attempted')
        print('Stopped only the owned benchmark instance.')
        return
    if pidfile.exists():
        try:
            os.kill(int(pidfile.read_text().strip()), 0)
            parser.error('Owned PID is already running')
        except ProcessLookupError:
            parser.error('Stale PID file; inspect it before proceeding')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', PORT)) == 0:
            parser.error('Port 13307 occupied; no process changed')
    command = [MYSQL / 'mysqld', '--no-defaults', '--datadir=' + str(data), '--socket=' + str(sock), '--pid-file=' + str(pidfile),
               '--log-error=' + str(private / 'mysql-error.log'), '--port=' + str(PORT), '--bind-address=127.0.0.1', '--mysqlx=0',
               '--skip-name-resolve', '--skip-log-bin', '--innodb-buffer-pool-size=268435456', '--innodb-flush-log-at-trx-commit=1',
               '--sync-binlog=1', '--transaction-isolation=READ-COMMITTED', '--character-set-server=utf8mb4', '--collation-server=utf8mb4_bin',
               '--default-time-zone=+00:00']
    with (private / 'server-console.log').open('a') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    os.chmod(private / 'server-console.log', 0o600)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise SystemExit('Owned mysqld exited; inspect the private error log')
        if sock.exists():
            defaults = ['--defaults-file=' + str(rootdefaults)] if config['provisioned'] else ['--no-defaults', '--user=root', '--socket=' + str(sock)]
            ping = subprocess.run([MYSQL / 'mysqladmin', *defaults, '--protocol=SOCKET', 'ping'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if ping.returncode == 0:
                break
        time.sleep(0.2)
    else:
        process.terminate()
        raise SystemExit('Owned instance did not become ready within 60s')
    if not config['provisioned']:
        # Passwords travel only on stdin, never argv/log output. Generated values are URL-safe SQL literals.
        password = values['benchmarkPassword']
        sql = ("CREATE DATABASE " + DATABASE + " CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;\n"
               "CREATE USER 'orm_benchmark'@'127.0.0.1' IDENTIFIED BY '" + password + "';\n"
               "GRANT ALL ON " + DATABASE + ".* TO 'orm_benchmark'@'127.0.0.1';\n"
               "ALTER USER 'root'@'localhost' IDENTIFIED BY '" + values['rootPassword'] + "';\n")
        result = subprocess.run([MYSQL / 'mysql', '--no-defaults', '--user=root', '--protocol=SOCKET', '--socket=' + str(sock)], input=sql, text=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode:
            process.terminate()
            raise SystemExit('Private provisioning failed; partial state preserved for inspection')
        config['provisioned'] = True
        private_write(marker, json.dumps(config, indent=2) + '\n')
    private_write(private / 'server-command.json', json.dumps([str(a) for a in command], indent=2) + '\n')
    print('Owned MySQL ready on 127.0.0.1:13307; credentials remain private.')


if __name__ == '__main__':
    main()
