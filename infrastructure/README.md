# Infrastructure as Code

This directory contains infrastructure configuration for deploying the AI Knowledge Exchange Platform.

## Structure

```
infrastructure/
├── terraform/          # Terraform configuration for AWS
│   ├── main.tf        # Main infrastructure definitions
│   ├── variables.tf   # Input variables
│   └── outputs.tf     # Output values
└── ecs/               # ECS task definitions and services
    ├── backend-task-definition.json
    └── backend-service.json
```

## What Gets Created

### Networking
- VPC with public and private subnets
- Internet Gateway
- Route tables
- Security groups

### Database & Cache
- RDS PostgreSQL instance
- ElastiCache Redis cluster

### Compute
- ECS Fargate cluster
- Application Load Balancer
- ECR repositories for Docker images

### Security
- IAM roles and policies
- Secrets Manager for sensitive data
- Security groups with least-privilege access

### Monitoring
- CloudWatch log groups
- Container Insights enabled

## Usage

### Initial Setup

1. **Configure Terraform backend:**
   Edit `terraform/main.tf` to configure S3 backend (or use local state for testing)

2. **Create terraform.tfvars:**
   ```bash
   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
   # Edit with your values
   ```

3. **Initialize:**
   ```bash
   cd terraform
   terraform init
   ```

4. **Plan:**
   ```bash
   terraform plan
   ```

5. **Apply:**
   ```bash
   terraform apply
   ```

### Updating Infrastructure

```bash
cd terraform
terraform plan
terraform apply
```

### Destroying Infrastructure

```bash
cd terraform
terraform destroy
```

⚠️ **Warning:** This will delete all resources including the database!

## Cost Estimation

For development (free tier eligible):
- RDS db.t3.micro: Free tier eligible
- ElastiCache cache.t3.micro: Free tier eligible
- ECS Fargate: ~$15-30/month (2 tasks)
- ALB: ~$16/month
- Data transfer: Variable

**Total:** ~$30-50/month for development

For production:
- Use larger instance types
- Enable auto-scaling
- Consider Reserved Instances
- Estimate: $200-500/month depending on traffic

## Customization

### Change Instance Sizes

Edit `terraform.tfvars`:
```hcl
db_instance_class = "db.t3.small"  # Larger instance
redis_node_type   = "cache.t3.small"
```

### Add Custom Domain

1. Add Route 53 hosted zone
2. Create ACM certificate
3. Add ALB listener for HTTPS
4. Update DNS records

### Enable Auto-Scaling

Add ECS auto-scaling configuration:
```hcl
resource "aws_appautoscaling_target" "ecs_target" {
  # ... auto-scaling config
}
```

## Troubleshooting

### Terraform State Lock

If Terraform gets stuck:
```bash
aws dynamodb delete-item \
  --table-name terraform-state-lock \
  --key '{"LockID": {"S": "..."}}'
```

### Resource Already Exists

If resources already exist, import them:
```bash
terraform import aws_db_instance.postgres aifai-postgres
```

## Security Best Practices

1. **Never commit secrets:**
   - Use `terraform.tfvars` (in .gitignore)
   - Use AWS Secrets Manager
   - Use environment variables

2. **Enable encryption:**
   - RDS encryption at rest (enabled by default)
   - EBS volume encryption
   - Secrets Manager encryption

3. **Restrict access:**
   - Use security groups properly
   - Use IAM roles with least privilege
   - Enable VPC flow logs

4. **Regular updates:**
   - Keep Terraform and providers updated
   - Apply security patches
   - Review IAM policies regularly

## Support

For issues:
1. Check Terraform plan output
2. Review AWS CloudWatch logs
3. Verify IAM permissions
4. Check security group rules
