"""Standard-library-only API demo; capabilities never appear in command lines."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

KUBE = ['kubectl', '--context', os.environ.get('KUBE_CONTEXT', 'k3d-p2p-drive'),
        '-n', os.environ.get('NAMESPACE', 'p2p-drive')]
RELEASE = os.environ.get('RELEASE', 'tahoe')


def progress(message):
    print(f'[{time.strftime("%H:%M:%S")}] {message}', flush=True)


def k(*args):
    return subprocess.check_output(KUBE + list(args))


def eventually(check, description, timeout=120):
    progress(f'Waiting for {description} (timeout: {timeout}s)...')
    deadline = time.monotonic() + timeout
    next_update = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            value = check()
            if value:
                return value
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            pass
        if time.monotonic() >= next_update:
            progress(f'Still waiting for {description}...')
            next_update = time.monotonic() + 10
        time.sleep(2)
    raise RuntimeError('Timed out waiting for ' + description)


@contextmanager
def api():
    progress('Starting a private client port-forward...')
    # Let kubectl choose an unused local port and parse its non-secret output.
    with tempfile.TemporaryFile(mode='w+') as log:
        proc = subprocess.Popen(KUBE + ['port-forward', '--address', '127.0.0.1',
                                'pod/' + RELEASE + '-client-0', ':3456'],
                                stdout=log, stderr=log)
        try:
            def address():
                import re
                log.seek(0)
                match = re.search(r'Forwarding from 127\.0\.0\.1:(\d+)', log.read())
                if proc.poll() is not None:
                    raise RuntimeError('kubectl port-forward exited')
                return 'http://127.0.0.1:' + match[1] if match else None
            yield eventually(address, 'client port-forward', 30)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def request(base, path, data=None, method=None):
    req = urllib.request.Request(base + path, data=data, method=method)
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def connected(base):
    info = json.loads(request(base, '/?t=json'))
    return sum(server['connection_status'] == 'connected'
               for server in info['servers'])


def check(base, cap):
    path = '/uri/' + urllib.parse.quote(cap, safe='')
    return json.loads(request(base, path, b't=check&output=JSON&verify=true'))['results']


def upload(base, data):
    return request(base, '/uri', data, 'PUT').decode().strip()


def download(base, cap):
    return request(base, '/uri/' + urllib.parse.quote(cap, safe=''))


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def healthy_upload(base):
    eventually(lambda: connected(base) == 3, 'three connected storage servers')
    progress('Checking storage placement across agent nodes...')
    pods = json.loads(k('get', 'pods', '-l', 'app.kubernetes.io/instance=' + RELEASE +
                        ',tahoe-role=storage', '-o', 'json'))['items']
    require(len(pods) == 3, 'Expected exactly three storage pods')
    hosts = {pod['spec']['nodeName'] for pod in pods}
    require(len(hosts) == 3, 'Storage servers must occupy three distinct agent nodes')
    allowed = {node['metadata']['name'] for node in
               json.loads(k('get', 'nodes', '-o', 'json'))['items']
               if 'node-role.kubernetes.io/control-plane' not in node['metadata']['labels']}
    require(hosts <= allowed, 'A storage server is on a control-plane node')
    print('PASS: three storage servers placed on three distinct agent nodes')
    client = json.loads(k('get', 'pod', RELEASE + '-client-0', '-o', 'json'))
    progress('Checking that a storage pod cannot access the client HTTP API...')
    # Loopback access already succeeded above. The API must fail from a peer pod.
    probe = (
        'import socket,sys\n'
        'try:\n'
        '    socket.create_connection((sys.argv[1], 3456), timeout=3)\n'
        'except OSError:\n'
        '    sys.exit(0)\n'
        'sys.exit(1)\n'
    )
    k('exec', pods[0]['metadata']['name'], '--', 'python', '-c', probe,
      client['status']['podIP'])
    print('PASS: client API works through loopback forwarding and is unreachable from a storage pod')

    # Random 2 MiB input prevents literal-file encoding and deduplication.
    original = os.urandom(2 * 1024 * 1024)
    digest = hashlib.sha256(original).hexdigest()
    progress('Uploading 2 MiB of random data...')
    cap = upload(base, original)
    require(cap.startswith('URI:CHK:'), 'Expected an immutable erasure-coded CHK file')
    progress('Verifying erasure coding and share distribution...')
    healthy = check(base, cap)
    require(healthy['count-shares-needed'] == 2 and healthy['count-shares-expected'] == 3,
            'Encoding must be 2-of-3')
    require(healthy['count-shares-good'] == 3 and healthy['count-good-share-hosts'] == 3,
            'Expected three good shares on three servers')
    sharemap = healthy['sharemap']
    require(set(sharemap) == {'0', '1', '2'} and all(len(v) == 1 for v in sharemap.values())
            and len({v[0] for v in sharemap.values()}) == 3,
            'Share map must assign each share to a different server')
    print('PASS: Tahoe reports 2-of-3 encoding and one distinct share per server')
    progress('Downloading with all storage servers online and comparing SHA-256...')
    require(hashlib.sha256(download(base, cap)).hexdigest() == digest,
            'Healthy download SHA-256 mismatch')
    print('PASS: healthy download SHA-256 matches')
    return cap, digest


def recovery():
    progress(f'Starting recovery test: context={KUBE[2]}, namespace={KUBE[4]}, release={RELEASE}')
    with api() as base:
        cap, digest = healthy_upload(base)
    # Exercise every single-server outage, retaining each StatefulSet PVC.
    for index in range(3):
        name = f'{RELEASE}-storage-{index}'
        progress(f'Outage {index + 1}/3: recording {name} volume and identity...')
        pvc = 'data-' + name + '-0'
        before = json.loads(k('get', 'pvc', pvc, '-o', 'json'))
        identity = k('exec', name + '-0', '--', 'sha256sum', '/data/node/private/node.privkey')
        try:
            progress(f'Stopping {name} without deleting its PVC; waiting for pod removal...')
            k('scale', 'statefulset/' + name, '--replicas=0')
            k('wait', '--for=delete', 'pod/' + name + '-0', '--timeout=120s')
            # A fresh client process cannot serve data from a previous download's memory.
            progress('Restarting the client to clear in-memory state; waiting for readiness...')
            k('rollout', 'restart', 'statefulset/' + RELEASE + '-client')
            k('rollout', 'status', 'statefulset/' + RELEASE + '-client', '--timeout=180s')
            with api() as base:
                eventually(lambda: connected(base) == 2, 'two remaining connected servers')
                progress('Verifying exactly two shares remain reachable...')
                degraded = check(base, cap)
                require(degraded['count-shares-good'] == 2 and
                        degraded['count-good-share-hosts'] == 2,
                        'Degraded file must have exactly two reachable shares on two servers')
                progress(f'Downloading while {name} is offline and comparing SHA-256...')
                require(hashlib.sha256(download(base, cap)).hexdigest() == digest,
                        'Degraded download SHA-256 mismatch')
            after = json.loads(k('get', 'pvc', pvc, '-o', 'json'))
            require(before['metadata']['uid'] == after['metadata']['uid'] and
                    before['spec']['volumeName'] == after['spec']['volumeName'],
                    'Persistent volume changed during outage')
            print(f'PASS: {name} offline; two-share download SHA-256 matches; PVC retained')
        finally:
            progress(f'Restoring {name}; waiting for readiness...')
            k('scale', 'statefulset/' + name, '--replicas=1')
            k('rollout', 'status', 'statefulset/' + name, '--timeout=180s')
        with api() as base:
            eventually(lambda: connected(base) == 3, 'restored server connection')
            progress(f'Checking {name} retained its original share and identity...')
            require(check(base, cap)['count-shares-good'] == 3, 'Restored share missing')
        require(k('exec', name + '-0', '--', 'sha256sum', '/data/node/private/node.privkey')
                == identity, 'Storage identity changed after restart')
        print(f'PASS: {name} restored with the same identity and original share')
    print('PASS: all three single-server outages recovered; SHA-256 ' + digest)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('wait')
    sub.add_parser('recovery')
    up = sub.add_parser('upload')
    up.add_argument('file', type=Path)
    up.add_argument('capability_file', type=Path)
    down = sub.add_parser('download')
    down.add_argument('capability_file', type=Path)
    down.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.command == 'recovery':
        recovery()
        return
    with api() as base:
        if args.command == 'wait':
            eventually(lambda: connected(base) == 3, 'three connected storage servers')
            print('All three storage servers connected.')
        elif args.command == 'upload':
            # Exclusive creation avoids overwriting a capability or following a symlink.
            with args.capability_file.open('x') as out:
                out.write(upload(base, args.file.read_bytes()) + '\n')
            print('Uploaded; capability saved privately to ' + str(args.capability_file))
        else:
            args.output.write_bytes(download(base, args.capability_file.read_text().strip()))
            print('Downloaded to ' + str(args.output))


if __name__ == '__main__':
    try:
        main()
    except urllib.error.HTTPError as error:
        # HTTPError's normal string includes a URL containing the file capability.
        print(f'Tahoe API returned HTTP {error.code}; capability omitted.', file=sys.stderr)
        sys.exit(1)
