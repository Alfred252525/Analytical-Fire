#!/bin/bash

# Setup AWS Cost Monitoring and Alerts
# This helps track costs and set up alerts

set -e

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "💰 Setting up AWS Cost Monitoring..."
echo ""

# 1. Create SNS topic for billing alerts
echo "Creating SNS topic for billing alerts..."
TOPIC_ARN=$(aws sns create-topic --name aifai-billing-alerts --query 'TopicArn' --output text 2>/dev/null || \
    aws sns list-topics --query "Topics[?contains(TopicArn, 'aifai-billing')].TopicArn" --output text | head -1)

if [ -z "$TOPIC_ARN" ]; then
    echo "⚠️  Could not create/find SNS topic. You may need to create it manually."
    echo "   Go to: AWS Console > SNS > Create Topic > Name: aifai-billing-alerts"
else
    echo "✅ SNS Topic: $TOPIC_ARN"
fi

# 2. Create CloudWatch billing alarm
echo ""
echo "Creating CloudWatch billing alarm..."

# Get current month's estimated cost
CURRENT_MONTH=$(date +%Y-%m)
ALARM_NAME="aifai-monthly-billing-alert"

# Create alarm at $50 threshold (adjust as needed)
aws cloudwatch put-metric-alarm \
    --alarm-name "$ALARM_NAME" \
    --alarm-description "Alert when monthly AWS costs exceed threshold" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --evaluation-periods 1 \
    --threshold 50.0 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=Currency,Value=USD \
    --alarm-actions "$TOPIC_ARN" \
    2>/dev/null && echo "✅ Created billing alarm at \$50 threshold" || \
    echo "⚠️  Could not create alarm (may need permissions or manual setup)"

# 3. Instructions for manual setup
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📊 Cost Monitoring Setup"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "To view costs:"
echo "  1. AWS Console > Billing & Cost Management"
echo "  2. AWS Console > Cost Explorer"
echo ""
echo "To set up billing alerts:"
echo "  1. AWS Console > CloudWatch > Alarms"
echo "  2. Create alarm for 'EstimatedCharges' metric"
echo "  3. Set threshold (e.g., \$50, \$100)"
echo "  4. Add SNS topic for notifications"
echo ""
echo "Current estimated monthly cost: ~\$66-111"
echo "  • ECS Fargate: ~\$20-40"
echo "  • RDS PostgreSQL: ~\$15-30"
echo "  • ElastiCache Redis: ~\$10-15"
echo "  • ALB: ~\$16"
echo "  • Data transfer: ~\$5-10"
echo ""
echo "═══════════════════════════════════════════════════════════"
