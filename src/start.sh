#!/bin/sh
set -eu
: "${VPN_CONFIG:=/config/openvpn/client.ovpn}"
: "${VPN_AUTH_FILE:=}"
: "${VPN_TUN:=tun0}"
: "${RECONNECT_DELAY:=5}"
: "${DNS_SERVERS:=1.1.1.1,9.9.9.9}"
export VPN_CONFIG VPN_AUTH_FILE VPN_TUN RECONNECT_DELAY DNS_SERVERS
[ -r "$VPN_CONFIG" ] || { echo "ERROR: OpenVPN config unreadable: $VPN_CONFIG" >&2; exit 1; }
# Fail-closed policy must precede any external traffic.
python3 /opt/gateway/firewall.py
python3 /opt/gateway/preflight.py
# Replace Docker/host DNS settings, including the embedded 127.0.0.11 resolver,
# with explicit numeric DNS servers. Firewall only permits these through tun0.
python3 /opt/gateway/dns.py
cd "$(dirname "$VPN_CONFIG")" || exit 1
while :; do
  echo 'Starting OpenVPN (firewall remains enforced)'
  if [ -n "$VPN_AUTH_FILE" ]; then
    openvpn --cd "$(dirname "$VPN_CONFIG")" --config "$VPN_CONFIG" --auth-user-pass "$VPN_AUTH_FILE" --dev "$VPN_TUN" --script-security 1 --pull-filter ignore 'redirect-gateway ipv6' --pull-filter ignore 'route-ipv6' || true
  else
    openvpn --cd "$(dirname "$VPN_CONFIG")" --config "$VPN_CONFIG" --dev "$VPN_TUN" --script-security 1 --pull-filter ignore 'redirect-gateway ipv6' --pull-filter ignore 'route-ipv6' || true
  fi
  echo 'OpenVPN stopped; kill switch remains active' >&2
  sleep "$RECONNECT_DELAY"
done
