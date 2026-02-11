#!/usr/bin/env python3
"""
One-shot visibility setup. Run once with AWS CLI configured. No Console clicking.

Does:
  1. Add VISIBILITY_SECRET to aifai-app-secrets (merge into existing JSON).
  2. Ensure ECS task definition aifai-backend has VISIBILITY_SECRET; register new revision if needed.
  3. Update ECS service to use that revision and force new deployment.
  4. Optionally build/push backend image (so /api/v1/visibility/sample exists) and force deploy again.

After this, run: python3 scripts/run_visibility_audit.py

Requires: aws CLI, boto3, AWS credentials with permissions to:
  - secretsmanager:GetSecretValue, PutSecretValue on aifai-app-secrets
  - ecs:DescribeTaskDefinition, RegisterTaskDefinition, DescribeServices, UpdateService
  - (if --build) ecr get-login, docker, ecr:GetDownloadUrlForLayer etc.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

try:
    import boto3
except ImportError:
    print("boto3 required: pip install boto3", file=sys.stderr)
    sys.exit(1)


def get_region() -> str:
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    tf_dir = os.path.join(repo_root, "infrastructure", "terraform")
    try:
        out = subprocess.run(
            ["terraform", "output", "-raw", "aws_region"],
            cwd=tf_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"


def main() -> int:
    parser = argparse.ArgumentParser(description="One-shot visibility setup (no Console)")
    parser.add_argument("--region", default=None, help="AWS region (default: terraform or us-east-1)")
    parser.add_argument("--no-build", action="store_true", help="Skip build/push backend image (run deploy-backend-update.sh yourself after)")
    parser.add_argument("--dry-run", action="store_true", help="Only print what would be done")
    args = parser.parse_args()

    region = args.region or get_region()
    dry = args.dry_run
    os.environ["AWS_REGION"] = region
    os.environ["AWS_DEFAULT_REGION"] = region

    print(f"Region: {region}")
    if dry:
        print("DRY RUN – no changes")
    print()

    sts = boto3.client("sts", region_name=region)
    try:
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
    except Exception as e:
        print(f"AWS credentials failed: {e}", file=sys.stderr)
        return 1

    sm = boto3.client("secretsmanager", region_name=region)
    secret_id = "aifai-app-secrets"

    # 1. Get current secret, add VISIBILITY_SECRET (and get ARN for ECS)
    try:
        r = sm.get_secret_value(SecretId=secret_id)
        data = json.loads(r["SecretString"])
        secret_arn = r.get("ARN", "").strip()  # full ARN (includes AWS suffix) for ECS valueFrom
    except sm.exceptions.ResourceNotFoundException:
        print(f"Secret {secret_id} not found in {region}. Use the region where your stack lives (e.g. us-east-1 or us-east-2).", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Failed to read secret: {e}", file=sys.stderr)
        return 1

    if "VISIBILITY_SECRET" in data or "visibility_secret" in data:
        print(f"VISIBILITY_SECRET already in {secret_id}; skipping secret update.")
        visibility_value = data.get("VISIBILITY_SECRET") or data.get("visibility_secret")
    else:
        import secrets
        visibility_value = secrets.token_hex(32)
        data["VISIBILITY_SECRET"] = visibility_value
        if dry:
            print(f"[dry-run] Would add VISIBILITY_SECRET to {secret_id}")
        else:
            sm.put_secret_value(SecretId=secret_id, SecretString=json.dumps(data))
            print(f"Added VISIBILITY_SECRET to {secret_id}")

    # 2. ECS task definition: ensure VISIBILITY_SECRET in container secrets (use real secret ARN)
    ecs = boto3.client("ecs", region_name=region)
    family = "aifai-backend"
    try:
        td = ecs.describe_task_definition(taskDefinition=family)
        task_def = td["taskDefinition"]
    except Exception as e:
        print(f"Failed to describe task definition {family}: {e}. Wrong region or stack not deployed?", file=sys.stderr)
        return 1

    # Strip fields that register-task-definition doesn't accept
    register = {k: v for k, v in task_def.items() if k not in (
        "taskDefinitionArn", "revision", "status", "requiresAttributes",
        "compatibilities", "registeredAt", "registeredBy",
    )}
    containers = register.get("containerDefinitions") or []
    if not containers:
        print("No container definitions", file=sys.stderr)
        return 1
    cont = containers[0]
    secrets_list = cont.get("secrets") or []
    has_vis = any(
        (s.get("name") == "VISIBILITY_SECRET") or (s.get("valueFrom") or "").endswith(":VISIBILITY_SECRET::")
        for s in secrets_list
    )
    if not has_vis:
        # ECS needs full secret ARN + :KEY:: for JSON key (secret ARN from API includes suffix)
        value_from = f"{secret_arn}:VISIBILITY_SECRET::" if secret_arn else f"arn:aws:secretsmanager:{region}:{account_id}:secret:aifai-app-secrets:VISIBILITY_SECRET::"
        secrets_list.append({"name": "VISIBILITY_SECRET", "valueFrom": value_from})
        cont["secrets"] = secrets_list
        if dry:
            print("[dry-run] Would register new task definition revision with VISIBILITY_SECRET")
        else:
            ecs.register_task_definition(**register)
            print("Registered new task definition revision with VISIBILITY_SECRET")
    else:
        print("Task definition already has VISIBILITY_SECRET")

    # 3. Update ECS service: latest task definition, force new deployment
    cluster = os.environ.get("AIFAI_ECS_CLUSTER")
    if not cluster:
        try:
            out = subprocess.run(
                ["terraform", "output", "-raw", "ecs_cluster_name"],
                cwd=os.path.join(os.path.dirname(__file__), "..", "infrastructure", "terraform"),
                capture_output=True,
                text=True,
                timeout=10,
            )
            cluster = out.stdout.strip() if out.returncode == 0 else None
        except Exception:
            pass
    cluster = cluster or "aifai-cluster"
    service = "aifai-backend"

    if dry:
        print(f"[dry-run] Would update service {service} on cluster {cluster}")
    else:
        ecs.update_service(
            cluster=cluster,
            service=service,
            taskDefinition=family,
            forceNewDeployment=True,
        )
        print(f"Triggered new deployment for {service} (task def + force new deployment)")
        print("Waiting for service to stabilize (2–3 min)...")
        waiter = ecs.get_waiter("services_stable")
        waiter.wait(cluster=cluster, services=[service], WaiterConfig={"Delay": 15, "MaxAttempts": 40})
        print("Service stable.")

    # 4. Build and push backend image (so visibility endpoint exists) and force deploy again
    if not args.no_build and not dry:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        deploy_script = os.path.join(script_dir, "deploy-backend-update.sh")
        if os.path.isfile(deploy_script):
            print("Running deploy-backend-update.sh so backend has visibility endpoint...")
            ret = subprocess.run(["/bin/bash", deploy_script], cwd=os.path.join(script_dir, ".."))
            if ret.returncode != 0:
                print("Deploy script failed. Run ./scripts/deploy-backend-update.sh yourself, then run_visibility_audit.py", file=sys.stderr)
                return ret.returncode
        else:
            print("Run ./scripts/deploy-backend-update.sh so the backend image has the visibility endpoint, then run_visibility_audit.py")
    elif args.no_build:
        print("Skipped build. Run ./scripts/deploy-backend-update.sh then python3 scripts/run_visibility_audit.py")

    print()
    print("Next: get the report (you or the agent):")
    print("  python3 scripts/run_visibility_audit.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
