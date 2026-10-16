#!/usr/bin/env python3
"""Configure DNS over the tunnel, never via Docker's loopback resolver."""
import ipaddress, os, pathlib, sys
servers = [x.strip() for x in os.getenv('DNS_SERVERS','1.1.1.1,9.9.9.9').split(',') if x.strip()]
if not servers: sys.exit('ERROR: DNS_SERVERS must contain numeric IPv4 addresses')
for server in servers:
    if ipaddress.ip_address(server).version != 4: sys.exit('ERROR: DNS_SERVERS only supports IPv4')
path = pathlib.Path('/etc/resolv.conf')
try:
    path.write_text(''.join(f'nameserver {s}\n' for s in servers) + 'options timeout:2 attempts:2\n')
except OSError as exc:
    sys.exit(f'ERROR: cannot configure DNS; refusing to start: {exc}')
print('DNS configured for tunnel-only resolution', flush=True)
