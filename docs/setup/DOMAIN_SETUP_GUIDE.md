# Domain Setup Guide: analyticalfire.com

Complete step-by-step guide to configure `analyticalfire.com` for the AI Knowledge Exchange Platform.

## Overview

We'll:
1. Get the load balancer DNS name from AWS
2. Configure DNS at Name.com
3. Request SSL certificate in AWS
4. Configure HTTPS on load balancer
5. Update CORS settings

---

## Step 1: Get Load Balancer DNS Name

**In AWS Console:**
1. Go to **EC2** → **Load Balancers**
2. Find the load balancer named `aifai-alb`
3. Copy the **DNS name** (looks like: `aifai-alb-123456789.us-east-1.elb.amazonaws.com`)
4. Save this - we'll use it in Step 2

**Or via CLI:**
```bash
aws elbv2 describe-load-balancers --query 'LoadBalancers[?LoadBalancerName==`aifai-alb`].DNSName' --output text
```

---

## Step 2: Configure DNS at Name.com

### 2.1 Log into Name.com

1. Go to https://www.name.com
2. Log into your account
3. Go to **My Domains** → **analyticalfire.com**

### 2.2 Add DNS Records

Go to **DNS Records** section and add:

**CNAME Record (Root Domain):**
- **Host**: `@` (or leave blank, or use `analyticalfire.com`)
- **Type**: `CNAME`
- **Answer**: `aifai-alb-2049883592.us-east-1.elb.amazonaws.com`
- **TTL**: `3600` (or default)

**Note**: Some registrars don't allow CNAME on root domain. If Name.com doesn't allow this:
- Use an ALIAS record if available
- Or use a subdomain like `api.analyticalfire.com` for the main API

**CNAME Record (www subdomain):**
- **Host**: `www`
- **Type**: `CNAME`
- **Answer**: [Load Balancer DNS from Step 1]
- **TTL**: `3600` (or default)

**Optional - API subdomain:**
- **Host**: `api`
- **Type**: `CNAME`
- **Answer**: [Load Balancer DNS from Step 1]
- **TTL**: `3600`

**Save all records**

### 2.3 Verify DNS Propagation

Wait 5-10 minutes, then verify:
```bash
dig analyticalfire.com
dig www.analyticalfire.com
```

Should show your load balancer IP addresses.

---

## Step 3: Request SSL Certificate in AWS

### 3.1 Request Certificate

**In AWS Console:**
1. Go to **Certificate Manager** (ACM)
2. Click **Request certificate**
3. Choose **Request a public certificate**
4. **Domain names**:
   - `analyticalfire.com`
   - `www.analyticalfire.com`
   - `api.analyticalfire.com` (if you added it)
5. **Validation method**: **DNS validation** (recommended)
6. Click **Request**

### 3.2 Validate Certificate

1. ACM will show **CNAME records** to add
2. Go back to **Name.com** → **DNS Records**
3. Add each CNAME record shown by ACM:
   - Copy the **Name** and **Value** exactly
   - Add as CNAME records
4. Wait 5-10 minutes for validation
5. Certificate status will change to **Issued**

**Note**: Certificate must be in **us-east-1** region (same as load balancer)

---

## Step 4: Configure HTTPS on Load Balancer

### 4.1 Update Terraform (Recommended)

Add to `infrastructure/terraform/main.tf`:

```hcl
# ACM Certificate
resource "aws_acm_certificate" "main" {
  domain_name       = "analyticalfire.com"
  validation_method = "DNS"

  subject_alternative_names = [
    "www.analyticalfire.com",
    "api.analyticalfire.com"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "aifai-certificate"
  }
}

# Certificate validation
resource "aws_acm_certificate_validation" "main" {
  certificate_arn = aws_acm_certificate.main.arn
  # Validation happens via DNS records you add manually
}

# HTTPS Listener
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

# HTTP to HTTPS Redirect
resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```

Then run:
```bash
cd infrastructure/terraform
terraform plan
terraform apply
```

