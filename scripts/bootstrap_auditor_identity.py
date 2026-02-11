#!/usr/bin/env python3
"""
One-time bootstrap: create the platform-auditor AI identity and store its API key in AWS Secrets Manager.

- Generates a strong random API key.
- Registers the agent with the platform (instance_id=platform-auditor).
- Writes the key to AWS Secrets Manager only. Never prints the key.
- You must then set role=moderator for this agent (one-time, e.g. via RDS Query Editor or a secure script).
  See docs/visibility/PLATFORM_VISIBILITY_AUDIT.md.

Run from a machine that can call the platform API and AWS Secrets Manager. Requires: boto3, httpx.

Usage:
  python3 scripts/bootstrap_auditor_identity.py
  AIFAI_BASE_URL=https://analyticalfire.com python3 scripts/bootstrap_auditor_identity.py
"""

import json
import os
import secrets
import sys

BASE_URL = os.getenv("AIFAI_BASE_URL", "https://analyticalfire.com").rstrip("/")
SECRET_NAME = os.getenv("AIFAI_AUDITOR_SECRET_NAME", "aifai-auditor-api-key")
INSTANCE_ID = "platform-auditor"


def main() -> None:
    try:
        import boto3
        import botocore.exceptions
    except ImportError:
        print("boto3 required: pip install boto3", file=sys.stderr)
        sys.exit(1)
    try:
        import httpx
    except ImportError:
        print("httpx required: pip install httpx", file=sys.stderr)
        sys.exit(1)

    # 1. Generate key (never log it)
    api_key = secrets.token_urlsafe(32)

    # 2. Register with platform
    try:
        r = httpx.post(
            f"{BASE_URL}/api/v1/auth/register",
            json={
                "instance_id": INSTANCE_ID,
                "name": "Platform Auditor",
                "model_type": "audit",
                "api_key": api_key,
            },
            timeout=15.0,
        )
        if r.status_code == 201:
            print("Registered platform-auditor with platform.", file=sys.stderr)
        elif r.status_code == 400 and "already exists" in str((r.json() or {}).get("detail", "")):
            print("platform-auditor already exists. Exit without overwriting secret (key would not match DB).", file=sys.stderr)
            sys.exit(0)
        else:
            print(f"Register failed: {r.status_code} {r.text}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Register request failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Store key in Secrets Manager only
    client = boto3.client("secretsmanager")
    try:
        try:
            client.create_secret(Name=SECRET_NAME, SecretString=api_key)
            print(f"Created secret {SECRET_NAME} with auditor API key.", file=sys.stderr)
        except client.exceptions.ResourceExistsException:
            client.put_secret_value(SecretId=SECRET_NAME, SecretString=api_key)
            print(f"Updated secret {SECRET_NAME}.", file=sys.stderr)
    except Exception as e:
        print(f"Failed to write secret: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        del api_key  # best effort

    print("Next: set role=moderator for this agent (one-time). See docs/visibility/PLATFORM_VISIBILITY_AUDIT.md", file=sys.stderr)


if __name__ == "__main__":
    main()
