# Ready to Deploy Checklist

Use this checklist to verify everything is set up before deployment.

## ✅ Pre-Deployment Checklist

- [ ] IAM user created: `aifai-deployment` (or your choice)
- [ ] Custom least-privilege policy created and attached
- [ ] Access Key ID saved: `AKIA...`
- [ ] Secret Access Key saved: `...` (can't view again!)
- [ ] AWS CLI configured: `aws configure` completed
- [ ] AWS CLI tested: `aws sts get-caller-identity` works
- [ ] Preferred region chosen: `us-east-1` (or other)
- [ ] Billing alerts set up (optional but recommended)

## 📋 What to Share

Once everything is checked, share:

1. **Access Key ID**: `AKIA...`
2. **Secret Access Key**: `...`
3. **Region**: `us-east-1` (or your choice)
4. **Confirmation**: "Ready to deploy!"

## 🚀 After You Share

I'll:
1. Configure AWS CLI with your credentials
2. Run `./scripts/setup-aws.sh` (creates S3 bucket, generates secrets)
3. Run `./scripts/deploy.sh` (deploys everything)
4. Give you the platform URL when done!

**Estimated time**: 30-45 minutes for full deployment

---

**That's it!** Simple and lean. 🎯
