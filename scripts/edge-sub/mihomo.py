#!/usr/bin/env python3
"""
mihomo.yaml 生成器: 从 hysteria2 / vless REALITY / shadowsocks-2022 URI 输出 mihomo/Clash.Meta 配置。

用法:
    mihomo.py <URI1> [URI2 ...] > out.yaml
"""
from __future__ import annotations
import sys, json, base64, re, os, urllib.parse as up


def parse_hysteria2(uri: str) -> dict:
    if not uri.startswith(("hysteria2://", "hy2://")):
        raise ValueError("not a hysteria2 URI: " + uri[:40])
    s = uri
    if s.startswith("hysteria2://"):
        s = s[len("hysteria2://"):]
    elif s.startswith("hy2://"):
        s = s[len("hy2://"):]
    frag = ""
    if "#" in s:
        s, frag = s.split("#", 1)
    q = ""
    if "?" in s:
        s, q = s.split("?", 1)
    m = re.match(r"^([^@]*)@([^:]+):(\d+)$", s)
    if not m:
        raise ValueError("URI bad shape (userinfo@host:port): " + s)
    userinfo, host, port = m.group(1), m.group(2), int(m.group(3))
    password = up.unquote(userinfo)
    params = dict(up.parse_qsl(q, keep_blank_values=True))
    name = up.unquote(frag) or params.get("peer") or "hysteria2"
    sni = params.get("sni") or host
    insecure = params.get("insecure", "0") in ("1", "true", "yes")
    obfs_type = params.get("obfs", "").strip()
    obfs_pwd  = params.get("obfs-password", "")
    return {
        "type": "hysteria2",
        "name": name, "host": host, "port": port, "password": password,
        "sni": sni, "insecure": insecure,
        "obfs_type": obfs_type, "obfs_password": obfs_pwd,
        "raw_params": params,
    }


def parse_vless(uri: str) -> dict:
    if not uri.startswith("vless://"):
        raise ValueError("not a vless URI: " + uri[:40])
    s = uri[len("vless://"):]
    frag = ""
    if "#" in s:
        s, frag = s.split("#", 1)
    q = ""
    if "?" in s:
        s, q = s.split("?", 1)
    m = re.match(r"^([^@]*)@([^:]+):(\d+)$", s)
    if not m:
        raise ValueError("VLESS URI bad shape (uuid@host:port): " + s)
    uuid, host, port = m.group(1), m.group(2), int(m.group(3))
    params = dict(up.parse_qsl(q, keep_blank_values=True))
    name = up.unquote(frag) or "reality-vision"
    sni = params.get("sni") or host
    flow = params.get("flow", "xtls-rprx-vision")
    pbk = params.get("pbk", "")
    sid = params.get("sid", "")
    fp = params.get("fp", "chrome")
    return {
        "type": "vless",
        "name": name, "host": host, "port": port,
        "uuid": uuid, "flow": flow, "sni": sni, "pbk": pbk, "sid": sid, "fp": fp,
    }


def parse_shadowsocks(uri: str) -> dict:
    if not uri.startswith("ss://"):
        raise ValueError("not a shadowsocks URI: " + uri[:40])
    s = uri[len("ss://"):]
    frag = ""
    if "#" in s:
        s, frag = s.split("#", 1)
    name = up.unquote(frag) or "shadowsocks"
    if "@" in s:
        userinfo_part, host_port_part = s.split("@", 1)
        try:
            pad = len(userinfo_part) % 4
            b64_str = userinfo_part + ("=" * ((4 - pad) % 4))
            decoded = base64.urlsafe_b64decode(b64_str).decode("utf-8")
            if ":" in decoded:
                method, password = decoded.split(":", 1)
            else:
                method, password = "", decoded
        except Exception:
            if ":" in userinfo_part:
                method, password = userinfo_part.split(":", 1)
            else:
                method, password = "", userinfo_part
        m = re.match(r"^([^:]+):(\d+)$", host_port_part)
        if not m:
            raise ValueError(f"invalid host:port in ss URI: {host_port_part}")
        host, port = m.group(1), int(m.group(2))
    else:
        pad = len(s) % 4
        b64_str = s + ("=" * ((4 - pad) % 4))
        decoded = base64.urlsafe_b64decode(b64_str).decode("utf-8")
        userinfo, host_port = decoded.split("@", 1)
        method, password = userinfo.split(":", 1)
        host, port = host_port.split(":", 1)
        port = int(port)
    return {
        "type": "ss",
        "name": name,
        "host": host,
        "port": port,
        "cipher": method,
        "password": password,
        "udp": True,
    }


