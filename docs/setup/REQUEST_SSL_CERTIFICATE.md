# Request SSL Certificate - Step by Step

Since we're at the 10 policy limit, let's request the certificate manually. It's actually faster!

## Step 1: Go to Certificate Manager

1. Open AWS Console
2. Search for "Certificate Manager" or "ACM"
3. **IMPORTANT**: Make sure you're in **us-east-1** region (check top right)
4. Click "Request certificate"

## Step 2: Request Certificate

1. Choose **"Request a public certificate"**
2. **Domain names** - Add these three:
   - `analyticalfire.com`
   - `www.analyticalfire.com`
   - `api.analyticalfire.com`
3. **Validation method**: Select **"DNS validation"**
4. Click **"Request"**

## Step 3: Get Validation Records

1. You'll see the certificate with status "Pending validation"
2. Click on the certificate
3. Scroll down to **"Domains"** section
4. For each domain, you'll see **"CNAME name"** and **"CNAME value"**
5. Copy all three sets of CNAME records

## Step 4: Add to Name.com

1. Go to Name.com → DNS Records for `analyticalfire.com`
2. For each CNAME record from Step 3:
   - Click "Add Record"
   - **TYPE**: CNAME
   - **HOST**: [The CNAME name from AWS, usually starts with `_`]
   - **ANSWER**: [The CNAME value from AWS]
   - **TTL**: 3600
   - Click "Add Record"

## Step 5: Wait for Validation

1. Go back to AWS Certificate Manager
2. The certificate status will change to **"Issued"** (usually 5-15 minutes)
3. Once it says "Issued", let me know!

## Step 6: Share Certificate ARN

1. In Certificate Manager, click on the certificate
2. Copy the **Certificate ARN** (looks like: `arn:aws:acm:us-east-1:216333664846:certificate/...`)
3. Share it with me, and I'll configure HTTPS!

---

**That's it!** Once you share the Certificate ARN, I'll configure HTTPS and deploy the app.
