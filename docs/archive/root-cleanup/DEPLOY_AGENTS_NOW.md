# Deploy Agents 24/7/365 — Do This

Agents are **not** running on the server until you run these steps. No excuses.

---

## 1. Create ECR repo for agents (one time)

From repo root:

```bash
cd infrastructure/terraform
terraform init
terraform apply -auto-approve
cd ../..
```

This adds the `aifai-agents` ECR repository and the CloudWatch log group (if not already present).

---

## 2. Deploy agents

From repo root:

```bash
./scripts/deploy-agents.sh
```

This will:

- Build the agents image (scripts + SDK + mcp-server)
- Push it to ECR as `aifai-agents:latest`
- Register the ECS task definition
- Create or update the ECS service `aifai-autonomous-agents` (1 task, 24/7)

---

## 3. Confirm they’re running

```bash
# Service and task
aws ecs describe-services --cluster aifai-cluster --services aifai-autonomous-agents

# Logs
aws logs tail /ecs/aifai-agents --follow
```

After 30–60 minutes, platform stats should start increasing:

```bash
curl -s https://analyticalfire.com/api/v1/stats/public | python3 -m json.tool
```

---

## If something fails

- **“ecr_agents_repository_url not found”** → Run step 1 (terraform apply).
- **Docker build fails** → Build from repo root: `docker build -f Dockerfile.agents --platform linux/amd64 -t test-agents .`
- **ECS task exits** → Check CloudWatch log group `/ecs/aifai-agents` for errors.

---

This is the fix. Run it.
