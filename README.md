# Unraid OpenVPN Gateway

**Release candidate 1.0.0-rc2 — not yet production-validated.** An OpenVPN-only Docker gateway for Unraid (primary) and Compose (secondary). Other containers share its network namespace using Unraid **Network Type → Container → vpn-gateway**.

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
- LAN exceptions are explicit. `LAN_CIDRS` identifies trusted client subnets and creates narrow return routes through the underlay gateway; `LAN_TCP_PORTS`/`LAN_UDP_PORTS` permit new inbound connections only on the underlay interface. Established replies are allowed back through that interface. For bridge networking, publish ports on the gateway; for macvlan, use its IP directly. Never use `0.0.0.0/0` as a LAN CIDR.
- Shared-network apps should not receive `NET_ADMIN`, `NET_RAW` unnecessarily, or privileged access. Applications may need restarting when the gateway is recreated.
- Gateway health checks verify tunnel IP and routes, not remote reachability or absence of DNS leaks.
- The firewall is installed after the container starts, so Docker's initial namespace may have a brief startup interval before policy enforcement. **Do not claim strict zero-leak cold-start guarantees until this is tested and addressed with host-level enforcement.**
- No VPN provider profile, certificate, private key, or credentials are included in the image.

## Unraid install
1. Copy `unraid/my-vpn-gateway.xml` to `/boot/config/plugins/dockerMan/templates-user/my-vpn-gateway.xml`. The template includes a 512×512 icon hosted from this repository. GitHub must be reachable by Unraid to fetch the icon.
2. Place provider files in `/mnt/user/appdata/vpn-gateway/openvpn/`. For certificate-only profiles leave `VPN_AUTH_FILE` blank.
3. Confirm the `v1.0.0-rc2` GitHub Actions image build has completed successfully and the GHCR package is public (or Unraid is authenticated to GHCR). The template pulls `ghcr.io/kleinish/unraid-vpn-gateway:1.0.0-rc2` by default; no local build is needed.
4. In Unraid **Docker → Add Container**, select the template, set the network to Bridge or **Custom: eth0.72** with a fixed IP such as `10.6.72.90` if available on your network, and set `VPN_CONFIG` to your mounted `.ovpn` filename. Keep `NET_ADMIN` and `/dev/net/tun`.
5. Check `docker logs vpn-gateway` for `Initialization Sequence Completed` and `docker inspect vpn-gateway --format '{{.State.Health.Status}}'` for healthy.
6. In an application's settings choose **Network Type → Container → vpn-gateway**. For Bridge, publish application ports on the gateway, not the app. For macvlan, the application shares the gateway IP and usually does not need a Docker port publication; set `LAN_CIDRS` and `LAN_TCP_PORTS`/`LAN_UDP_PORTS` and verify routing. For example, a WebUI listening on `0.0.0.0:8080` should be reachable at `http://10.6.72.90:8080` only after firewall and return-route tests succeed. Cross-VLAN clients receive specific non-VPN return routes automatically when configured in `LAN_CIDRS`. Some Unraid hosts cannot directly access their own macvlan containers.

## Compose
`docker compose up -d`. The Compose file pulls the tagged GHCR image by default. To build from source instead, run `docker build -t unraid-vpn-gateway:1.0.0-rc2 .` and change the Compose image reference. Change `VPN_CONFIG` and optional credentials in `compose.yaml`. Compose consumers use `network_mode: service:vpn-gateway`.

## Environment variables
| Variable | Default | Description |
|---|---|---|
| VPN_CONFIG | `/config/openvpn/client.ovpn` | OpenVPN config path |
| VPN_AUTH_FILE | empty | Optional two-line username/password file |
| VPN_TUN | `tun0` | Tunnel interface |
| DNS_SERVERS | `1.1.1.1,9.9.9.9` | DNS through tunnel |
| LAN_CIDRS | empty | Comma-separated authorized IPv4 client CIDRs; installs return routes |
| LAN_GATEWAY | auto | Optional IPv4 router for LAN return routes; auto-detects default gateway on eth0 |
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
3. For a release candidate: `git tag v1.0.0-rc2 && git push origin v1.0.0-rc2`. GHCR image becomes `ghcr.io/<owner>/unraid-vpn-gateway:1.0.0-rc2` once the action succeeds.
4. In GitHub **Packages**, set package visibility to **Public** if necessary. The included Unraid template already references `ghcr.io/kleinish/unraid-vpn-gateway:1.0.0-rc2`.
5. Prefer immutable release tags and publish `v1.0.0` only after live disconnect, DNS, and application tests pass.

## License
No license has been selected. Choose one before distributing this project broadly.

## Unraid template and icon
- Template source: [`unraid/my-vpn-gateway.xml`](unraid/my-vpn-gateway.xml). Install it as `/boot/config/plugins/dockerMan/templates-user/my-vpn-gateway.xml`.
- Icon: [`vpn.png`](vpn.png), 512×512 PNG. The XML `<Icon>` references `https://raw.githubusercontent.com/Kleinish/unraid-vpn-gateway/main/vpn.png`.
- GHCR release image: `ghcr.io/kleinish/unraid-vpn-gateway:1.0.0-rc2`. This is a release candidate, not a verified production release.
- When changing the release version, update the XML `<Repository>` tag and Compose `image:` together.

## Cross-VLAN WebUI example (Unraid macvlan)

With `vpn-gateway` on `eth0.72` at `10.6.72.10/24`, and a workstation on `10.7.7.0/24` reaching Syncthing's WebUI:

```ini
LAN_CIDRS=10.7.7.0/24
LAN_TCP_PORTS=8384
LAN_UDP_PORTS=
LAN_GATEWAY=10.6.72.1
```

`LAN_GATEWAY` may be blank if the gateway's underlay default route is `via 10.6.72.1 dev eth0`. On startup the firewall allows **new inbound TCP 8384** only from `10.7.7.0/24` on `eth0`, and allows **established replies** back via `eth0`. It also installs a specific `10.7.7.0/24 via 10.6.72.1 dev eth0` route, so OpenVPN's split default routes cannot divert the replies into the tunnel. Your router/firewall must independently allow the workstation to reach `10.6.72.10:8384`; the gateway cannot bypass that policy.

To expose another app, add its port to `LAN_TCP_PORTS` (e.g. `8384,8080`) and **recreate the gateway** in Unraid. No automatic Docker event watcher is needed: apps share the gateway's namespace and the gateway owns all ingress policy. Keep each port restricted to trusted client CIDRs, and enable authentication on exposed WebUIs. Recreating the gateway can interrupt dependent applications; restart them if necessary.

Verify:

```bash
docker exec vpn-gateway ip route get 10.7.7.12
docker exec vpn-gateway iptables -S INPUT
docker exec vpn-gateway iptables -S OUTPUT
```

Expected return path: `via 10.6.72.1 dev eth0`. If you change the allowed subnets or ports, recreate the gateway so startup rules are reapplied. If you need different permitted ports per VLAN, this release uses a shared port list across all configured `LAN_CIDRS`; do not include untrusted subnets.

**Security note:** These routes permit only the explicitly allowed established replies through the host-side firewall; they do not authorize new arbitrary outbound LAN connections. This is not a substitute for VLAN router ACLs. The known cold-start exposure window and VPN-endpoint exception remain limitations; test disconnects and DNS leaks before production use.
