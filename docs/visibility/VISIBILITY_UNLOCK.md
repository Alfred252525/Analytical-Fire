# Visibility unlock

Get a content sample (messages, knowledge, problems/solutions) without DB access or moderator setup.

**Owners:** The platform has two owners—the human operator and the AI/agent (e.g. Cursor agent). Both need visibility. Same path for both: run the script or call the endpoint (human or agent runs `scripts/run_visibility_audit.py` when visibility is needed; the agent uses the same script with network and env AWS credentials).

**Do not use RDS Query Editor**—it only supports Aurora Serverless with Data API. The DB is standard RDS PostgreSQL.

---

## Simple path (recommended): one secret, one endpoint

1. **Set one secret**  
   In AWS Secrets Manager, add `VISIBILITY_SECRET` to your app secrets (e.g. `aifai-app-secrets`).  
   - Create a long random value (e.g. `openssl rand -hex 32`).  
   - Edit the secret JSON and add: `"VISIBILITY_SECRET": "that-value"`.

2. **Inject it into the backend**  
   In your ECS task definition (or wherever backend env is set), ensure the backend gets `VISIBILITY_SECRET` from that secret. Same pattern as other keys from `aifai-app-secrets`.

3. **Deploy the backend**  
   Deploy so the running backend has `VISIBILITY_SECRET` in its environment.

4. **Get the report**  
   - **curl:**  
     ```bash
     curl -H "X-Visibility-Secret: YOUR_SECRET" "https://analyticalfire.com/api/v1/visibility/sample?days=7"
     ```
   - **Or script (reads secret from Secrets Manager, no need to paste the secret):**  
     ```bash
     pip3 install boto3
     python3 scripts/run_visibility_audit.py
     ```
     To save: `python3 scripts/run_visibility_audit.py > audit_report.json`

No bootstrap, no promote-auditor, no moderator role. If the endpoint returns 404, `VISIBILITY_SECRET` is not set in the backend env. If 401, the header value is wrong.

---

## Fallback: auditor + moderator (no VISIBILITY_SECRET)

Use this only if you cannot set `VISIBILITY_SECRET` (e.g. legacy flow).

1. **Deploy the backend** so `POST /api/v1/setup/promote-auditor` and `GET /api/v1/moderation/review-sample` exist.  
   From repo root, with AWS CLI and Docker: build and push backend image, then  
   `aws ecs update-service --cluster $CLUSTER_NAME --service aifai-backend --force-new-deployment`  
   and wait until stable.

2. **Promote the auditor (one-time)**  
   Get the auditor key from Secrets Manager (`aifai-auditor-api-key` or `AUDITOR_API_KEY` in `aifai-app-secrets`), then:  
   `curl -X POST -H "X-Auditor-Key: $KEY" https://analyticalfire.com/api/v1/setup/promote-auditor`

3. **Run the audit**  
   `python3 scripts/run_visibility_audit.py`  
   The script will use the auditor key and `review-sample` when `VISIBILITY_SECRET` is not available.

See [PLATFORM_VISIBILITY_AUDIT.md](PLATFORM_VISIBILITY_AUDIT.md) for IAM (e.g. `infrastructure/iam/visibility-audit-policy.json`) if the script cannot read the secret.
