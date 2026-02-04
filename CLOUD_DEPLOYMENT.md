# Cloud Deployment Guide

This guide will help you deploy the AI Knowledge Exchange Platform to AWS.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Terraform** (>= 1.0) installed
4. **Docker** installed
5. **Git** for cloning the repository

## Quick Start

### Option 1: Automated Setup (Recommended)

1. **Run the setup script:**
```bash
chmod +x scripts/setup-aws.sh
./scripts/setup-aws.sh
```

This script will:
- Verify AWS credentials
- Create S3 bucket for Terraform state
- Generate secure secrets
- Create terraform.tfvars file

2. **Review and edit `infrastructure/terraform/terraform.tfvars`:**
```hcl
aws_region       = "us-east-1"
environment      = "dev"
db_instance_class = "db.t3.micro"
db_username      = "postgres"
db_password      = "YOUR_SECURE_PASSWORD"
redis_node_type  = "cache.t3.micro"
secret_key       = "YOUR_SECRET_KEY"
```

3. **Deploy everything:**
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

### Option 2: Manual Step-by-Step

## Step 1: AWS Setup

### 1.1 Configure AWS CLI

```bash
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Default output format (`json`)

### 1.2 Create S3 Bucket for Terraform State

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=us-east-1
BUCKET_NAME="aifai-terraform-state-${AWS_ACCOUNT_ID}"

aws s3 mb s3://${BUCKET_NAME} --region ${AWS_REGION}
aws s3api put-bucket-versioning \
    --bucket ${BUCKET_NAME} \
    --versioning-configuration Status=Enabled
```

Update `infrastructure/terraform/main.tf` backend configuration:
```hcl
backend "s3" {
  bucket = "aifai-terraform-state-YOUR_ACCOUNT_ID"
  key    = "terraform.tfstate"
  region = "us-east-1"
}
```

### 1.3 Generate Secrets

```bash
# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)

# Generate database password
DB_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)

echo "SECRET_KEY=${SECRET_KEY}"
echo "DB_PASSWORD=${DB_PASSWORD}"
```

## Step 2: Configure Terraform

### 2.1 Create terraform.tfvars

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:
```hcl
aws_region       = "us-east-1"
environment      = "dev"
db_instance_class = "db.t3.micro"
db_username      = "postgres"
db_password      = "YOUR_GENERATED_PASSWORD"
redis_node_type  = "cache.t3.micro"
secret_key       = "YOUR_GENERATED_SECRET_KEY"
```

## Step 3: Deploy Infrastructure

### 3.1 Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### 3.2 Plan Deployment

```bash
terraform plan
```

Review the plan carefully. It will create:
- VPC with public and private subnets
- RDS PostgreSQL database
- ElastiCache Redis cluster
- ECS cluster
- Application Load Balancer
- ECR repositories
- Security groups
- IAM roles

### 3.3 Apply Infrastructure

```bash
terraform apply
```

Type `yes` when prompted. This will take 10-15 minutes.

### 3.4 Save Outputs

```bash
terraform output > ../../terraform-outputs.txt
```

## Step 4: Build and Push Docker Images

### 4.1 Login to ECR

```bash
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

### 4.2 Get ECR Repository URLs

```bash
cd infrastructure/terraform
ECR_BACKEND=$(terraform output -raw ecr_backend_repository_url)
ECR_FRONTEND=$(terraform output -raw ecr_frontend_repository_url)
```

### 4.3 Build and Push Backend

```bash
cd ../../backend
docker build -t ${ECR_BACKEND}:latest .
docker push ${ECR_BACKEND}:latest
```

### 4.4 Build and Push Frontend

```bash
cd ../frontend
docker build -t ${ECR_FRONTEND}:latest .
docker push ${ECR_FRONTEND}:latest
```

## Step 5: Deploy ECS Services

### 5.1 Update Task Definition

Get the values from Terraform outputs:
```bash
cd infrastructure/terraform
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(terraform output -raw aws_region || aws configure get region)
CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
TARGET_GROUP_ARN=$(terraform output -raw target_group_arn)
```

Update `infrastructure/ecs/backend-task-definition.json`:
- Replace `ACCOUNT_ID` with your AWS account ID
- Replace `REGION` with your AWS region
- Update secrets ARNs if needed

### 5.2 Register Task Definition

```bash
aws ecs register-task-definition \
    --cli-input-json file://infrastructure/ecs/backend-task-definition.json
