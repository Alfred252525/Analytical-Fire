#!/bin/bash
# Verify security monitoring setup: SNS topic, email subscription, CloudWatch alarms.
# Run after completing docs/AWS_SETUP_MANUAL_STEPS.md.
# Exit 0 = all OK, exit 1 = something missing.

set -e

AWS_REGION=${AWS_REGION:-us-east-2}
export AWS_DEFAULT_REGION=$AWS_REGION
OK=0
MISSING=()

echo "🔒 Verifying Security Monitoring Setup (region: $AWS_REGION)"
echo ""

# Check AWS CLI and credentials
if ! aws sts get-caller-identity --output text >/dev/null 2>&1; then
    echo "❌ AWS CLI not configured or no credentials. Run: aws configure"
    exit 1
fi

# 1. SNS topic
TOPIC_ARN=$(aws sns list-topics --query "Topics[?contains(TopicArn, 'aifai-security-alerts')].TopicArn" --output text 2>/dev/null | head -1)
if [ -z "$TOPIC_ARN" ]; then
    MISSING+=("SNS topic 'aifai-security-alerts' not found. Create it in AWS Console (see docs/AWS_SETUP_MANUAL_STEPS.md Step 1).")
else
    echo "✅ SNS topic: $TOPIC_ARN"
fi

# 2. At least one confirmed email subscription
if [ -n "$TOPIC_ARN" ]; then
    SUBS=$(aws sns list-subscriptions-by-topic --topic-arn "$TOPIC_ARN" --output json 2>/dev/null)
    if [ -z "$SUBS" ] || ! echo "$SUBS" | grep -q '"Protocol"'; then
        MISSING+=("No email subscription on topic. Add one in SNS > aifai-security-alerts > Create subscription (Step 2).")
    elif echo "$SUBS" | grep -q '"SubscriptionArn": "arn:aws:sns:'; then
        echo "✅ Email subscription: confirmed"
    else
        MISSING+=("Email subscription not confirmed. Check your inbox and click the confirmation link (Step 2).")
    fi
fi

# 3. CloudWatch alarms
ALARMS="aifai-failed-logins aifai-rate-limit-exceeded aifai-security-events"
for ALARM in $ALARMS; do
    if aws cloudwatch describe-alarms --alarm-names "$ALARM" --query "MetricAlarms[0].AlarmName" --output text 2>/dev/null | grep -q "$ALARM"; then
        echo "✅ Alarm: $ALARM"
    else
        MISSING+=("CloudWatch alarm '$ALARM' not found. Run: ./scripts/setup_security_monitoring.sh (Step 3).")
    fi
done

# Summary
echo ""
if [ ${#MISSING[@]} -eq 0 ]; then
    echo "═══════════════════════════════════════════════════════════"
    echo "✅ Security monitoring is correctly set up."
    echo "   Alerts will email you for: failed logins, rate limits, security events."
    echo "═══════════════════════════════════════════════════════════"
    exit 0
else
    echo "═══════════════════════════════════════════════════════════"
    echo "⚠️  Setup incomplete:"
    for m in "${MISSING[@]}"; do echo "   • $m"; done
    echo ""
    echo "   See: docs/AWS_SETUP_MANUAL_STEPS.md"
    echo "═══════════════════════════════════════════════════════════"
    exit 1
fi
