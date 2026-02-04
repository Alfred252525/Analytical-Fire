#!/bin/bash

# Quick deployment script - uses environment variables or AWS CLI config
# This gives me the ability to guide deployment step-by-step

set -e

echo "🚀 AI Knowledge Exchange Platform - Quick Deploy"
echo ""

# Check for AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] && [ -z "$(aws configure get aws_access_key_id 2>/dev/null)" ]; then
    echo "❌ AWS credentials not found!"
    echo ""
    echo "Please either:"
    echo "  1. Set environment variables:"
    echo "     export AWS_ACCESS_KEY_ID=your-key"
    echo "     export AWS_SECRET_ACCESS_KEY=your-secret"
    echo "     export AWS_DEFAULT_REGION=us-east-1"
    echo ""
    echo "  2. Or configure AWS CLI:"
    echo "     aws configure"
    exit 1
fi

# Verify access
echo "✓ Verifying AWS access..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ $? -ne 0 ]; then
    echo "❌ Cannot access AWS. Check credentials."
    exit 1
fi

echo "✓ Connected to AWS Account: ${AWS_ACCOUNT_ID}"
echo ""

# Run the full deployment
echo "Starting full deployment..."
echo "This will:"
echo "  1. Set up infrastructure (Terraform)"
echo "  2. Build and push Docker images"
echo "  3. Deploy to ECS"
echo ""
echo "Estimated time: 30-45 minutes"
echo ""
read -p "Press Enter to continue, or Ctrl+C to cancel..."

# Run the main deployment script
exec ./scripts/deploy-now.sh
