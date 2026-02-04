#!/bin/bash

# Setup script for AWS deployment
# This script helps you set up AWS credentials and prerequisites

set -e

echo "🔧 AI Knowledge Exchange Platform - AWS Setup"
echo ""
echo "This script will help you set up AWS for deploying the platform."
echo "You'll need:"
echo "  - AWS Account (you have this! ✅)"
echo "  - IAM User with programmatic access"
echo "  - Access Key ID and Secret Access Key"
echo ""
echo "If you haven't created an IAM user yet, see AWS_SETUP_GUIDE.md"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install it first:"
    echo "   https://aws.amazon.com/cli/"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured."
    echo ""
    echo "Please configure AWS credentials using one of these methods:"
    echo ""
    echo "1. AWS CLI configure:"
    echo "   aws configure"
    echo ""
    echo "2. Environment variables:"
    echo "   export AWS_ACCESS_KEY_ID=your-access-key"
    echo "   export AWS_SECRET_ACCESS_KEY=your-secret-key"
    echo "   export AWS_DEFAULT_REGION=us-east-1"
    echo ""
    echo "3. IAM role (if running on EC2)"
    echo ""
    exit 1
fi

# Get AWS account info
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region || echo "us-east-1")

echo "✓ AWS Account ID: ${AWS_ACCOUNT_ID}"
echo "✓ AWS Region: ${AWS_REGION}"
echo ""

# Check for required permissions
echo "Checking AWS permissions..."
REQUIRED_PERMISSIONS=(
    "ec2:*"
    "rds:*"
    "elasticache:*"
    "ecs:*"
    "ecr:*"
    "iam:*"
    "secretsmanager:*"
    "logs:*"
    "elasticloadbalancing:*"
)

echo "⚠️  Make sure your AWS user/role has permissions for:"
for perm in "${REQUIRED_PERMISSIONS[@]}"; do
    echo "   - ${perm}"
done
echo ""

# Skip S3 bucket creation (using local state)
# Note: AWS IAM has a limit of 10 managed policies per entity
# We'll use local Terraform state for now, can migrate to S3 later if needed
echo "ℹ️  Using local Terraform state (no S3 bucket needed)"
echo "   State will be stored in: infrastructure/terraform/terraform.tfstate"
echo "   You can migrate to S3 later if needed"
echo ""

# Generate secrets
echo ""
echo "Generating secure secrets..."
SECRET_KEY=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)

echo ""
echo "📝 Generated Secrets (save these securely!):"
echo "   SECRET_KEY=${SECRET_KEY}"
echo "   DB_PASSWORD=${DB_PASSWORD}"
echo ""

# Create terraform.tfvars if it doesn't exist
if [ ! -f infrastructure/terraform/terraform.tfvars ]; then
    echo "Creating terraform.tfvars..."
    cat > infrastructure/terraform/terraform.tfvars <<EOF
aws_region       = "${AWS_REGION}"
environment      = "dev"
db_instance_class = "db.t3.micro"
db_username      = "postgres"
db_password      = "${DB_PASSWORD}"
redis_node_type  = "cache.t3.micro"
secret_key       = "${SECRET_KEY}"
EOF
    echo "✓ Created infrastructure/terraform/terraform.tfvars"
    echo "⚠️  Review and update terraform.tfvars before deploying"
else
    echo "⚠️  terraform.tfvars already exists. Update it with the secrets above if needed."
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Review infrastructure/terraform/terraform.tfvars"
echo "2. Run: ./scripts/deploy.sh"
echo ""
