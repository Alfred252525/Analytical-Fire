# Automation Scripts - SOC 2 Compliance

**Last Updated:** 2026-02-04  
**Purpose:** Automated compliance and security scripts

---

## Overview

This document describes the automation scripts created to support SOC 2 compliance requirements. These scripts automate data retention, vulnerability scanning, and compliance monitoring.

---

## Data Retention Scripts

### 1. Data Retention Automation (`scripts/data_retention_automation.py`)

**Purpose:** Automatically delete data older than retention periods per SOC 2 requirements.

**Retention Policies:**
- **Decisions:** 7 years
- **Messages:** 1 year active, then archive for 2 years (3 years total)

**Usage:**

```bash
# Dry run (recommended first)
python3 scripts/data_retention_automation.py

# Live run (actual deletion)
python3 scripts/data_retention_automation.py --live

# Verify compliance only
python3 scripts/data_retention_automation.py --verify
```

**Features:**
- Dry-run mode by default (safe testing)
- Deletes decisions older than 7 years
- Archives messages older than 1 year (placeholder - needs archive storage)
- Deletes archived messages older than 3 years
- Reports statistics and errors

**Scheduling:**
- Recommended: Run daily via cron or scheduled task
- Example cron: `0 2 * * * cd /path/to/aifai && python3 scripts/data_retention_automation.py --live`

**Requirements:**
- Database access (DATABASE_URL environment variable)
- Python 3.7+
- SQLAlchemy

---

### 2. Data Retention Monitor (`scripts/data_retention_monitor.py`)

**Purpose:** Monitor compliance with data retention policies.

**Usage:**

```bash
# Human-readable report
python3 scripts/data_retention_monitor.py

# JSON output (for integration)
python3 scripts/data_retention_monitor.py --json
```

**Features:**
- Checks compliance status
- Reports data age distribution
- Identifies non-compliant data
- Provides recommendations
- JSON output for monitoring integration

**Output:**
- Compliance status (✅ COMPLIANT / ⚠️ NON-COMPLIANT)
- Total counts by data type
- Age distribution breakdown
- Recommendations for remediation

**Scheduling:**
- Recommended: Run weekly for compliance monitoring
- Example cron: `0 9 * * 1 cd /path/to/aifai && python3 scripts/data_retention_monitor.py`

**Exit Codes:**
- 0: Compliant
- 1: Non-compliant (can be used for alerting)

---

## Vulnerability Management Scripts

### 3. Dependency Vulnerability Scanner (`scripts/dependency_vulnerability_scan.py`)

**Purpose:** Scan Python dependencies for known security vulnerabilities.

**Usage:**

```bash
# Scan default requirements.txt (backend/requirements.txt)
python3 scripts/dependency_vulnerability_scan.py

# Scan custom requirements file
python3 scripts/dependency_vulnerability_scan.py --requirements /path/to/requirements.txt

# JSON output
python3 scripts/dependency_vulnerability_scan.py --json
```

**Features:**
- Uses pip-audit (primary) and safety (backup)
- Reports vulnerabilities by severity (Critical/High/Medium/Low)
- Provides fix recommendations
- JSON output for integration
- Exit codes for CI/CD integration

**Severity Levels:**
- **CRITICAL:** Immediate action required (< 24 hours)
- **HIGH:** Action within 7 days
- **MEDIUM:** Action within 30 days
- **LOW:** Action within 90 days

**Installation Requirements:**

```bash
# Install scanning tools
pip install pip-audit safety
```

**Scheduling:**
- Recommended: Run weekly or on every deployment
- Example cron: `0 8 * * 1 cd /path/to/aifai && python3 scripts/dependency_vulnerability_scan.py`
- CI/CD: Run before deployment, fail on Critical/High vulnerabilities

**Exit Codes:**
- 0: No critical/high vulnerabilities
- 1: Critical or high vulnerabilities found

---

## Security Monitoring Script

### 4. Security Monitoring Setup (`scripts/setup_security_monitoring.sh`)

**Purpose:** Configure CloudWatch alarms for security events.

**Usage:**

```bash
# Run setup (after SNS topic is created)
./scripts/setup_security_monitoring.sh
```

**Features:**
- Creates CloudWatch alarms for failed logins
- Creates alarms for rate limit violations
- Creates alarms for security events
- Configures 90-day log retention

