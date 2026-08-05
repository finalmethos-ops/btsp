#!/usr/bin/env bash
set -euo pipefail

host="${1:-192.168.0.146}"
output_directory="${2:-.runtime/tls}"
origin_name="${3:-btsp-origin}"

python3 - "$host" "$origin_name" <<'PY'
import ipaddress
import re
import sys

address = ipaddress.IPv4Address(sys.argv[1])
origin_name = sys.argv[2]
networks = (
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
)
if not any(address in network for network in networks):
    raise SystemExit("Host must be an RFC 1918 private IPv4 address.")
if not re.fullmatch(
    r"(?=.{1,253}\Z)(?!-)(?:[a-zA-Z0-9-]{1,63}\.)*"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?",
    origin_name,
):
    raise SystemExit("Origin name must be a valid DNS hostname.")
PY

authority_directory="$output_directory/authority"
server_directory="$output_directory/server"
authority_key="$authority_directory/btsp-intranet-ca.key"
authority_certificate="$authority_directory/btsp-intranet-ca.crt"
server_key="$server_directory/server.key"
server_request="$server_directory/server.csr"
server_certificate="$server_directory/server.crt"

if [[ -e "$authority_key" && ! -e "$authority_certificate" ]] ||
   [[ ! -e "$authority_key" && -e "$authority_certificate" ]]; then
  echo "Incomplete certificate-authority material exists; refusing to continue." >&2
  exit 2
fi

if [[ -e "$server_key" || -e "$server_request" || -e "$server_certificate" ]]; then
  echo "Server certificate material already exists; refusing to overwrite it." >&2
  exit 2
fi

umask 077
mkdir -p "$authority_directory" "$server_directory"

if [[ ! -e "$authority_key" ]]; then
  openssl genpkey \
    -algorithm RSA \
    -pkeyopt rsa_keygen_bits:4096 \
    -out "$authority_key"

  openssl req \
    -x509 \
    -new \
    -sha256 \
    -days 3650 \
    -key "$authority_key" \
    -out "$authority_certificate" \
    -subj "/CN=BTSP Intranet Root CA/O=BTSP" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -addext "subjectKeyIdentifier=hash"
else
  openssl verify \
    -CAfile "$authority_certificate" \
    "$authority_certificate"
fi

openssl genpkey \
  -algorithm RSA \
  -pkeyopt rsa_keygen_bits:3072 \
  -out "$server_key"

openssl req \
  -new \
  -sha256 \
  -key "$server_key" \
  -out "$server_request" \
  -subj "/CN=$origin_name/O=BTSP"

openssl x509 \
  -req \
  -sha256 \
  -days 825 \
  -in "$server_request" \
  -CA "$authority_certificate" \
  -CAkey "$authority_key" \
  -CAcreateserial \
  -out "$server_certificate" \
  -extfile <(
    printf '%s\n' \
      "basicConstraints=critical,CA:FALSE" \
      "keyUsage=critical,digitalSignature,keyEncipherment" \
      "extendedKeyUsage=serverAuth" \
      "subjectAltName=DNS:$origin_name,IP:$host,IP:127.0.0.1,DNS:localhost" \
      "authorityKeyIdentifier=keyid,issuer" \
      "subjectKeyIdentifier=hash"
  )

rm "$server_request" "$authority_directory/btsp-intranet-ca.srl"
chmod 600 "$authority_key" "$server_key"
chmod 644 "$authority_certificate" "$server_certificate"

openssl verify \
  -CAfile "$authority_certificate" \
  "$server_certificate"

echo "Created BTSP server certificate for stable origin $origin_name and LAN host $host."
echo "Install this public certificate as a trusted root on clients:"
echo "$authority_certificate"
