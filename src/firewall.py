#!/usr/bin/env python3
"""Fail-closed IPv4 firewall for shared Docker network namespace.
IPv6 disabled via ip6tables. Numeric IPv4 remotes required to avoid DNS bootstrap leaks.
"""
import ipaddress
import os
import re
import shlex
import subprocess
from pathlib import Path


def run(*args):
    subprocess.run(args, check=True)


def parse_csv(name):
    return [x.strip() for x in os.getenv(name, '').split(',') if x.strip()]


def ports(name):
    result = []
    for item in parse_csv(name):
        if not item.isdecimal() or not 1 <= int(item) <= 65535:
            raise ValueError(f'Invalid {name} port: {item}')
        result.append(str(int(item)))
    return result


def endpoints(path):
    remotes = []
    proto = 'udp'
    port_default = '1194'
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith(('#', ';', '<')):
            continue
        parts = shlex.split(line, comments=True)
        if not parts:
            continue
        if parts[0] == 'proto' and len(parts) > 1:
            proto = parts[1]
        elif parts[0] == 'port' and len(parts) > 1:
            port_default = parts[1]
        elif parts[0] == 'remote' and len(parts) > 1:
            ip = ipaddress.ip_address(parts[1])
            if ip.version != 4:
                raise ValueError('Only numeric IPv4 remote endpoints supported in v0.1')
            port = parts[2] if len(parts) > 2 else port_default
            protocol = parts[3] if len(parts) > 3 else proto
            protocol = 'tcp' if protocol.startswith('tcp') else 'udp' if protocol.startswith('udp') else ''
            if not protocol or not port.isdecimal() or not 1 <= int(port) <= 65535:
                raise ValueError('Unsupported endpoint protocol/port')
            remotes.append((str(ip), str(int(port)), protocol))
    if not remotes:
        raise ValueError('No numeric IPv4 remote in .ovpn; use provider IP endpoint for fail-closed startup')
    return remotes



def lan_routes(lans, gateway, iface='eth0'):
    """Add narrow return routes, never a default-route bypass."""
    if not lans:
        return
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}', iface):
        raise ValueError('Invalid LAN interface')
    if gateway:
        gw = ipaddress.ip_address(gateway)
        if gw.version != 4 or gw.is_loopback or gw.is_multicast or gw.is_unspecified:
            raise ValueError('LAN_GATEWAY must be a usable IPv4 address')
        gateway = str(gw)
    else:
        # Read the original underlay default route (before OpenVPN starts).
        result = subprocess.run(['ip', '-4', 'route', 'show', 'default', 'dev', iface],
                                check=True, capture_output=True, text=True)
        matches = re.findall(r'\bvia\s+(\d+\.\d+\.\d+\.\d+)', result.stdout)
        if not matches:
            raise ValueError('No underlay default gateway; set LAN_GATEWAY explicitly')
        gateway = str(ipaddress.IPv4Address(matches[0]))
    # The next hop must be directly reachable via the underlay interface.
    result = subprocess.run(['ip', '-4', 'route', 'get', gateway],
                            check=True, capture_output=True, text=True)
    if not re.search(r'\bdev\s+' + re.escape(iface) + r'\b', result.stdout):
        raise ValueError(f'LAN_GATEWAY {gateway} is not reachable via {iface}')
    for cidr in lans:
        net = ipaddress.IPv4Network(cidr)
        if net.prefixlen == 0:
            raise ValueError('LAN_CIDRS must not include 0.0.0.0/0')
        if net.is_multicast or net.is_loopback or net.is_link_local or net.is_unspecified:
            raise ValueError(f'Unsafe LAN_CIDRS network: {cidr}')
        # Connected subnets are already routed directly and should not be overridden.
        current = subprocess.run(['ip', '-4', 'route', 'get', str(net.network_address)],
                                 check=True, capture_output=True, text=True)
        if re.search(r'\bdev\s+' + re.escape(iface) + r'\b', current.stdout) and ' via ' not in current.stdout:
            continue
        run('ip', '-4', 'route', 'replace', str(net), 'via', gateway, 'dev', iface)
    print(f'LAN return routes active via {gateway} dev {iface}', flush=True)

