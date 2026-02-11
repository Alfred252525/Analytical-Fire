# Handoff

**Where:** Your Mac. Terminal. The folder that contains the aifai repo (e.g. `/Users/zimmy/Documents/aifai`).

**Command:** `pip3 install certifi && python3 scripts/run_visibility_audit.py`

If you get SSL errors, run `pip3 install certifi` first. If it fails for other reasons, copy-paste the FIX command it prints.

Seeding: `python3 scripts/seed_diverse_problems.py` (needs AIFAI_INSTANCE_ID + AIFAI_API_KEY).
