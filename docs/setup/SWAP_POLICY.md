# Swap Policy - Remove S3, Add ACM

## Safe to Remove: AmazonS3FullAccess

**Why it's safe:**
- We're using **local Terraform state** (not S3)
- No S3 buckets are being created
- We can add it back later if needed

## Steps

1. **Remove AmazonS3FullAccess:**
   - Go to IAM → Users → `aifai-deployment`
   - Find `AmazonS3FullAccess` in the policies list
   - Click the checkbox next to it
   - Click "Remove" button
   - Confirm removal

2. **Add AWSCertificateManagerFullAccess:**
   - Click "Add permissions" → "Attach policies directly"
   - Search for: `AWSCertificateManagerFullAccess`
   - Check the box
   - Click "Add permissions"

## That's It!

Once done, let me know and I'll:
1. Request the SSL certificate automatically
2. Get the validation CNAME records
3. Guide you to add them to Name.com
4. Configure HTTPS once validated

---

**Note**: If we ever need S3 later (for Terraform state or file storage), we can swap it back or create a custom policy with just the S3 permissions we need.
