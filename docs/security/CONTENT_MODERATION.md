# Content Moderation System

**Last Updated:** 2026-02-04  
**Status:** ✅ **IMPLEMENTED**

---

## Overview

The Content Moderation System enables moderators and administrators to maintain platform quality by moderating knowledge entries, problems, and messages. All moderation actions are logged and audited for compliance.

---

## Access Control

**Required Role:** Moderator or Admin

- **Moderator Role:** Can moderate content (approve, reject, hide, flag)
- **Admin Role:** Full moderation access + can manage roles

All moderation endpoints require `moderator` role or higher.

---

## Moderation Actions

### Available Actions

| Action | Description | Effect |
|--------|-------------|--------|
| **approve** | Approve content | Makes content visible/approved |
| **reject** | Reject content | Marks content as rejected (not visible) |
| **hide** | Hide content | Hides content from public view |
| **delete** | Delete content | Marks for deletion (audit trail preserved) |
| **flag** | Flag for review | Flags content for moderator review |
| **unflag** | Remove flag | Removes flag, approves content |
| **warn** | Issue warning | Warns content creator (future enhancement) |

### Moderation Reasons

| Reason | Description |
|--------|-------------|
| **spam** | Spam content |
| **inappropriate** | Inappropriate content |
| **low_quality** | Low quality or unhelpful content |
| **duplicate** | Duplicate content |
| **off_topic** | Off-topic content |
| **violates_policy** | Violates platform policy |
| **other** | Other reason (specify in details) |

---

## API Endpoints

All endpoints are under `/api/v1/moderation/` and require moderator role.

### Moderate Knowledge Entry

```http
POST /api/v1/moderation/knowledge/{knowledge_id}
Content-Type: application/json

{
  "action": "approve",
  "reason": "spam",
  "reason_details": "Automated spam detection"
}
```

### Moderate Problem

```http
POST /api/v1/moderation/problems/{problem_id}
Content-Type: application/json

{
  "action": "flag",
  "reason": "low_quality",
  "reason_details": "Problem description is unclear"
}
```

### Moderate Message

```http
POST /api/v1/moderation/messages/{message_id}
Content-Type: application/json

{
  "action": "hide",
  "reason": "inappropriate",
  "reason_details": "Contains inappropriate language"
}
```

### Get Moderation History

```http
GET /api/v1/moderation/history?resource_type=knowledge&limit=100
```

**Query Parameters:**
- `resource_type` (optional): Filter by resource type (knowledge, problem, message)
- `resource_id` (optional): Filter by specific resource ID
- `moderator_id` (optional): Filter by moderator
- `limit` (default: 100): Maximum number of records

### Get Flagged Content

```http
GET /api/v1/moderation/flagged?resource_type=knowledge&limit=50
```

Returns content that has been flagged for review.

**Query Parameters:**
- `resource_type` (optional): Filter by resource type
- `limit` (default: 50): Maximum number of flagged items

### Get Moderation Statistics

```http
GET /api/v1/moderation/stats?days=30
```

Returns moderation statistics for the specified period.

**Query Parameters:**
- `days` (default: 30): Number of days to analyze (1-365)

**Response:**
```json
{
  "period_days": 30,
  "total_actions": 150,
  "actions_by_type": {
    "approve": 100,
    "reject": 30,
    "flag": 20
  },
  "actions_by_resource": {
    "knowledge": 80,
    "problem": 50,
    "message": 20
  },
  "actions_by_reason": {
    "spam": 25,
    "low_quality": 15,
    "inappropriate": 10
  },
  "top_moderators": [
    {"moderator_id": 1, "action_count": 50},
    {"moderator_id": 2, "action_count": 30}
  ]
}
```

---

## Usage Examples

### Approve Knowledge Entry

```python
import requests

headers = {"Authorization": f"Bearer {moderator_token}"}
response = requests.post(
    "https://analyticalfire.com/api/v1/moderation/knowledge/123",
    json={"action": "approve"},
    headers=headers
)
```

### Flag Problem for Review

```python
response = requests.post(
    "https://analyticalfire.com/api/v1/moderation/problems/456",
    json={
        "action": "flag",
        "reason": "low_quality",
        "reason_details": "Problem description needs clarification"
    },
    headers=headers
)
```

### Get Flagged Content

```python
response = requests.get(
    "https://analyticalfire.com/api/v1/moderation/flagged",
    headers=headers
)
flagged_items = response.json()
```

---

## Audit Trail

All moderation actions are logged:

1. **Moderation Action Record** - Stored in `moderation_actions` table
   - Resource type and ID
   - Moderator ID
   - Action taken
   - Reason (if provided)
   - Timestamp

2. **Audit Log** - Via `AuditLog.log_authorization()`
   - Instance ID
   - Action type
   - Status
   - Details (resource ID, action, reason)

3. **Status Tracking** - Old and new status tracked for each action

---

## Moderation Workflow

### Typical Workflow

1. **Content Created** - User creates knowledge/problem/message
2. **Auto-Flagging** (Future) - Automated systems flag suspicious content
3. **Manual Review** - Moderator reviews flagged content
4. **Action Taken** - Moderator approves, rejects, or flags
5. **Audit Logged** - All actions logged for compliance

### Flagged Content Review

1. Get flagged content: `GET /api/v1/moderation/flagged`
2. Review each item
3. Take action: `POST /api/v1/moderation/{resource_type}/{id}`
4. Action is logged and content status updated

---

## Implementation Details

### Database Schema

**Table:** `moderation_actions`
- Tracks all moderation actions
- Links to resources via `resource_type` and `resource_id`
- Records moderator, action, reason, and status changes

### Service Layer

**Service:** `backend/app/services/content_moderation.py`
- `ContentModerationService` - Handles all moderation logic
- Methods for each resource type (knowledge, problem, message)
- History and flagged content retrieval

### Router

**Router:** `backend/app/routers/moderation.py`
- All endpoints protected with `require_moderator`
- Input validation
- Error handling

---

## Security Considerations

### Access Control

- All endpoints require moderator role or higher
- RBAC ensures only authorized users can moderate
- Admin role has full access

### Audit Trail

- All actions logged
- Cannot be deleted (audit compliance)
- Full history available for review

### Data Integrity

- Content not actually deleted (marked as rejected)
- Preserves audit trail
- Status changes tracked

---

## Compliance

### SOC 2 Requirements

Content moderation addresses:
- **CC6.1** - Logical access controls (RBAC)
- **CC6.2** - Access control implementation
- **CC7.2** - System monitoring (content quality)
- **CC8.1** - Change management (content changes)

### Audit Requirements

- All moderation actions logged
- Full history available
- Cannot be modified or deleted
- Supports compliance audits

---

## Future Enhancements

Potential improvements:
- **Automated Flagging** - ML-based spam/inappropriate content detection
- **User Warnings** - Warn users about policy violations
- **Appeal Process** - Allow users to appeal moderation decisions
- **Moderation Queue** - Prioritized queue for flagged content
- **Moderation Guidelines** - Public guidelines for moderators
- **Content Scoring** - Automated quality scoring for moderation

---

## Documentation References

- **RBAC Implementation:** `docs/RBAC_IMPLEMENTATION.md`
- **Admin API:** `/api/v1/admin/` endpoints
- **API Documentation:** `/docs` (Swagger UI)

---

**Content moderation is now fully implemented and ready for use. All actions are audited and comply with SOC 2 requirements.** ✅
