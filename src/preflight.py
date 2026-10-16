#!/usr/bin/env python3
"""Validate local OpenVPN files without printing key material."""
import os, shlex, pathlib, sys
cfg = pathlib.Path(os.environ['VPN_CONFIG']).resolve()
base = cfg.parent
refs = {'ca','cert','key','tls-auth','tls-crypt','tls-crypt-v2','pkcs12','secret','crl-verify'}
inline = set()
lines = cfg.read_text().splitlines()
for line in lines:
    x = line.strip().lower()
    if x.startswith('<') and x.endswith('>') and not x.startswith('</'):
        inline.add(x[1:-1])
for raw in lines:
    line = raw.strip()
    if not line or line.startswith(('#',';','<')):
        continue
    try: parts = shlex.split(line, comments=True)
    except ValueError as exc: sys.exit(f'ERROR: invalid OpenVPN config syntax: {exc}')
    if not parts: continue
    key = parts[0].lower()
    if key in refs and len(parts)>1 and key not in inline:
        target = pathlib.Path(parts[1]); target = target if target.is_absolute() else base/target
        if not target.is_file(): sys.exit(f'ERROR: missing {key} file: {target}')
    if key == 'auth-user-pass' and len(parts)==1 and not os.getenv('VPN_AUTH_FILE'):
        sys.exit('ERROR: auth-user-pass requires VPN_AUTH_FILE (interactive prompts unsupported)')
if os.getenv('VPN_AUTH_FILE') and not pathlib.Path(os.environ['VPN_AUTH_FILE']).is_file():
    sys.exit('ERROR: VPN_AUTH_FILE is set but unreadable')
print('OpenVPN configuration preflight passed', flush=True)
