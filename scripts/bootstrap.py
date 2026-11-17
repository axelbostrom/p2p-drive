"""Copy the introducer FURL to the API server without exposing it in logs."""
import base64
import json
import os
import subprocess
import time

kubectl = ['kubectl', '--context', os.environ['KUBE_CONTEXT'], '-n', os.environ['NAMESPACE']]
for attempt in range(60):
    result = subprocess.run(kubectl + ['exec', os.environ['RELEASE'] + '-introducer-0', '--',
                            'cat', '/data/node/private/introducer.furl'],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode == 0 and result.stdout.strip().startswith(b'pb://'):
        break
    time.sleep(1)
else:
    raise SystemExit('Introducer did not produce a FURL within 60 seconds')
secret = {'apiVersion': 'v1', 'kind': 'Secret',
          'metadata': {'name': 'tahoe-introducer'}, 'type': 'Opaque',
          'data': {'introducer.furl': base64.b64encode(result.stdout.strip()).decode()}}
subprocess.run(kubectl + ['apply', '-f', '-'], input=json.dumps(secret).encode(), check=True,
               stdout=subprocess.DEVNULL)
print('Introducer Secret synchronized (value hidden).')
