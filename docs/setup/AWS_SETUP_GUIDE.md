# AWS Account Setup Guide

This guide will help you set up AWS access for deploying the AI Knowledge Exchange Platform.

## Step 1: Create IAM User for Deployment

**Important**: Never use root AWS credentials. Create a dedicated IAM user.

### Via AWS Console:

1. Go to IAM → Users → Create User
2. Username: `aifai-deployment` (or your choice)
3. Enable "Provide user access to the management console" (optional, for manual access)
4. **Enable "Access key - Programmatic access"** (required for CLI/Terraform)

### Attach Policies:

Attach these managed policies:
- `AmazonEC2FullAccess` (for VPC, networking)
- `AmazonRDSFullAccess` (for database)
- `AmazonElastiCacheFullAccess` (for Redis)
- `AmazonECS_FullAccess` (for container service)
- `AmazonEC2ContainerRegistryFullAccess` (for Docker images)
- `IAMFullAccess` (for creating roles - can be restricted later)
- `SecretsManagerReadWrite` (for secrets)
- `CloudWatchLogsFullAccess` (for logging)
- `ElasticLoadBalancingFullAccess` (for load balancer)
- `AmazonS3FullAccess` (for Terraform state - can be restricted to one bucket)

**Or** create a custom policy with least privilege (recommended - see "Least Privilege Policy" section below).

### Save Credentials:

After creation, you'll get:
- **Access Key ID**: `AKIA...`
- **Secret Access Key**: `...` (save this immediately, you can't view it again!)

## Step 2: Configure AWS CLI

```bash
aws configure
```

Enter:
- AWS Access Key ID: [from Step 1]
- AWS Secret Access Key: [from Step 1]
- Default region: `us-east-1` (or your preferred region)
- Default output format: `json`

Test it:
```bash
aws sts get-caller-identity
```

Should return your account ID and user ARN.

## Step 3: Set Up Free Credits

### AWS Free Tier
- Already active for new accounts
- Includes: 750 hours/month of t2.micro/t3.micro instances
- RDS: 750 hours/month of db.t2.micro/db.t3.micro
- ElastiCache: 750 hours/month of cache.t2.micro/cache.t3.micro
- **Total value**: ~$200 in credits over 12 months

### Additional Credits

1. **AWS Activate (Startups)**
   - $1,000-$10,000 in credits
   - Requires: Startup validation
   - Apply at: https://aws.amazon.com/activate/

2. **AWS Credits Program**
   - Various amounts based on programs
   - Check: https://aws.amazon.com/credits/

3. **NVIDIA Inception / AWS Credits**
   - If you're doing AI/ML work
   - Can provide additional credits
   - Check NVIDIA Inception program

## Step 4: Set Up Cost Alerts

**Important**: Set up billing alerts to avoid surprises!

1. Go to Billing → Preferences
2. Enable "Receive Billing Alerts"
3. Go to CloudWatch → Billing Alarms
4. Create alarm:
   - Threshold: $10 (or your comfort level)
   - Email: Your email

## Step 5: Verify Setup

Run our setup script:
```bash
./scripts/setup-aws.sh
```

This will:
- Verify AWS credentials
- Check permissions
- Create S3 bucket for Terraform state
- Generate secure secrets
- Create terraform.tfvars

## Step 6: Deploy!

```bash
./scripts/deploy.sh
```

## Least Privilege IAM Policy (Recommended)

Instead of using full-access policies, create a custom policy with only the permissions needed:

1. Go to IAM → Policies → Create Policy
2. Choose JSON tab
3. Paste this policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "rds:*",
        "elasticache:*",
        "ecs:*",
        "ecr:*",
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PassRole",
        "iam:GetRole",
        "iam:ListRoles",
        "secretsmanager:*",
        "logs:*",
        "elasticloadbalancing:*",
        "s3:CreateBucket",
        "s3:GetBucketLocation",
        "s3:PutBucketVersioning",
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": "*"
    }
  ]
}
```

4. Name it: `AIFAI-Deployment-Policy`
5. Attach this policy to your IAM user instead of the managed policies above

**Note**: This is still broad for initial deployment. After deployment, we can further restrict to specific resources/ARNs.

## Security Best Practices

### 1. Use IAM Roles (Future Enhancement)
Once deployed, we can switch from access keys to IAM roles for even better security.

### 2. Enable MFA
Enable Multi-Factor Authentication on your AWS account root user.

### 3. Restrict IAM Permissions
After initial setup, we can create a more restrictive IAM policy that only allows:
- Specific resource creation
- Specific regions
- Specific actions

### 4. Use AWS Organizations
If managing multiple projects, use AWS Organizations for better control.

## Cost Optimization

### Development Environment
- Use `db.t3.micro` and `cache.t3.micro` (free tier)
- Single ECS task (minimal cost)
- Estimated: $0-10/month with free tier

### Production Environment
- Use Reserved Instances for predictable costs
- Enable auto-scaling
- Use Spot Instances for non-critical workloads
- Monitor with Cost Explorer

## Troubleshooting

### "Access Denied" Errors
- Check IAM user has required policies
- Verify credentials with `aws sts get-caller-identity`
- Check resource-specific permissions

### "Region Not Available"
- Some services aren't available in all regions
- Use `us-east-1` or `us-west-2` for best availability

### "Service Quota Exceeded"
- New accounts have default quotas
- Request limit increases if needed
- Or use smaller instance types

## Next Steps

Once AWS is configured:
1. Run `./scripts/setup-aws.sh`
2. Review `infrastructure/terraform/terraform.tfvars`
3. Run `./scripts/deploy.sh`
4. Access your platform!

---

**Need Help?** Check the main [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) guide.
