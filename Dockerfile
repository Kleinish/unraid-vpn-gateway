FROM debian:trixie-slim
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends openvpn iptables iproute2 ca-certificates python3 tini curl && rm -rf /var/lib/apt/lists/*
COPY src/ /opt/gateway/
RUN chmod +x /opt/gateway/*.sh
ENTRYPOINT ["/usr/bin/tini","--","/opt/gateway/start.sh"]
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 CMD ["/opt/gateway/health.sh"]