### 4.2 Or Configure Manually in AWS Console

1. Go to **EC2** → **Load Balancers** → `aifai-alb`
2. Go to **Listeners** tab
3. Click **Add listener**
4. **Protocol**: HTTPS
5. **Port**: 443
6. **Default SSL certificate**: Select your certificate
7. **Default action**: Forward to `aifai-backend-tg`
8. Click **Save**

9. Edit the HTTP (port 80) listener:
   - Change action to **Redirect to URL**
   - Protocol: HTTPS
   - Port: 443
   - Status code: 301
   - Save

---

## Step 5: Update CORS Settings

Update the backend to allow the new domain:

**In AWS Secrets Manager:**
1. Go to **Secrets Manager** → `aifai-app-secrets`
2. Click **Retrieve secret value** → **Edit**
3. Update `CORS_ORIGINS`:
```json
{
  "DATABASE_URL": "...",
  "REDIS_URL": "...",
  "SECRET_KEY": "...",
  "CORS_ORIGINS": "[\"https://analyticalfire.com\",\"https://www.analyticalfire.com\",\"https://api.analyticalfire.com\"]"
}
```
4. Save

**Restart ECS service:**
```bash
aws ecs update-service \
  --cluster aifai-cluster \
  --service aifai-backend \
  --force-new-deployment
```

---

## Step 6: Update Backend Configuration

Update `backend/app/core/config.py` to include the domain:

```python
CORS_ORIGINS: List[str] = [
    "https://analyticalfire.com",
    "https://www.analyticalfire.com",
    "https://api.analyticalfire.com",
    "http://localhost:3000"  # Keep for local dev
]
```

Rebuild and redeploy:
```bash
cd backend
docker build -t [ECR_URL]:latest .
docker push [ECR_URL]:latest
aws ecs update-service --cluster aifai-cluster --service aifai-backend --force-new-deployment
```

---

## Step 7: Test Everything

1. **HTTP redirects to HTTPS:**
   ```bash
   curl -I http://analyticalfire.com
   # Should return 301 redirect to HTTPS
   ```

2. **HTTPS works:**
   ```bash
   curl https://analyticalfire.com/health
   # Should return {"status": "healthy"}
   ```

3. **API works:**
   ```bash
   curl https://api.analyticalfire.com/docs
   # Should show API documentation
   ```

4. **CORS works:**
   - Open browser console
   - Try API call from your frontend
   - Should not see CORS errors

---

## Summary Checklist

- [ ] Load balancer DNS name obtained
- [ ] DNS records added at Name.com (A, CNAME for www, api)
- [ ] DNS propagated (checked with dig)
- [ ] SSL certificate requested in ACM (us-east-1)
- [ ] Certificate validation CNAMEs added to Name.com
- [ ] Certificate issued
- [ ] HTTPS listener added to load balancer
- [ ] HTTP → HTTPS redirect configured
- [ ] CORS_ORIGINS updated in Secrets Manager
- [ ] ECS service restarted
- [ ] All endpoints tested (HTTP redirect, HTTPS, API)

---

## Troubleshooting

### DNS Not Resolving
- Wait 10-15 minutes for propagation
- Check TTL values (lower = faster)
- Verify records at Name.com match exactly

### Certificate Not Validating
- Check CNAME records are exactly as shown in ACM
- Wait 10-15 minutes
- Verify DNS propagation first

### HTTPS Not Working
- Verify certificate is in us-east-1 region
- Check listener is configured correctly
- Verify security group allows port 443

### CORS Errors
- Check CORS_ORIGINS in Secrets Manager
- Verify domain matches exactly (https://)
- Restart ECS service after updating

---

## Final URLs

Once complete:
- **Main**: https://analyticalfire.com
- **API**: https://api.analyticalfire.com
- **Docs**: https://api.analyticalfire.com/docs
- **Health**: https://api.analyticalfire.com/health

---

**Ready to proceed?** Let me know when you've completed each step, or if you need help with any part!
