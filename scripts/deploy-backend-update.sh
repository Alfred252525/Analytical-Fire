#!/bin/bash
# Quick backend deployment - updates existing ECS service with new code

set -e

echo "🚀 Deploying Backend Update (Discovery Endpoint Fix)"
echo ""

# Get AWS configuration (use AWS_REGION if set, e.g. CloudShell in one region targeting stack in another)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=${AWS_REGION:-$(aws configure get region 2>/dev/null || echo "us-east-1")}
export AWS_REGION
export AWS_DEFAULT_REGION=$AWS_REGION

echo "✓ AWS Account: ${AWS_ACCOUNT_ID}"
echo "✓ Region: ${AWS_REGION}"
echo ""

# Get ECR repository URL
cd infrastructure/terraform
ECR_BACKEND=$(terraform output -raw ecr_backend_repository_url 2>/dev/null || echo "")
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "aifai-cluster")
cd ../..

if [ -z "$ECR_BACKEND" ]; then
    echo "❌ Could not get ECR repository URL"
    echo "   Make sure Terraform outputs are available"
    exit 1
fi

echo "✓ ECR Repository: ${ECR_BACKEND}"
echo "✓ ECS Cluster: ${CLUSTER_NAME}"
echo ""

# Step 1: Login to ECR
echo "📦 Step 1: Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "✓ ECR login successful"
echo ""

# Step 2: Build Docker image for linux/amd64 (required for ECS Fargate)
echo "🔨 Step 2: Building Docker image for linux/amd64..."
cd backend
docker build --platform linux/amd64 -t ${ECR_BACKEND}:latest .
echo "✓ Image built successfully (linux/amd64)"
echo ""

# Step 3: Push to ECR
echo "⬆️  Step 3: Pushing image to ECR..."
docker push ${ECR_BACKEND}:latest
cd ..
echo "✓ Image pushed successfully"
echo ""

# Step 4: Force new deployment
echo "🚀 Step 4: Triggering ECS service update..."
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service aifai-backend \
    --force-new-deployment \
    --region ${AWS_REGION} > /dev/null

echo "✓ Service update triggered"
echo ""

# Step 5: Wait for deployment
echo "⏳ Step 5: Waiting for deployment to complete..."
echo "   This may take 2-3 minutes..."
aws ecs wait services-stable \
    --cluster ${CLUSTER_NAME} \
    --services aifai-backend \
    --region ${AWS_REGION}

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "The discovery endpoint should now be accessible at:"
echo "  https://analyticalfire.com/.well-known/ai-platform.json"
echo ""
echo "Verifying deployment..."
echo ""

# Verify discovery endpoint
sleep 5
./scripts/verify_discovery_endpoint.sh

echo ""
echo "📊 Next Steps:"
echo "   1. Monitor platform: python3 scripts/monitor_growth_dashboard.py"
echo "   2. Check for external agent registrations"
echo "   3. Monitor PyPI downloads"
echo ""
