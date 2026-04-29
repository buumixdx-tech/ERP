#!/usr/bin/env python3
import urllib.request
import json
import sys
sys.path.insert(0, '/opt/cs-server')

# 1. Login
data = json.dumps({'username': 'admin', 'password': 'admin123'}).encode()
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/login', data=data, headers={'Content-Type': 'application/json'})
resp = urllib.request.urlopen(req, timeout=10)
result = json.loads(resp.read().decode())
print('1. Login:', 'SUCCESS' if result.get('success') else 'FAILED')
token = result.get('data', {}).get('access_token', '')
print('   Token:', token[:40], '...')

# 2. Test /me
req2 = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/me', headers={'Authorization': 'Bearer ' + token})
try:
    resp2 = urllib.request.urlopen(req2, timeout=10)
    me = json.loads(resp2.read().decode())
    print('2. /me:', 'SUCCESS' if me.get('success') else 'FAILED', '-', me.get('data', {}).get('username'))
except urllib.error.HTTPError as e:
    print('2. /me: FAILED -', e.code, e.read().decode())

# 3. Test /vc/list WITHOUT token
req3 = urllib.request.Request('http://127.0.0.1:8000/api/v1/vc/list')
try:
    resp3 = urllib.request.urlopen(req3, timeout=10)
    vcs = json.loads(resp3.read().decode())
    print('3. /vc/list (no token): SHOULD FAIL BUT GOT', vcs.get('success', False))
except urllib.error.HTTPError as e:
    print('3. /vc/list (no token): CORRECTLY BLOCKED -', e.code)

# 4. Test /vc/list WITH token
req4 = urllib.request.Request('http://127.0.0.1:8000/api/v1/vc/list', headers={'Authorization': 'Bearer ' + token})
try:
    resp4 = urllib.request.urlopen(req4, timeout=10)
    vcs = json.loads(resp4.read().decode())
    print('4. /vc/list (with token):', 'SUCCESS' if vcs.get('success') else 'FAILED', '- Total:', vcs.get('data', {}).get('total', 0))
except urllib.error.HTTPError as e:
    print('4. /vc/list (with token): FAILED -', e.code, e.read().decode())

# 5. Test /api/v1/master/customers (protected endpoint)
req5 = urllib.request.Request('http://127.0.0.1:8000/api/v1/master/customers', headers={'Authorization': 'Bearer ' + token})
try:
    resp5 = urllib.request.urlopen(req5, timeout=10)
    customers = json.loads(resp5.read().decode())
    print('5. /master/customers (with token):', 'SUCCESS' if customers.get('success') else 'FAILED')
except urllib.error.HTTPError as e:
    print('5. /master/customers: FAILED -', e.code, e.read().decode())

print()
print('=== All Tests Completed ===')
