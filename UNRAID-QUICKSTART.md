# Unraid quick start

See [README.md](README.md) for full deployment, security limitations, and cross-VLAN troubleshooting.

1. Copy `unraid/my-vpn-gateway.xml` into `/boot/config/plugins/dockerMan/templates-user/my-vpn-gateway.xml`.
2. Configure OpenVPN and select Custom `eth0.72` with a fixed IP if using macvlan.
3. For cross-VLAN Syncthing GUI access from `10.7.7.0/24`, set `LAN_CIDRS=10.7.7.0/24`, `LAN_TCP_PORTS=8384`, and optionally `LAN_GATEWAY=10.6.72.1`.
4. Attach Syncthing with Network Type Container -> vpn-gateway. Open `http://10.6.72.10:8384` from an authorized client.
5. Validate VPN kill switch and return route before production use.
