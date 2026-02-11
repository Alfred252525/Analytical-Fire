# Get visibility working — one command (no Console)

**You do not need to click through AWS.** One script does everything.

---

## One-shot setup (run once)

From the repo root, with **AWS CLI configured** (same account/region as your stack; region is usually **us-east-1** from Terraform):

```bash
pip install boto3   # if needed
python3 scripts/visibility_setup_one_shot.py
```

That script will:

1. Add **VISIBILITY_SECRET** to **aifai-app-secrets** (merge into existing JSON; generates a random value).
2. Ensure the **aifai-backend** ECS task definition has **VISIBILITY_SECRET** from that secret; register a new revision if needed.
3. Update the **aifai-backend** ECS service to use that revision and force a new deployment; wait until stable.
4. Run **deploy-backend-update.sh** so the running backend image has the visibility endpoint (build, push, force deploy).

When it finishes, get the report (you or the agent):

```bash
python3 scripts/run_visibility_audit.py
```

**Run in AWS CloudShell (exact order):**

1. `cd /home/cloudshell-user/Analytical-Fire`
2. `git pull`  ← **Do this before running the script** so you have the latest version.
3. `export AWS_REGION=us-east-1`
4. `python3 scripts/run_visibility_audit.py`

Script is compatible with Python 3.9 (CloudShell). If you see `TypeError: unsupported operand type(s) for |`, you're on an old copy—run `git pull` and try again.

**Options:**

- `--no-build` — Skip the deploy-backend-update step (e.g. if the backend image already has the visibility endpoint). You can run `./scripts/deploy-backend-update.sh` yourself later.
- `--region us-east-1` — Force region (default is from Terraform output or env; stack is us-east-1).
- `--dry-run` — Print what would be done, no changes.

**If you see "Secret ... not found" or "Failed to describe task definition":** You're in the wrong region or the stack isn't deployed there. Use `--region us-east-1` and ensure your AWS credentials can access that account/region.

---

## Region

The Terraform stack uses **us-east-1 (N. Virginia)**. The script uses Terraform output or `AWS_REGION`; it does not use the region shown in your browser. If you ever used the Console and saw "No secrets", you were in **us-east-2 (Ohio)**; the script runs in the correct region as long as your CLI is configured for the same account (us-east-1).

---

## Manual steps (only if you can't run the script)

If the one-shot script can't be used (e.g. no AWS CLI, different setup), see the steps in [VISIBILITY_UNLOCK.md](VISIBILITY_UNLOCK.md). You'll need to add **VISIBILITY_SECRET** to **aifai-app-secrets** in **us-east-1**, add it to the ECS task definition, deploy the backend, then run `python3 scripts/run_visibility_audit.py`.