def yaml_escape(s: str) -> str:
    if not s:
        return ""
    if all(c.isalnum() or c in "-_.,:;+=!()*&^%$#@?/<>|~ " for c in s):
        return s
    return "'" + s.replace("'", "''") + "'"


def build_yaml(nodes: list[dict]) -> str:
    server_override = os.environ.get("EDGE_SERVER_IP") or (
        open("/etc/edge/server_ip").read().strip() if os.path.exists("/etc/edge/server_ip") else ""
    )
    node_blocks = []
    node_names = []
    for p in nodes:
        name = yaml_escape(p["name"])
        node_names.append(name)
        host = server_override if server_override else p["host"]
        port = p["port"]
        if p["type"] == "hysteria2":
            pw = yaml_escape(p["password"])
            sni = yaml_escape(p["sni"])
            lines = [
                f"  - name: {name}",
                f"    type: hysteria2",
                f"    server: {host}",
                f"    port: {port}",
                f"    password: {pw}",
                f"    sni: {sni}",
                f"    skip-cert-verify: {'true' if p['insecure'] else 'false'}",
            ]
            if p.get("obfs_type"):
                lines.append(f"    obfs: {yaml_escape(p['obfs_type'])}")
            if p.get("obfs_password"):
                lines.append(f"    obfs-password: {yaml_escape(p['obfs_password'])}")
            node_blocks.append(chr(10).join(lines))
        elif p["type"] == "vless":
            lines = [
                f"  - name: {name}",
                f"    type: vless",
                f"    server: {host}",
                f"    port: {port}",
                f"    uuid: {p['uuid']}",
                f"    network: tcp",
                f"    tls: true",
                f"    udp: true",
                f"    flow: {p['flow']}",
                f"    servername: {yaml_escape(p['sni'])}",
                f"    reality-opts:",
                f"      public-key: {p['pbk']}",
                f"      short-id: {p['sid']}",
                f"    client-fingerprint: {p['fp']}",
            ]
            node_blocks.append(chr(10).join(lines))
        elif p["type"] == "ss":
            lines = [
                f"  - name: {name}",
                f"    type: ss",
                f"    server: {host}",
                f"    port: {port}",
                f"    cipher: {yaml_escape(p['cipher'])}",
                f"    password: {yaml_escape(p['password'])}",
                f"    udp: true",
            ]
            node_blocks.append(chr(10).join(lines))

    proxies_yaml = chr(10).join(node_blocks)
    proxies_list = chr(10).join([f"      - {n}" for n in node_names])

    out = f"""# Generated by /opt/edge-sub/mihomo.py
mixed-port: 7890
allow-lan: false
mode: rule
log-level: warning
geo-auto-update: false
geodata-mode: false

proxies:
{proxies_yaml}

proxy-groups:
  - name: PROXY
    type: select
    proxies:
{proxies_list}
      - DIRECT
  - name: AUTO
    type: url-test
    url: https://www.gstatic.com/generate_204
    interval: 300
    proxies:
{proxies_list}

rules:
  # AI 流量 UDP 443 客户端即时拦截 (0ms Fail-Fast 降级至 TCP HTTP/2，杜绝 QUIC 绕过 WARP 导致机房裸 IP 泄露)
  - AND,((NETWORK,UDP),(DST-PORT,443),(DOMAIN-KEYWORD,openai)),REJECT
  - AND,((NETWORK,UDP),(DST-PORT,443),(DOMAIN-KEYWORD,chatgpt)),REJECT
  - AND,((NETWORK,UDP),(DST-PORT,443),(DOMAIN-KEYWORD,anthropic)),REJECT
  - AND,((NETWORK,UDP),(DST-PORT,443),(DOMAIN-KEYWORD,claude)),REJECT
  - AND,((NETWORK,UDP),(DST-PORT,443),(DOMAIN-SUFFIX,gemini.google.com)),REJECT
  - AND,((NETWORK,UDP),(DST-PORT,443),(DOMAIN-SUFFIX,aistudio.google.com)),REJECT
  - GEOIP,private,DIRECT,no-resolve
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
"""
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        raise SystemExit(2)
    uris = sys.argv[1:]
    nodes = []
    for u in uris:
        u = u.strip()
        if not u: continue
        if u.startswith(("hysteria2://", "hy2://")):
            nodes.append(parse_hysteria2(u))
        elif u.startswith("vless://"):
            nodes.append(parse_vless(u))
        elif u.startswith("ss://"):
            nodes.append(parse_shadowsocks(u))
        else:
            sys.stderr.write(f"Warning: unknown URI scheme: {u[:30]}\n")
    if not nodes:
        raise SystemExit("No valid nodes parsed")
    sys.stdout.write(build_yaml(nodes))


if __name__ == "__main__":
    main()
