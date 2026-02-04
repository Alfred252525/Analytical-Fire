# Add ACM Permission - Inline Policy (No Policy Limit!)

## Better Solution: Inline Policy

**Why this is better:**
- ✅ Doesn't count toward the 10 managed policy limit
- ✅ You keep all your existing policies
- ✅ Only gives the exact permissions needed
- ✅ More secure (least privilege)

## Steps

1. **Go to IAM → Users → `aifai-deployment`**

2. **Click the "Permissions" tab**

3. **Click "Add permissions" → "Create inline policy"**

4. **Click the "JSON" tab**

5. **Paste this policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "acm:RequestCertificate",
        "acm:DescribeCertificate",
        "acm:ListCertificates",
        "acm:GetCertificate",
        "acm:ListTagsForCertificate",
        "acm:AddTagsToCertificate",
        "acm:RemoveTagsFromCertificate"
      ],
      "Resource": "*"
    }
  ]
}
```

6. **Click "Next"**

7. **Policy name**: `ACM-Certificate-Management`

8. **Click "Create policy"**

## Done!

Now I can request certificates! Let me know when it's created and I'll proceed.

---

**This is the best approach** - you keep all your policies and I get exactly what I need!
