#!/bin/sh
set -eu
TUN="${VPN_TUN:-tun0}"
ip -4 addr show dev "$TUN" 2>/dev/null | grep -q 'inet ' || exit 1
ip -4 route show | grep -Eq "(^default .*dev ${TUN}( |$)|^0\.0\.0\.0/1 .*dev ${TUN}( |$))" || exit 1
ip -4 route show | grep -Eq "(^default .*dev ${TUN}( |$)|^128\.0\.0\.0/1 .*dev ${TUN}( |$))" || exit 1
exit 0
