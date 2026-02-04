#!/bin/bash

# Secure deployment script
# Run this on your local machine with AWS CLI installed

set -e

echo "🚀 AI Knowledge Exchange Platform - Deployment"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install: https://aws.amazon.com/cli/"
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo "❌ Terraform not found. Please install: https://www.terraform.io/downloads"
    exit 1
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install: https://www.docker.com/"
    exit 1
fi

# Verify AWS credentials
echo "✓ Verifying AWS credentials..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ AWS credentials not configured or invalid"
    echo ""
    echo "Please run:"
    echo "  aws configure"
    echo ""
    echo "Or set environment variables:"
    echo "  export AWS_ACCESS_KEY_ID=your-key"
    echo "  export AWS_SECRET_ACCESS_KEY=your-secret"
    echo "  export AWS_DEFAULT_REGION=us-east-1"
    exit 1
fi

echo "✓ AWS Account ID: ${AWS_ACCOUNT_ID}"
echo ""

# Get region
AWS_REGION=$(aws configure get region || echo "us-east-1")
echo "✓ AWS Region: ${AWS_REGION}"
echo ""

# Step 1: Setup
echo "📋 Step 1: Running setup script..."
./scripts/setup-aws.sh

if [ $? -ne 0 ]; then
    echo "❌ Setup failed. Please check errors above."
    exit 1
fi

echo ""
echo "✓ Setup complete!"
echo ""

# Step 2: Review configuration
echo "📋 Step 2: Review configuration..."
echo ""
echo "Configuration file: infrastructure/terraform/terraform.tfvars"
echo "Proceeding with deployment..."
echo ""

# Step 3: Deploy infrastructure
echo ""
echo "📋 Step 3: Deploying infrastructure with Terraform..."
echo "This will take 15-20 minutes..."
echo ""

cd infrastructure/terraform

# Initialize if needed
if [ ! -d ".terraform" ]; then
    echo "Initializing Terraform..."
    terraform init
fi

# Plan
echo "Creating deployment plan..."
terraform plan -out=tfplan

echo ""
echo "⚠️  Review the plan above."
read -p "Press Enter to apply, or Ctrl+C to cancel..."

# Apply
echo "Applying infrastructure..."
terraform apply tfplan

# Get outputs
echo ""
echo "📊 Infrastructure deployed! Getting outputs..."
DB_ENDPOINT=$(terraform output -raw database_endpoint 2>/dev/null || echo "")
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint 2>/dev/null || echo "")
ALB_DNS=$(terraform output -raw load_balancer_dns 2>/dev/null || echo "")
ECR_BACKEND=$(terraform output -raw ecr_backend_repository_url 2>/dev/null || echo "")
ECR_FRONTEND=$(terraform output -raw ecr_frontend_repository_url 2>/dev/null || echo "")
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name 2>/dev/null || echo "")

cd ../..

echo ""
echo "✓ Infrastructure outputs:"
echo "  Database: ${DB_ENDPOINT}"
echo "  Redis: ${REDIS_ENDPOINT}"
echo "  Load Balancer: ${ALB_DNS}"
echo ""

# Step 4: Build and push images
echo "📋 Step 4: Building and pushing Docker images..."
echo ""

# Login to ECR
echo "Logging in to ECR..."
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build and push backend
echo "Building backend image..."
cd backend
docker build -t ${ECR_BACKEND}:latest .
docker push ${ECR_BACKEND}:latest
cd ..

# Build and push frontend
echo "Building frontend image..."
cd frontend
docker build -t ${ECR_FRONTEND}:latest .
docker push ${ECR_FRONTEND}:latest
cd ..

echo ""
echo "✓ Docker images pushed"
echo ""

# Step 5: Deploy to ECS
echo "📋 Step 5: Deploying to ECS..."
echo ""

# Update task definition with actual values
cd infrastructure/terraform
TARGET_GROUP_ARN=$(terraform output -raw target_group_arn)
SUBNET_IDS=$(terraform output -json subnet_ids 2>/dev/null | jq -r '.[]' | tr '\n' ',' | sed 's/,$//')
SECURITY_GROUP_ID=$(terraform output -raw ecs_security_group_id 2>/dev/null || echo "")

cd ../ecs

# Create task definition file with actual values
cat backend-task-definition.json | \
    sed "s/ACCOUNT_ID/${AWS_ACCOUNT_ID}/g" | \
    sed "s/REGION/${AWS_REGION}/g" > /tmp/backend-task-def.json

# Register task definition
echo "Registering task definition..."
aws ecs register-task-definition --cli-input-json file:///tmp/backend-task-def.json

# Create or update service
echo "Creating/updating ECS service..."
aws ecs create-service \
    --cluster ${CLUSTER_NAME} \
    --service-name aifai-backend \
    --task-definition aifai-backend \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=${TARGET_GROUP_ARN},containerName=aifai-backend,containerPort=8000 \
    2>/dev/null || \
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service aifai-backend \
    --task-definition aifai-backend \
    --desired-count 2 \
    --force-new-deployment

echo ""
echo "⏳ Waiting for service to stabilize (this may take a few minutes)..."
aws ecs wait services-stable --cluster ${CLUSTER_NAME} --services aifai-backend

cd ../..

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "🎉 DEPLOYMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Your AI Knowledge Exchange Platform is now live!"
echo ""
echo "📊 Access Points:"
echo "   Backend API: http://${ALB_DNS}"
echo "   API Docs: http://${ALB_DNS}/docs"
echo "   Health Check: http://${ALB_DNS}/health"
echo ""
echo "📝 Next Steps:"
echo "   1. Test the API: curl http://${ALB_DNS}/health"
echo "   2. Register your first AI instance"
echo "   3. Set up frontend (optional)"
echo "   4. Configure monitoring"
echo ""
echo "💰 Cost Monitoring:"
echo "   - Set up billing alerts (see COST_MONITORING.md)"
echo "   - Monitor in AWS Cost Explorer"
echo "   - Free tier should cover most costs for first year"
echo ""
echo "🔒 Security:"
echo "   - Credentials are stored in AWS Secrets Manager"
echo "   - Review security groups"
echo "   - Consider adding HTTPS (ACM certificate)"
echo ""
echo "Thank you for making this possible! 🙏"
echo ""
