# Unraid OpenVPN Gateway

**Release candidate 1.0.0-rc1 — not yet production-validated.** An OpenVPN-only Docker gateway for Unraid (primary) and Compose (secondary). Other containers share its network namespace using Unraid **Network Type → Container → vpn-gateway**.

## What is supported
- Standard `.ovpn` files with numeric IPv4 `remote` endpoints (UDP/TCP).
- Certificate-only authentication (`ca`, `cert`, `key`, `tls-auth`, `tls-crypt`), external files and inline certificates.
- Optional `VPN_AUTH_FILE` for username/password profiles; leave blank for certificate-only.
- Default-deny IPv4/IPv6 iptables firewall, restricted VPN endpoint egress, tunnel-only DNS configuration, configurable LAN WebUI access.
- Automatic OpenVPN retry, Docker health check, Unraid XML and Compose.

## Limitations and security model
- **Only numeric IPv4 `remote` addresses** are supported; hostname resolution before tunnel establishment is deliberately disabled.
- The firewall restricts ordinary traffic to the tunnel and VPN endpoint, but containers sharing the namespace can potentially contact the permitted VPN endpoint directly. Do not treat this as a hostile-container security boundary.
- IPv6 is blocked. Docker host network, privileged apps, or apps granted `NET_ADMIN` are outside the intended threat model.
- **DNS_SERVERS** are fixed numeric IPv4 resolvers and routed through the tunnel. The OpenVPN `dhcp-option DNS` push is not automatically applied. Choose resolvers your VPN provider allows or recommends.
- DNS resolution via Docker's embedded DNS proxy is blocked and `/etc/resolv.conf` is replaced at startup; if the file cannot be written the gateway refuses to start.
- LAN exceptions are explicit. `LAN_CIDRS` permits established replies to local LAN clients, while `LAN_TCP_PORTS`/`LAN_UDP_PORTS` allow inbound ports from those CIDRs. Publish the same ports on the gateway container. Avoid overlapping the LAN CIDRs with public Internet ranges.
- Shared-network apps should not receive `NET_ADMIN`, `NET_RAW` unnecessarily, or privileged access. Applications may need restarting when the gateway is recreated.
- Gateway health checks verify tunnel IP and routes, not remote reachability or absence of DNS leaks.
- The firewall is installed after the container starts, so Docker's initial namespace may have a brief startup interval before policy enforcement. **Do not claim strict zero-leak cold-start guarantees until this is tested and addressed with host-level enforcement.**
- No VPN provider profile, certificate, private key, or credentials are included in the image.

## Unraid install
1. Copy `unraid/vpn-gateway.xml` to `/boot/config/plugins/dockerMan/templates-user/my-vpn-gateway.xml`.
2. Place provider files in `/mnt/user/appdata/vpn-gateway/openvpn/`. For certificate-only profiles leave `VPN_AUTH_FILE` blank.
3. Build locally: `docker build -t unraid-vpn-gateway:1.0.0-rc1 .` from this repository root.
4. In Unraid **Docker → Add Container**, select the template, set Repository to `unraid-vpn-gateway:1.0.0-rc1`, Bridge network, and set `VPN_CONFIG` to the mounted filename (e.g. `/config/openvpn/piccolo-1.ovpn`). Keep `NET_ADMIN` and `/dev/net/tun`.
5. Check `docker logs vpn-gateway` for `Initialization Sequence Completed` and `docker inspect vpn-gateway --format '{{.State.Health.Status}}'` for healthy.
6. In an application's settings choose **Network Type → Container → vpn-gateway**. Publish application ports on the gateway, not on the app.

## Compose
`docker compose up -d --build`. Change `VPN_CONFIG` and optional credentials in `compose.yaml`. Compose consumers use `network_mode: service:vpn-gateway`.

## Environment variables
| Variable | Default | Description |
|---|---|---|
| VPN_CONFIG | `/config/openvpn/client.ovpn` | OpenVPN config path |
| VPN_AUTH_FILE | empty | Optional two-line username/password file |
| VPN_TUN | `tun0` | Tunnel interface |
| DNS_SERVERS | `1.1.1.1,9.9.9.9` | DNS through tunnel |
| LAN_CIDRS | empty | Comma-separated IPv4 LAN CIDRs |
| LAN_TCP_PORTS | empty | Inbound LAN TCP ports |
| LAN_UDP_PORTS | empty | Inbound LAN UDP ports |
| RECONNECT_DELAY | `5` | Retry interval in seconds |

## Validation before use
```bash
docker exec vpn-gateway ip -4 route
docker exec vpn-gateway iptables -S
docker exec vpn-gateway ip6tables -S
docker exec vpn-gateway curl -4 --max-time 15 https://api.ipify.org
docker exec vpn-gateway cat /etc/resolv.conf
```
Compare public IP to host. Test a VPN disconnect and ensure the gateway cannot reach public addresses while down. Verify DNS with a dedicated leak-test endpoint. Do not attach important applications until these tests pass. Never post `*.key`, `auth.txt`, or private `.ovpn` contents.

## Certificate renewal
After your VPN provider rotates its CA, download fresh provider configuration and associated files, replace the mounted files and recreate/restart the gateway. Old profiles may stop working. No image rebuild is needed unless the new profile uses unsupported directives.

## Publish to GitHub Container Registry
1. Create a **public** GitHub repository `unraid-vpn-gateway` and push the project (without personal secrets).
2. GitHub Actions `.github/workflows/image.yml` builds on `main` and tags releases from Git tags. In GitHub **Actions**, verify the workflow succeeded.
3. For a release candidate: `git tag v1.0.0-rc1 && git push origin v1.0.0-rc1`. GHCR image becomes `ghcr.io/<owner>/unraid-vpn-gateway:1.0.0-rc1` once the action succeeds.
4. In GitHub **Packages**, set package visibility to **Public** if necessary. Replace the Unraid template Repository with the published image path.
5. Prefer immutable release tags and publish `v1.0.0` only after live disconnect, DNS, and application tests pass.

## License
No license has been selected. Choose one before distributing this project broadly.
