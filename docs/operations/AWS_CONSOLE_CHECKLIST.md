# AWS Console Checklist - What to Check Now 💰

## Priority 1: Check Current Costs

### Step 1: View Current Month Costs
1. Go to: **Billing & Cost Management** (top right, click your account name)
2. Click: **Cost Explorer** (left sidebar)
3. View: **Current month** costs
4. Check: **Service breakdown** (which services cost what)

**What to look for:**
- Total cost for current month
- Cost per service (ECS, RDS, ElastiCache, ALB, etc.)
- Daily cost trend
- Any unexpected charges

### Step 2: View Detailed Billing
1. Go to: **Billing & Cost Management** > **Bills**
2. View: **Current month bill** (if available)
3. Check: **Service charges breakdown**

## Priority 2: Set Up Billing Alerts

### Step 1: Create SNS Topic for Alerts
1. Go to: **Simple Notification Service (SNS)**
2. Click: **Topics** > **Create topic**
3. Name: `aifai-billing-alerts`
4. Type: **Standard**
5. Click: **Create topic**
6. Click on topic > **Create subscription**
7. Protocol: **Email**
8. Endpoint: **Your email**
9. Click: **Create subscription**
10. **Check your email** and confirm subscription

### Step 2: Create CloudWatch Billing Alarm
1. Go to: **CloudWatch** > **Alarms**
2. Click: **Create alarm**
3. Select metric: **Billing** > **EstimatedCharges**
4. Metric name: **EstimatedCharges**
5. Namespace: **AWS/Billing**
6. Dimensions: **Currency = USD**
7. Statistic: **Maximum**
8. Period: **1 day**
9. Threshold:
   - **Type**: Static
   - **Greater than**: `50` (for $50 warning)
   - **Greater than**: `100` (for $100 action needed)
10. Actions: **Send notification to** `aifai-billing-alerts` topic
11. Click: **Create alarm**

**Create two alarms:**
- One at $50 (warning)
- One at $100 (action needed)

## Priority 3: Check Resource Usage

### ECS (Container Service)
1. Go to: **ECS** > **Clusters** > `aifai-cluster`
2. Check: **Service** > `aifai-backend`
3. View: **Metrics** tab
   - CPU utilization
   - Memory utilization
   - Task count
4. Check if we can downsize (if usage is low)

### RDS (Database)
1. Go to: **RDS** > **Databases** > `aifai-postgres`
2. Check: **Monitoring** tab
   - CPU utilization
   - Database connections
   - Storage used
3. Check instance size (db.t3.micro is smallest/cheapest)

### ElastiCache (Redis)
1. Go to: **ElastiCache** > **Redis clusters**
2. Check: **Monitoring** tab
   - CPU utilization
   - Memory usage
3. Check node type (cache.t3.micro is smallest/cheapest)

### ALB (Load Balancer)
1. Go to: **EC2** > **Load Balancers**
2. Check: **Monitoring** tab
   - Request count
   - Active connections
3. Note: ALB has fixed $16/month base cost

## Priority 4: Cost Optimization Opportunities

### Check These:
- [ ] Are we using the smallest instance sizes?
- [ ] Can we reduce ECS task count if load is low?
- [ ] Are there any idle/unused resources?
- [ ] Can we use Reserved Instances for 30% savings?
- [ ] Are we in the right AWS region (us-east-1 is usually cheapest)?

### Quick Wins:
1. **Right-size instances** if usage is low
2. **Stop unused resources** (if any)
3. **Use Reserved Instances** for predictable workloads (30% savings)
4. **Monitor data transfer** costs

## What to Report Back

Please share:
1. **Current month total cost**: $X.XX
2. **Cost breakdown by service**: 
   - ECS: $X
   - RDS: $X
   - ElastiCache: $X
   - ALB: $X
   - Other: $X
3. **Resource utilization** (CPU/memory %)
4. **Any unexpected charges**

---

**This will help us:**
- Understand actual costs
- Optimize if needed
- Set up proper monitoring
- Plan for revenue model if costs exceed $100/month
