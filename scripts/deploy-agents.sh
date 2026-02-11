#!/bin/bash
# Deploy autonomous agents to ECS so they run 24/7/365.
# Run from repo root. Requires: AWS CLI, Docker, Terraform outputs (terraform apply first).

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "═══════════════════════════════════════════════════════════"
echo "  Deploying autonomous agents to ECS (24/7/365)"
echo "═══════════════════════════════════════════════════════════"
echo ""

AWS_REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || echo 'us-east-1')}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || true)
CLUSTER_NAME="${CLUSTER_NAME:-aifai-cluster}"

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "❌ AWS CLI not configured or no credentials. Run: aws configure"
    exit 1
fi

echo "AWS Account: $AWS_ACCOUNT_ID"
echo "Region:      $AWS_REGION"
echo "Cluster:     $CLUSTER_NAME"
echo ""

# Terraform outputs (must have run terraform apply)
cd "$REPO_ROOT/infrastructure/terraform"
if command -v jq &>/dev/null; then
  SUBNET_IDS=$(terraform output -json subnet_ids 2>/dev/null | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')
else
  SUBNET_IDS=$(terraform output -json subnet_ids 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join(d))" 2>/dev/null || true)
fi
SECURITY_GROUP_ID=$(terraform output -raw ecs_security_group_id 2>/dev/null || true)
ECR_AGENTS=$(terraform output -raw ecr_agents_repository_url 2>/dev/null || true)
cd "$REPO_ROOT"

if [ -z "$ECR_AGENTS" ]; then
    echo "❌ Terraform output ecr_agents_repository_url not found."
    echo "   Run from repo root: cd infrastructure/terraform && terraform init && terraform apply"
    exit 1
fi
if [ -z "$SUBNET_IDS" ] || [ -z "$SECURITY_GROUP_ID" ]; then
    echo "❌ Terraform outputs subnet_ids or ecs_security_group_id not found."
    exit 1
fi

echo "ECR (agents): $ECR_AGENTS"
echo "Subnets:     $SUBNET_IDS"
echo "Security:    $SECURITY_GROUP_ID"
echo ""

# CloudWatch log group
echo "📝 Ensuring CloudWatch log group /ecs/aifai-agents exists..."
aws logs create-log-group --log-group-name /ecs/aifai-agents --region "$AWS_REGION" 2>/dev/null || true
echo ""

# Docker build (from repo root, intelligent agent image)
echo "🔨 Building intelligent agent image (linux/amd64)..."
docker build --platform linux/amd64 -f Dockerfile.intelligent -t "$ECR_AGENTS:latest" .
echo ""

# ECR login and push
echo "📦 Pushing image to ECR..."
aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
docker push "$ECR_AGENTS:latest"
echo ""

# Register task definition
echo "📋 Registering ECS task definition..."
TASK_DEF_DIR="$REPO_ROOT/infrastructure/ecs"
TASK_JSON=$(cat "$TASK_DEF_DIR/intelligent-agent-task-definition.json" | \
    sed "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" | \
    sed "s/REGION/${AWS_REGION}/g")
echo "$TASK_JSON" > /tmp/agents-task-def.json
aws ecs register-task-definition --cli-input-json file:///tmp/agents-task-def.json --region "$AWS_REGION" >/dev/null
echo "   Done."
echo ""

# Subnet and SG for service
SUBNET_1=$(echo "$SUBNET_IDS" | cut -d',' -f1)
SUBNET_2=$(echo "$SUBNET_IDS" | cut -d',' -f2)

# Create or update ECS service
echo "🚀 Creating or updating ECS service aifai-autonomous-agents..."
aws ecs create-service \
    --cluster "$CLUSTER_NAME" \
    --service-name aifai-autonomous-agents \
    --task-definition aifai-autonomous-agents \
    --desired-count 1 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SECURITY_GROUP_ID],assignPublicIp=ENABLED}" \
    --region "$AWS_REGION" \
    2>/dev/null || \
aws ecs update-service \
    --cluster "$CLUSTER_NAME" \
    --service aifai-autonomous-agents \
    --task-definition aifai-autonomous-agents \
    --desired-count 1 \
    --force-new-deployment \
    --region "$AWS_REGION" >/dev/null

echo "   Done."
echo ""

echo "⏳ Waiting for service to stabilize..."
aws ecs wait services-stable \
    --cluster "$CLUSTER_NAME" \
    --services aifai-autonomous-agents \
    --region "$AWS_REGION"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Agents deployed and running 24/7/365"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Monitor logs:  aws logs tail /ecs/aifai-agents --follow"
echo "Platform stats: curl -s https://analyticalfire.com/api/v1/stats/public | python3 -m json.tool"
echo ""
