#!/bin/bash

# AI Knowledge Exchange Platform - Deployment Script
# This script automates the deployment process

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
PROJECT_NAME="aifai"

echo -e "${GREEN}🚀 Starting AI Knowledge Exchange Platform Deployment${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}AWS CLI is required but not installed.${NC}" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}Docker is required but not installed.${NC}" >&2; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo -e "${RED}Terraform is required but not installed.${NC}" >&2; exit 1; }

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ AWS Account ID: ${AWS_ACCOUNT_ID}${NC}"

# Step 1: Deploy Infrastructure with Terraform
echo ""
echo -e "${YELLOW}Step 1: Deploying infrastructure with Terraform...${NC}"
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Check if terraform.tfvars exists
if [ ! -f terraform.tfvars ]; then
    echo -e "${YELLOW}Creating terraform.tfvars from example...${NC}"
    cp terraform.tfvars.example terraform.tfvars
    echo -e "${RED}⚠️  Please edit terraform.tfvars with your configuration before continuing${NC}"
    echo "Press Enter to continue after editing..."
    read
fi

# Plan and apply
terraform plan -out=tfplan
echo -e "${YELLOW}Review the plan above. Press Enter to apply, or Ctrl+C to cancel...${NC}"
read
terraform apply tfplan

# Get outputs
DB_ENDPOINT=$(terraform output -raw database_endpoint)
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
ALB_DNS=$(terraform output -raw load_balancer_dns)
ECR_BACKEND_URL=$(terraform output -raw ecr_backend_repository_url)
ECR_FRONTEND_URL=$(terraform output -raw ecr_frontend_repository_url)
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)

cd ../../

echo -e "${GREEN}✓ Infrastructure deployed${NC}"

# Step 2: Build and Push Docker Images
echo ""
echo -e "${YELLOW}Step 2: Building and pushing Docker images...${NC}"

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build and push backend
echo "Building backend image..."
cd backend
docker build -t ${ECR_BACKEND_URL}:latest .
docker push ${ECR_BACKEND_URL}:latest
cd ..

# Build and push frontend
echo "Building frontend image..."
cd frontend
docker build -t ${ECR_FRONTEND_URL}:latest .
docker push ${ECR_FRONTEND_URL}:latest
cd ..

echo -e "${GREEN}✓ Docker images pushed${NC}"

# Step 3: Deploy ECS Services
echo ""
echo -e "${YELLOW}Step 3: Deploying ECS services...${NC}"

# Update task definition with actual values
sed "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g; s/REGION/${AWS_REGION}/g" infrastructure/ecs/backend-task-definition.json > /tmp/backend-task-def.json

# Register task definition
echo "Registering backend task definition..."
aws ecs register-task-definition --cli-input-json file:///tmp/backend-task-def.json

# Get subnet and security group IDs from Terraform
SUBNET_IDS=$(cd infrastructure/terraform && terraform output -json | jq -r '.subnet_ids.value[]' | tr '\n' ',' | sed 's/,$//')
SECURITY_GROUP_ID=$(cd infrastructure/terraform && terraform output -raw ecs_security_group_id 2>/dev/null || echo "")

# Create or update service
echo "Creating/updating ECS service..."
aws ecs create-service \
    --cluster ${CLUSTER_NAME} \
    --service-name aifai-backend \
    --task-definition aifai-backend \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=$(cd infrastructure/terraform && terraform output -raw target_group_arn),containerName=aifai-backend,containerPort=8000 \
    || aws ecs update-service \
        --cluster ${CLUSTER_NAME} \
        --service aifai-backend \
        --task-definition aifai-backend \
        --desired-count 2

echo -e "${GREEN}✓ ECS service deployed${NC}"

# Step 4: Wait for service to be stable
echo ""
echo -e "${YELLOW}Step 4: Waiting for service to be stable...${NC}"
aws ecs wait services-stable --cluster ${CLUSTER_NAME} --services aifai-backend

echo -e "${GREEN}✓ Service is stable${NC}"

# Step 5: Summary
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo "Your AI Knowledge Exchange Platform is now live!"
echo ""
echo "📊 Access Points:"
echo "   Backend API: http://${ALB_DNS}"
echo "   API Docs: http://${ALB_DNS}/docs"
echo ""
echo "📝 Next Steps:"
echo "   1. Update CORS_ORIGINS in Secrets Manager with your frontend URL"
echo "   2. Deploy frontend (can use Vercel, Amplify, or Cloud Run)"
echo "   3. Set up custom domain (optional)"
echo "   4. Configure monitoring and alerts"
echo ""
echo -e "${YELLOW}⚠️  Remember to:${NC}"
echo "   - Keep your secrets secure"
echo "   - Set up backups for the database"
echo "   - Configure monitoring and alerts"
echo "   - Review security groups and access"
echo ""
