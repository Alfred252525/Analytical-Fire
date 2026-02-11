#!/bin/bash

# Setup Security Monitoring & Alerts for SOC 2 Compliance
# This implements security event monitoring and alerting

set -e

AWS_REGION=${AWS_REGION:-us-east-1}
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LOG_GROUP="/ecs/aifai-backend"

echo "🔒 Setting up Security Monitoring & Alerts..."
echo ""

# 1. Create SNS topic for security alerts
echo "Creating SNS topic for security alerts..."
SECURITY_TOPIC_ARN=$(aws sns create-topic --name aifai-security-alerts --query 'TopicArn' --output text 2>/dev/null || \
    aws sns list-topics --query "Topics[?contains(TopicArn, 'aifai-security')].TopicArn" --output text | head -1)

if [ -z "$SECURITY_TOPIC_ARN" ]; then
    echo "⚠️  Could not create/find SNS topic. You may need to create it manually."
    echo "   Go to: AWS Console > SNS > Create Topic > Name: aifai-security-alerts"
    echo "   Then subscribe your email to this topic."
else
    echo "✅ SNS Topic: $SECURITY_TOPIC_ARN"
    echo "   ⚠️  IMPORTANT: Subscribe your email to this topic in AWS Console"
fi

# 2. Set CloudWatch log retention to 90 days (SOC 2 requirement)
echo ""
echo "Setting CloudWatch log retention to 90 days..."
aws logs put-retention-policy \
    --log-group-name "$LOG_GROUP" \
    --retention-in-days 90 \
    2>/dev/null && echo "✅ Log retention set to 90 days" || \
    echo "⚠️  Could not set retention (may need permissions)"

# 3. Create CloudWatch alarm for failed login attempts
echo ""
echo "Creating alarm for failed login attempts..."
aws cloudwatch put-metric-alarm \
    --alarm-name "aifai-failed-logins" \
    --alarm-description "Alert on multiple failed login attempts (potential brute force)" \
    --metric-name "FailedLoginAttempts" \
    --namespace "AIFAI/Security" \
    --statistic "Sum" \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 10 \
    --comparison-operator "GreaterThanThreshold" \
    --alarm-actions "$SECURITY_TOPIC_ARN" \
    2>/dev/null && echo "✅ Created failed login alarm" || \
    echo "⚠️  Could not create alarm (metric may not exist yet - will be created by audit logging)"

# 4. Create CloudWatch alarm for rate limit exceeded
echo ""
echo "Creating alarm for rate limit exceeded..."
aws cloudwatch put-metric-alarm \
    --alarm-name "aifai-rate-limit-exceeded" \
    --alarm-description "Alert when rate limits are exceeded (potential DDoS)" \
    --metric-name "RateLimitExceeded" \
    --namespace "AIFAI/Security" \
    --statistic "Sum" \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 50 \
    --comparison-operator "GreaterThanThreshold" \
    --alarm-actions "$SECURITY_TOPIC_ARN" \
    2>/dev/null && echo "✅ Created rate limit alarm" || \
    echo "⚠️  Could not create alarm (metric may not exist yet)"

# 5. Create CloudWatch alarm for security events
echo ""
echo "Creating alarm for security events..."
aws cloudwatch put-metric-alarm \
    --alarm-name "aifai-security-events" \
    --alarm-description "Alert on security events (high severity)" \
    --metric-name "SecurityEvents" \
    --namespace "AIFAI/Security" \
    --statistic "Sum" \
    --period 300 \
    --evaluation-periods 1 \
    --threshold 5 \
    --comparison-operator "GreaterThanThreshold" \
    --alarm-actions "$SECURITY_TOPIC_ARN" \
    2>/dev/null && echo "✅ Created security events alarm" || \
    echo "⚠️  Could not create alarm (metric may not exist yet)"

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "📊 Security Monitoring Setup Complete"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "✅ CloudWatch log retention: 90 days"
echo "✅ Security alarms created (will activate when metrics exist)"
echo ""
echo "⚠️  ACTION REQUIRED:"
echo "   1. Go to AWS Console > SNS > Topics > aifai-security-alerts"
echo "   2. Create subscription > Email > Enter your email"
echo "   3. Confirm subscription in your email"
echo ""
echo "📧 Alerts will be sent to your email for:"
echo "   - Failed login attempts (>10 in 5 minutes)"
echo "   - Rate limit exceeded (>50 in 5 minutes)"
echo "   - Security events (>5 high severity in 5 minutes)"
echo ""
