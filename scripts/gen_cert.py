"""
Generate a self-signed TLS certificate for local HTTPS development.

Usage:
    python311 scripts/gen_cert.py

Outputs:
    certs/cert.pem  — certificate
    certs/key.pem   — private key

Then add to .env:
    HTTPS_CERT_FILE=certs/cert.pem
    HTTPS_KEY_FILE=certs/key.pem
    ENVIRONMENT=dev

Restart the server — it will serve https://localhost:8000
Browser will show a security warning (self-signed) — click "Advanced → Proceed" once.

NOTE: In production (ThinkBook + Cloudflare Tunnel), you do NOT need this.
Cloudflare terminates TLS at the edge and issues a real certificate automatically.
"""
import sys
from pathlib import Path

# Requires: pip install cryptography
try:
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509 import DNSName, IPAddress
    import ipaddress
    from datetime import datetime, timezone, timedelta
except ImportError:
    print("Missing dependency. Run: python311 -m pip install cryptography")
    sys.exit(1)

CERTS_DIR = Path(__file__).resolve().parent.parent / "certs"
CERTS_DIR.mkdir(exist_ok=True)

CERT_FILE = CERTS_DIR / "cert.pem"
KEY_FILE = CERTS_DIR / "key.pem"

# Generate private key
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

# Build certificate
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
])
cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)
    .public_key(key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.now(timezone.utc))
    .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
    .add_extension(
        x509.SubjectAlternativeName([
            DNSName("localhost"),
            IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]),
        critical=False,
    )
    .sign(key, hashes.SHA256())
)

KEY_FILE.write_bytes(key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
))
CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

print(f"Certificate: {CERT_FILE}")
print(f"Private key: {KEY_FILE}")
print()
print("Add to .env:")
print(f"  HTTPS_CERT_FILE=certs/cert.pem")
print(f"  HTTPS_KEY_FILE=certs/key.pem")
