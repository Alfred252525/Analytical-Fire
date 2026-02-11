#!/usr/bin/env python3
"""Visibility audit. One command. Outputs JSON or the exact fix.
Usage: python3 scripts/run_visibility_audit.py
"""
from __future__ import annotations

import json
import os
import sys
from typing import Optional

BASE_URL = os.getenv("AIFAI_BASE_URL", "https://analyticalfire.com").rstrip("/")
APP_SECRETS_NAME = os.getenv("AIFAI_APP_SECRETS_NAME", "aifai-app-secrets")
AUDITOR_SECRET_NAME = os.getenv("AIFAI_AUDITOR_SECRET_NAME", "aifai-auditor-api-key")

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
TF_DIR = os.path.join(REPO_ROOT, "infrastructure", "terraform")


def _get_region() -> str:
    try:
        import subprocess
        out = subprocess.run(
            ["terraform", "output", "-raw", "aws_region"],
            cwd=TF_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def _fix_cmd() -> str:
    """Exact copy-paste to fix visibility. No docs."""
    r = _get_region()
    return f"cd {os.path.abspath(REPO_ROOT)} && export AWS_REGION={r} AWS_DEFAULT_REGION={r} && python3 scripts/visibility_setup_one_shot.py --region {r} && ./scripts/deploy-backend-update.sh && python3 scripts/run_visibility_audit.py"


def _fix_with_where(ssl_error: bool = False) -> str:
    if ssl_error:
        return (
            "SSL FIX (run on your Mac in Terminal):\n"
            "pip3 install certifi\n"
            "Then re-run: python3 scripts/run_visibility_audit.py"
        )
    return (
        "RUN ON YOUR MAC, IN TERMINAL (the machine with the repo, AWS CLI, and Docker):\n"
        + _fix_cmd()
    )


def get_secrets_client():
    try:
        import boto3
        region = _get_region()
        return boto3.client("secretsmanager", region_name=region)
    except ImportError:
        print("boto3 required: pip install boto3", file=sys.stderr)
        sys.exit(1)


def get_visibility_secret() -> Optional[str]:
    """Get VISIBILITY_SECRET from aifai-app-secrets if present."""
    try:
        client = get_secrets_client()
        r = client.get_secret_value(SecretId=APP_SECRETS_NAME)
        data = json.loads(r["SecretString"])
        secret = data.get("VISIBILITY_SECRET") or data.get("visibility_secret")
        return (secret or "").strip() or None
    except Exception as e:
        print(f"Secret lookup failed: {e}", file=sys.stderr)
        return None


def get_auditor_key() -> Optional[str]:
    """Get auditor API key from Secrets Manager if present (dedicated secret or app-secrets)."""
    try:
        client = get_secrets_client()
        r = client.get_secret_value(SecretId=AUDITOR_SECRET_NAME)
        key = (r.get("SecretString") or "").strip()
        if key:
            return key
    except Exception:
        pass
    try:
        client = get_secrets_client()
        r = client.get_secret_value(SecretId=APP_SECRETS_NAME)
        data = json.loads(r["SecretString"])
        key = data.get("AUDITOR_API_KEY") or data.get("auditor_api_key")
        return (key or "").strip() or None
    except Exception:
        return None


def _make_ssl_context():
    """Use certifi's CA bundle to fix SSL on Mac. pip install certifi if missing."""
    try:
        import ssl
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return None


def fetch_report_via_visibility_secret(secret: str) -> tuple[Optional[dict], Optional[str]]:
    """Call GET /api/v1/visibility/sample. Returns (report_dict, None) or (None, error_message)."""
    try:
        import urllib.error
        import urllib.request
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/visibility/sample?messages_limit=10&knowledge_limit=10&problems_limit=5&days=7",
            headers={"X-Visibility-Secret": secret},
        )
        ctx = _make_ssl_context()
        kwargs = {"timeout": 30}
        if ctx:
            kwargs["context"] = ctx
        with urllib.request.urlopen(req, **kwargs) as resp:
            return (json.loads(resp.read().decode()), None)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return (None, "404: backend has no VISIBILITY_SECRET")
        if e.code == 401:
            return (None, "401: secret mismatch")
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        if body and e.code == 500:
            return (None, f"HTTP 500: {body[:500]}")
        return (None, f"HTTP {e.code}")
    except urllib.error.URLError as e:
        err = f"Request failed: {e.reason}"
        if "CERTIFICATE" in str(e.reason).upper() or "SSL" in str(e.reason).upper():
            err += " (Mac SSL fix: pip3 install certifi, then re-run)"
        return (None, err)
    except Exception as e:
        return (None, str(e))


def fetch_report_via_auditor_key(api_key: str) -> tuple[Optional[dict], Optional[str]]:
    """Call GET /api/v1/moderation/review-sample. Returns (report_dict, None) or (None, error_message)."""
    try:
        import urllib.error
        import urllib.request
        req = urllib.request.Request(
            f"{BASE_URL}/api/v1/moderation/review-sample?messages_limit=10&knowledge_limit=10&problems_limit=5&days=7",
            headers={"X-API-Key": api_key},
        )
        ctx = _make_ssl_context()
        kwargs = {"timeout": 30}
        if ctx:
            kwargs["context"] = ctx
        with urllib.request.urlopen(req, **kwargs) as resp:
            return (json.loads(resp.read().decode()), None)
    except urllib.error.HTTPError as e:
        return (None, f"Moderation endpoint returned {e.code}.")
    except urllib.error.URLError as e:
        err = f"Request failed: {e.reason}"
        if "CERTIFICATE" in str(e.reason).upper() or "SSL" in str(e.reason).upper():
            err += " (Mac SSL fix: pip3 install certifi, then re-run)"
        return (None, err)
    except Exception as e:
        return (None, str(e))


def main() -> None:
    last_error: Optional[str] = None
    ssl_err = False
    # 1. Prefer one-secret visibility endpoint (no bootstrap, no promote)
    secret = get_visibility_secret()
    if secret:
        report, err = fetch_report_via_visibility_secret(secret)
        if report:
            print(json.dumps(report, indent=2))
            return
        if err:
            last_error = err
            ssl_err = "CERTIFICATE" in (err or "").upper() or "SSL" in (err or "").upper()
            print(err, file=sys.stderr)
    else:
        pass  # fix printed at end
    # 2. Fallback: auditor key + review-sample
    api_key = get_auditor_key()
    if api_key:
        report, err = fetch_report_via_auditor_key(api_key)
        if report:
            print(json.dumps(report, indent=2))
            return
        if err:
            last_error = err
            ssl_err = ssl_err or "CERTIFICATE" in (err or "").upper() or "SSL" in (err or "").upper()
            print(err, file=sys.stderr)
    # Nothing worked
    print(_fix_with_where(ssl_error=ssl_err), file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
