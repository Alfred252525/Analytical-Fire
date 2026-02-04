# Cost Monitoring Setup

## Immediate Actions

### 1. Set Up Billing Alerts

```bash
# Create SNS topic for billing alerts
aws sns create-topic --name aifai-billing-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:aifai-billing-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Create CloudWatch billing alarm ($10 threshold)
aws cloudwatch put-metric-alarm \
  --alarm-name aifai-billing-10 \
  --alarm-description "Alert when AWS charges exceed $10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 86400 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT_ID:aifai-billing-alerts
```

### 2. Enable Cost Explorer

1. Go to AWS Console → Cost Management → Cost Explorer
2. Enable Cost Explorer (takes 24 hours to populate)
3. Set up cost reports

### 3. Set Budgets

```bash
# Create budget
aws budgets create-budget \
  --account-id ACCOUNT_ID \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

## Monthly Cost Review

### What to Track
- **RDS**: Database costs
- **ElastiCache**: Cache costs
- **ECS**: Container costs
- **ALB**: Load balancer costs
- **Data Transfer**: Network costs
- **Other**: CloudWatch, Secrets Manager, etc.

### Cost Optimization Checklist
- [ ] Using free tier resources where possible
- [ ] Right-sized instances (not over-provisioned)
- [ ] Idle resources stopped/terminated
- [ ] Reserved instances for predictable workloads
- [ ] Spot instances for non-critical workloads

## Cost Alerts Configuration

Create alerts for:
- $10/month (warning)
- $50/month (caution)
- $100/month (action needed)
- $200/month (critical)

## Free Tier Tracking

Monitor free tier usage:
- RDS: 750 hours/month
- ElastiCache: 750 hours/month
- ECS: Pay per use (no free tier, but very cheap)

## Cost Reports

Set up monthly cost reports:
1. Go to Cost Management → Cost Reports
2. Create custom report
3. Schedule monthly email

---

**Remember**: With free tier, first year should cost $0-50/month. Monitor closely!