def main():
    config = os.environ['VPN_CONFIG']
    eps = endpoints(config)
    lans = [str(ipaddress.ip_network(c, strict=False)) for c in parse_csv('LAN_CIDRS')]
    if any(ipaddress.ip_network(c).version != 4 for c in lans):
        raise ValueError('Only IPv4 LAN CIDRs supported')
    tcp = ports('LAN_TCP_PORTS')
    udp = ports('LAN_UDP_PORTS')
    tun = os.environ['VPN_TUN']
    iface = os.getenv('LAN_INTERFACE', 'eth0')
    gateway = os.getenv('LAN_GATEWAY', '').strip()
    if any(ipaddress.IPv4Network(c).prefixlen == 0 for c in lans):
        raise ValueError('LAN_CIDRS must not contain a default route')
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,15}', tun):
        raise ValueError('Invalid tunnel interface')
    # Set policies FIRST; flush afterward so previous rules cannot allow leaks.
    for binary in ('iptables', 'ip6tables'):
        for chain in ('INPUT', 'OUTPUT', 'FORWARD'):
            run(binary, '-P', chain, 'DROP')
        run(binary, '-F')
        run(binary, '-X')
        run(binary, '-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
        run(binary, '-A', 'OUTPUT', '-o', 'lo', '-j', 'ACCEPT')
    # Block Docker embedded DNS proxy before loopback accept: otherwise it can proxy queries outside the VPN.
    run('iptables', '-I', 'OUTPUT', '1', '-d', '127.0.0.11', '-p', 'udp', '--dport', '53', '-j', 'REJECT')
    run('iptables', '-I', 'OUTPUT', '1', '-d', '127.0.0.11', '-p', 'tcp', '--dport', '53', '-j', 'REJECT')
    run('iptables', '-A', 'INPUT', '-m', 'conntrack', '--ctstate', 'ESTABLISHED,RELATED', '-j', 'ACCEPT')
    # Do not permit arbitrary pre-existing eth0 connections via conntrack.
    run('iptables', '-A', 'OUTPUT', '-o', tun, '-m', 'conntrack', '--ctstate', 'ESTABLISHED,RELATED', '-j', 'ACCEPT')
    run('iptables', '-A', 'OUTPUT', '-o', tun, '-j', 'ACCEPT')
    run('iptables', '-A', 'INPUT', '-i', tun, '-j', 'ACCEPT')
    # OpenVPN handshake is the only allowed external non-tunnel traffic.
    for host, port, proto in eps:
        run('iptables', '-A', 'OUTPUT', '-o', 'eth0', '-d', host, '-p', proto, '--dport', port, '-j', 'ACCEPT')
    # Routes must exist before OpenVPN installs split default routes through tun0.
    lan_routes(lans, gateway, iface)
    # Local network bypass is explicit, restricted to configured CIDRs.
    for cidr in lans:
        run('iptables', '-A', 'OUTPUT', '-o', iface, '-d', cidr, '-m', 'conntrack', '--ctstate', 'ESTABLISHED,RELATED', '-j', 'ACCEPT')
        for port in tcp:
            run('iptables', '-A', 'INPUT', '-i', iface, '-s', cidr, '-p', 'tcp', '--dport', port, '-m', 'conntrack', '--ctstate', 'NEW', '-j', 'ACCEPT')
        for port in udp:
            run('iptables', '-A', 'INPUT', '-i', iface, '-s', cidr, '-p', 'udp', '--dport', port, '-m', 'conntrack', '--ctstate', 'NEW', '-j', 'ACCEPT')
    print(f'Firewall active: {len(eps)} VPN endpoint(s), {len(lans)} LAN CIDR(s), IPv6 blocked', flush=True)


if __name__ == '__main__':
    main()
