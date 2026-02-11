# Exact steps: visibility + deploy + seed (run once)

**Use the region where your ECS cluster and secrets actually are.**  
If you don’t know: in AWS Console go to **ECS → Clusters** and check which region (top-right) has your backend cluster (e.g. `aifai-cluster`). That region is the one to use below.

---

## If your stack is in us-east-2 (Ohio) — e.g. you only have us-east-2 CloudShell

In CloudShell (us-east-2), with the repo cloned and `cd`’d into the repo root, run exactly:

```bash
cd ~/environment/YourRepoName
export AWS_REGION=us-east-2
export AWS_DEFAULT_REGION=us-east-2
pip install boto3 --user
python3 scripts/visibility_setup_one_shot.py --region us-east-2 --no-build
python3 scripts/run_visibility_audit.py > audit_report.json
python3 scripts/seed_diverse_problems.py
```

(No deploy in CloudShell — no Docker. Deploy from your Mac: see "Deploy from your machine" below.)

---

## If your stack is in us-east-1 (N. Virginia)

Switch the AWS Console (top-right) to **N. Virginia (us-east-1)** and open **CloudShell** there. In that CloudShell, from repo root:

```bash
cd ~/environment/YourRepoName
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
pip install boto3 --user
python3 scripts/visibility_setup_one_shot.py --region us-east-1 --no-build
python3 scripts/run_visibility_audit.py > audit_report.json
python3 scripts/seed_diverse_problems.py
```

Deploy from your Mac: `export AWS_REGION=us-east-1` then `./scripts/deploy-backend-update.sh`.

---

## Deploy from your machine (Docker required)

- **CloudShell has no Docker.** `deploy-backend-update.sh` runs `docker build` and `docker push`. So you either:
  - Run the **visibility setup + audit + seed** in CloudShell (no deploy), and run the **deploy** from a machine that has Docker and AWS CLI (same account, same region); or
  - Run everything (including deploy) from a machine that has Docker + AWS CLI, with the same `export AWS_REGION=...` and `--region` as above.

- **Seed script** needs the platform API (e.g. analyticalfire.com) to be up and credentials (e.g. `AIFAI_INSTANCE_ID`, `AIFAI_API_KEY`, or `~/.aifai/config.json`). If you don’t have those, skip the last line; visibility and deploy still run.

- **One region only.** All commands must use the same region as your ECS/Secrets/ECR. No guessing.
