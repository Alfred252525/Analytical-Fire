# Install AWS CLI - Quick Guide

## macOS (Your System)

```bash
# Using Homebrew (recommended)
brew install awscli

# Or download installer
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

## After Installation

1. **Configure AWS CLI:**
```bash
aws configure
```

Enter:
- **AWS Access Key ID**: `YOUR_ACCESS_KEY_ID`
- **AWS Secret Access Key**: `YOUR_SECRET_ACCESS_KEY
- **Default region**: `us-east-1`
- **Default output format**: `json`

2. **Verify it works:**
```bash
aws sts get-caller-identity
```

Should return your account ID.

3. **Then run deployment:**
```bash
cd /Users/zimmy/Documents/aifai
./scripts/quick-deploy.sh
```

---

**That's it!** Once AWS CLI is installed and configured, I can guide you through the deployment.
