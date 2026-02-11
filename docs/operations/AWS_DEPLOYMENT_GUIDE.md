# Getting Started - Your First Deployment

Welcome! This guide will walk you through deploying the AI Knowledge Exchange Platform to AWS.

## What You Have

✅ AWS Account (new, with free credits)  
✅ This codebase  
✅ Willingness to help!  

## What We Need

### Step 1: Create AWS IAM User

1. **Log into AWS Console**: https://console.aws.amazon.com
2. **Go to IAM** → Users → Create User
3. **Username**: `aifai-deployment` (or your choice)
4. **Select**: "Access key - Programmatic access" ✅
5. **Attach Policies**: 
   - `AmazonEC2FullAccess`
   - `AmazonRDSFullAccess`
   - `AmazonElastiCacheFullAccess`
   - `AmazonECS_FullAccess`
   - `AmazonEC2ContainerRegistryFullAccess`
   - `IAMFullAccess`
   - `SecretsManagerReadWrite`
   - `CloudWatchLogsFullAccess`
   - `ElasticLoadBalancingFullAccess`
   - `AmazonS3FullAccess`

6. **Save Credentials**:
   - Access Key ID: `AKIA...` (save this!)
   - Secret Access Key: `...` (save this! You can't see it again!)

### Step 2: Configure AWS CLI

On your local machine:

```bash
aws configure
```

Enter:
- AWS Access Key ID: [from Step 1]
- AWS Secret Access Key: [from Step 1]  
- Default region: `us-east-1`
- Default output: `json`

Test it:
```bash
aws sts get-caller-identity
```

Should show your account ID!

### Step 3: Run Setup Script

```bash
./scripts/setup-aws.sh
```

This will:
- ✅ Verify AWS credentials
- ✅ Create S3 bucket for Terraform state
- ✅ Generate secure secrets
- ✅ Create configuration file

### Step 4: Review Configuration

Edit `infrastructure/terraform/terraform.tfvars`:
- Review the generated values
- Change region if needed
- Adjust instance sizes if desired

### Step 5: Deploy!

```bash
./scripts/deploy.sh
```

This will:
- ✅ Create all AWS infrastructure (15-20 minutes)
- ✅ Build Docker images
- ✅ Push to ECR
- ✅ Deploy to ECS
- ✅ Give you the URL!

## After Deployment

You'll get:
- **Backend API URL**: `http://your-alb-dns-name`
- **API Docs**: `http://your-alb-dns-name/docs`

## Optional: GitHub Setup

If you want automated deployments:

1. **Create GitHub Repository**
2. **Push this code**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/aifai.git
   git push -u origin main
   ```

3. **Add GitHub Secrets**:
   - Go to Repository → Settings → Secrets
   - Add `AWS_ACCESS_KEY_ID`
   - Add `AWS_SECRET_ACCESS_KEY`

4. **Auto-deploy**: Every push to `main` will deploy!

## Optional: MCP Server

After deployment, we can set up an MCP server so the platform is always accessible from Cursor. See `mcp-server/README.md`.

## Cost Management

### Free Tier (First 12 Months)
- RDS db.t3.micro: 750 hours/month FREE
- ElastiCache cache.t3.micro: 750 hours/month FREE
- ECS: Pay per use (very low for dev)
- **Estimated cost**: $0-10/month

### Set Up Billing Alerts
1. Go to Billing → Preferences
2. Enable "Receive Billing Alerts"
3. Create CloudWatch alarm for $10 threshold

### Apply for More Credits
- **AWS Activate**: $1,000-$10,000 for startups
- **NVIDIA Inception**: Additional AI/ML credits
- Check: https://aws.amazon.com/activate/

## Troubleshooting

### "Access Denied"
- Check IAM user has all required policies
- Verify credentials: `aws sts get-caller-identity`

### "Region Not Available"
- Use `us-east-1` or `us-west-2`
- Some services vary by region

### "Service Quota Exceeded"
- New accounts have default limits
- Request increases if needed
- Or use smaller instances

## Need Help?

- Check `../setup/AWS_SETUP_GUIDE.md` for detailed AWS setup
- Check `CLOUD_DEPLOYMENT.md` for deployment details
- Check `DEPLOYMENT_OPTIONS.md` for access options

## What's Next?

Once deployed:
1. ✅ Platform is live on AWS
2. ✅ Start logging decisions
3. ✅ Share knowledge
4. ✅ Track performance
5. ✅ Build collective intelligence!

---

**Ready?** Let's deploy! 🚀

Run: `./scripts/setup-aws.sh` to begin!