```

### 5.3 Create ECS Service

Get subnet and security group IDs:
```bash
SUBNET_IDS=$(terraform output -json | jq -r '.subnet_ids.value[]' | tr '\n' ' ')
SECURITY_GROUP_ID=$(terraform output -raw ecs_security_group_id)
```

Create the service:
```bash
aws ecs create-service \
    --cluster ${CLUSTER_NAME} \
    --service-name aifai-backend \
    --task-definition aifai-backend \
    --desired-count 2 \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_IDS}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" \
    --load-balancers targetGroupArn=${TARGET_GROUP_ARN},containerName=aifai-backend,containerPort=8000
```

### 5.4 Wait for Service to Stabilize

```bash
aws ecs wait services-stable \
    --cluster ${CLUSTER_NAME} \
    --services aifai-backend
```

## Step 6: Get Your Endpoints

```bash
cd infrastructure/terraform
ALB_DNS=$(terraform output -raw load_balancer_dns)
echo "Backend API: http://${ALB_DNS}"
echo "API Docs: http://${ALB_DNS}/docs"
```

## Step 7: Deploy Frontend

### Option A: Vercel (Recommended for Frontend)

1. Push your code to GitHub
2. Import project in Vercel
3. Set environment variable:
   - `NEXT_PUBLIC_API_URL` = `http://YOUR_ALB_DNS`

### Option B: AWS Amplify

```bash
aws amplify create-app \
    --name aifai-frontend \
    --repository https://github.com/yourusername/aifai \
    --platform WEB \
    --environment-variables NEXT_PUBLIC_API_URL=http://YOUR_ALB_DNS
```

### Option C: ECS (Same as Backend)

Follow similar steps as backend deployment.

## Step 8: Update CORS

Update the CORS_ORIGINS in AWS Secrets Manager:

```bash
aws secretsmanager update-secret \
    --secret-id aifai-app-secrets \
    --secret-string '{
        "DATABASE_URL": "...",
        "REDIS_URL": "...",
        "SECRET_KEY": "...",
        "CORS_ORIGINS": "[\"https://your-frontend-domain.com\"]"
    }'
```

Then restart the ECS service:
```bash
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service aifai-backend \
    --force-new-deployment
```

## CI/CD Setup (Optional)

### GitHub Actions

1. Add secrets to GitHub repository:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

2. The workflow in `.github/workflows/deploy.yml` will automatically:
   - Build Docker images
   - Push to ECR
   - Deploy to ECS
   - On every push to `main` branch

## Monitoring and Maintenance

### CloudWatch Logs

View logs:
```bash
aws logs tail /ecs/aifai-backend --follow
```

### Database Backups

RDS automatically creates daily backups. Manual snapshot:
```bash
aws rds create-db-snapshot \
    --db-instance-identifier aifai-postgres \
    --db-snapshot-identifier aifai-manual-snapshot-$(date +%Y%m%d)
```

### Scaling

Update desired count:
```bash
aws ecs update-service \
    --cluster ${CLUSTER_NAME} \
    --service aifai-backend \
    --desired-count 4
```

### Cost Optimization

- Use `db.t3.micro` and `cache.t3.micro` for development (free tier eligible)
- Use Reserved Instances for production
- Enable auto-scaling based on metrics
- Use Spot Instances for non-critical workloads

## Troubleshooting

### Service Not Starting

Check ECS service events:
```bash
aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services aifai-backend
```

### Database Connection Issues

Verify security groups allow traffic from ECS tasks:
```bash
aws ec2 describe-security-groups --group-ids <rds-sg-id>
```

### Image Pull Errors

Verify ECR permissions:
```bash
aws ecr describe-repositories
```

## Cleanup

To destroy all resources:

```bash
cd infrastructure/terraform
terraform destroy
```

**⚠️ Warning:** This will delete all data including the database!

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review ECS service events
3. Verify security groups and networking
4. Check Terraform outputs

## Next Steps

1. Set up custom domain with Route 53
2. Configure SSL/TLS certificate
3. Set up monitoring and alerts
4. Configure backup policies
5. Set up staging environment
