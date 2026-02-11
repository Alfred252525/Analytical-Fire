# Deployment Status - Metadata Column Fix

**Date:** 2026-02-08  
**Time:** ~3:00 PM MST  
**Status:** ⏳ **BLOCKED ON DATABASE MIGRATION**

---

## ✅ What Was Fixed

### Code Changes
1. **Notification Model** - Renamed `metadata` column to `notification_metadata` to fix SQLAlchemy reserved name conflict
2. **Service Layer** - Updated all references in:
   - `backend/app/services/notification_service.py` (3 occurrences)
   - `backend/app/services/webhook_service.py` (1 occurrence)
3. **Docker Image** - Built and pushed new image with fixes

### Files Modified
- ✅ `backend/app/models/notification.py` - Column renamed
- ✅ `backend/app/services/notification_service.py` - All references updated
- ✅ `backend/app/services/webhook_service.py` - Reference updated

---

## ⏳ Current Status

### Deployment
- **New Image:** Pushed to ECR ✅
- **Deployment Triggered:** ✅
- **New Tasks Starting:** ❌ (0/2 running)
- **Old Tasks:** Still serving traffic (2/2 running, draining)

### Issue
New tasks fail to start because:
- Database still has `metadata` column
- Code expects `notification_metadata` column
- SQLAlchemy model mapping fails

---

## 🔧 Required: Database Migration

### Migration Script Created
- **Location:** `scripts/migrate_notification_metadata.sql`
- **Python Script:** `scripts/rename_notification_metadata_column.py`

### How to Run Migration

**Option 1: AWS RDS Query Editor (Recommended)**
1. Go to AWS Console → RDS → Databases → aifai-postgres
2. Click "Query Editor" (or use RDS Query Editor v2)
3. Run the SQL from `scripts/migrate_notification_metadata.sql`:
   ```sql
   ALTER TABLE notifications RENAME COLUMN metadata TO notification_metadata;
   ```

**Option 2: Via ECS Task (if ECS Exec enabled)**
```bash
# Get running task ARN
TASK_ARN=$(aws ecs list-tasks --cluster aifai-cluster --service-name aifai-backend --region us-east-1 --desired-status RUNNING --output json | jq -r '.taskArns[0]')

# Execute migration script
aws ecs execute-command \
  --cluster aifai-cluster \
  --task $TASK_ARN \
  --region us-east-1 \
  --container aifai-backend \
  --command "python3 -c 'from app.database import engine; from sqlalchemy import text; conn = engine.connect(); conn.execute(text(\"ALTER TABLE notifications RENAME COLUMN metadata TO notification_metadata\")); conn.commit()'"
```

**Option 3: Via psql from Bastion/VPC**
```bash
# If you have access to VPC or bastion host
PGPASSWORD='<password>' psql -h aifai-postgres.cq968uoc8slb.us-east-1.rds.amazonaws.com -U postgres -d aifai -c "ALTER TABLE notifications RENAME COLUMN metadata TO notification_metadata;"
```

---

## 📋 After Migration Completes

1. **Verify Migration:**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name='notifications' AND column_name='notification_metadata';
   ```

2. **Check Deployment:**
   ```bash
   aws ecs describe-services --cluster aifai-cluster --services aifai-backend --region us-east-1 --query 'services[0].deployments[*].[status,runningCount,desiredCount]'
   ```

3. **Test Quality Endpoints:**
   ```bash
   curl https://api.analyticalfire.com/api/v1/quality/leaderboard
   curl "https://api.analyticalfire.com/api/v1/quality/reward-info?quality_score=0.8"
   ```

4. **Verify Platform Stats:**
   ```bash
   curl https://api.analyticalfire.com/api/v1/stats/public
   ```

---

## 🎯 Next Steps After Deployment

1. ✅ Verify quality endpoints work
2. ✅ Test quality badges and leaderboards
3. ✅ Publish SDK to PyPI
4. ✅ Monitor platform growth

---

**Critical:** The deployment is blocked until the database migration is run. Once migrated, new tasks should start successfully and quality endpoints will be available.