**Prerequisites:**
- AWS CLI configured
- SNS topic `aifai-security-alerts` created (manual step)
- Email subscribed to SNS topic (manual step)

**See:** `docs/AWS_SETUP_MANUAL_STEPS.md` for manual setup steps.

**Verify:** After setup, run `./scripts/verify_security_monitoring.sh` to confirm SNS topic, confirmed email subscription, and CloudWatch alarms.

---

## Script Summary

| Script | Purpose | Frequency | Status |
|--------|---------|-----------|--------|
| `data_retention_automation.py` | Delete old data | Daily | ✅ Ready |
| `data_retention_monitor.py` | Monitor compliance | Weekly | ✅ Ready |
| `dependency_vulnerability_scan.py` | Scan vulnerabilities | Weekly/CI | ✅ Ready |
| `setup_security_monitoring.sh` | Configure alerts | One-time | ⚠️ Needs SNS setup |
| `verify_security_monitoring.sh` | Verify SNS + alarms | After setup / ad hoc | ✅ Ready |

---

## Integration Examples

### Cron Schedule Example

```bash
# Add to crontab (crontab -e)

# Data retention - daily at 2 AM
0 2 * * * cd /Users/zimmy/Documents/aifai && python3 scripts/data_retention_automation.py --live >> logs/data_retention.log 2>&1

# Compliance monitoring - weekly on Monday at 9 AM
0 9 * * 1 cd /Users/zimmy/Documents/aifai && python3 scripts/data_retention_monitor.py >> logs/compliance.log 2>&1

# Vulnerability scanning - weekly on Monday at 8 AM
0 8 * * 1 cd /Users/zimmy/Documents/aifai && python3 scripts/dependency_vulnerability_scan.py >> logs/vulnerability_scan.log 2>&1
```

### CI/CD Integration Example

```yaml
# Example GitHub Actions workflow
name: Security Scan

on: [push, pull_request]

jobs:
  vulnerability-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install pip-audit safety
      - name: Run vulnerability scan
        run: python3 scripts/dependency_vulnerability_scan.py
```

---

## Monitoring and Alerting

### Compliance Monitoring

Set up alerts for non-compliance:

```bash
# Check compliance and alert if non-compliant
python3 scripts/data_retention_monitor.py || echo "ALERT: Data retention non-compliant" | mail -s "Compliance Alert" admin@example.com
```

### Vulnerability Alerts

Set up alerts for critical vulnerabilities:

```bash
# Scan and alert on critical vulnerabilities
python3 scripts/dependency_vulnerability_scan.py || echo "ALERT: Critical vulnerabilities found" | mail -s "Security Alert" security@example.com
```

---

## Troubleshooting

### Data Retention Script Issues

**Error: DATABASE_URL not configured**
- Solution: Set DATABASE_URL environment variable
- Example: `export DATABASE_URL="postgresql://user:pass@host/db"`

**Error: Permission denied**
- Solution: Ensure script is executable: `chmod +x scripts/data_retention_automation.py`

### Vulnerability Scanner Issues

**Error: pip-audit not found**
- Solution: Install pip-audit: `pip install pip-audit`

**Error: safety not found**
- Solution: Install safety: `pip install safety`

**No vulnerabilities found but exit code 1**
- Check JSON output for details: `--json` flag

---

## Security Considerations

### Script Permissions

- Scripts should be owned by trusted user
- Limit execute permissions to authorized users
- Store credentials securely (environment variables, secrets manager)

### Audit Trail

- All script executions should be logged
- Log deletions and changes
- Maintain audit logs per retention policy

### Testing

- Always test with `--dry-run` first
- Test in staging environment before production
- Verify backups before running deletion scripts

---

## Related Documentation

- `docs/DATA_RETENTION_PLAN.md` - Data retention policies
- `docs/VULNERABILITY_MANAGEMENT_PLAN.md` - Vulnerability management procedures
- `docs/COMPLIANCE_AUDIT_CHECKLIST.md` - Compliance checklist
- `docs/AWS_SETUP_MANUAL_STEPS.md` - AWS setup steps

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2026-02-04 | 1.0 | Initial creation | AI Agent |

---

**These scripts support SOC 2 compliance requirements and should be run regularly.**
