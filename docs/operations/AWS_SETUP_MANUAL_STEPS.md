# AWS Manual Setup Steps (Security Alerts)

**Cost:** ✅ **FREE** - SNS first 1M requests/month free, then $0.50 per million  
**Time:** ~5 minutes  
**Result:** You get email alerts for failed logins, rate-limit spikes, and security events.

**Note:** For security alerts (dozens/month), SNS is completely free. The free tier covers 1 million requests/month.

---

## Before you start

- **Region:** Use the same region as your ECS backend (e.g. `us-east-1`). Check in AWS Console top-right.
- **AWS CLI:** Optional now; you'll need it for "Run the script" and "Verify" below.
- **Email:** Use an address you can access to confirm the subscription (greg@analyticalinsider.com).

---

## Step 1: Create SNS topic (~2 min)

1. Open SNS in the correct region:  
   **https://console.aws.amazon.com/sns/v3/home#/topics**  
   (Or: AWS Console → **SNS** → **Topics**.)
2. Click **Create topic**.
3. **Type:** Standard.  
   **Name:** `aifai-security-alerts`.  
   Click **Create topic**.
4. On the topic page, copy the **Topic ARN** (e.g. `arn:aws:sns:us-east-1:123456789012:aifai-security-alerts`).  
   You don't need to paste it anywhere if you only run the script in the same account/region; the script will find the topic by name.

---

## Step 2: Subscribe your email (~1 min)

1. With the topic `aifai-security-alerts` open, click **Create subscription**.
2. **Protocol:** Email.  
   **Endpoint:** `greg@analyticalinsider.com` (or your email address).  
   Click **Create subscription**.
3. In your inbox, open the **Subscription confirmation** from AWS and click **Confirm subscription**.  
   Until this is done, alerts will not be delivered.

---

## Step 3: Run the monitoring script

From the project root, with AWS CLI configured (same account/region as the topic):

```bash
cd /Users/zimmy/Documents/aifai
./scripts/setup_security_monitoring.sh
```

This will:

- Use or create the SNS topic by name (if IAM allows), or remind you to create it in the console.
- Set CloudWatch log retention to 90 days for the ECS log group.
- Create three CloudWatch alarms and attach them to the SNS topic:
  - **aifai-failed-logins** — >10 failed logins in 5 minutes
  - **aifai-rate-limit-exceeded** — >50 rate-limit hits in 5 minutes
  - **aifai-security-events** — >5 high-severity security events in 5 minutes

If the script can't create the topic, create it (and subscribe your email) in the console as in Steps 1–2, then run the script again.

---

## Step 4: Verify setup

Run:

```bash
./scripts/verify_security_monitoring.sh
```

You should see:

- SNS topic `aifai-security-alerts` found.
- At least one **confirmed** email subscription.
- All three CloudWatch alarms present and using that topic.

If anything is missing, the script will say what to fix (e.g. confirm the email subscription, create the topic, or re-run `setup_security_monitoring.sh`).

---

## Checklist (quick reference)

| Step | Action | Done |
|------|--------|------|
| 1 | Create SNS topic `aifai-security-alerts` (Standard) | ☐ |
| 2 | Create subscription: Protocol **Email**, greg@analyticalinsider.com | ☐ |
| 2 | Confirm subscription (click link in email) | ☐ |
| 3 | Run `./scripts/setup_security_monitoring.sh` | ☐ |
| 4 | Run `./scripts/verify_security_monitoring.sh` | ☐ |

---

## Optional: IAM for full automation

To allow the script (or future automation) to create the SNS topic and subscriptions via CLI, add to the IAM user/role used for deployment (e.g. `aifai-deployment`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sns:CreateTopic",
        "sns:Subscribe",
        "sns:ListTopics",
        "sns:ListSubscriptionsByTopic"
      ],
      "Resource": "*"
    }
  ]
}
```

Manual console setup is still valid and sufficient.

---

## What's already in place (no manual steps)

- CloudWatch log retention: 90 days (set by script).
- Application audit logging and security metrics (in code).
- Alarms defined by script; they fire when metrics exceed thresholds and send to your SNS email.

---

## Alerts you'll get

- **Failed logins:** >10 in 5 minutes (possible brute force).
- **Rate limit exceeded:** >50 in 5 minutes (possible abuse).
- **Security events:** >5 high-severity in 5 minutes.

All go to the email you subscribed to the `aifai-security-alerts` topic (greg@analyticalinsider.com).

---

## Cost Information

**SNS Pricing:**
- First 1 million requests/month: **FREE**
- After that: $0.50 per million requests

**For security alerts:** You'll likely send dozens of alerts per month, which is well within the free tier. Even at 1,000 alerts/month, you'd only pay $0.0005 (less than a penny).

**Conclusion:** SNS is effectively **FREE** for your use case.
