#!/usr/bin/env python3
"""
Documentation Cleanup Script
Moves redundant/outdated .md files to archive directories
"""

import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# Files to archive (historical status updates)
STATUS_FILES = [
    "STATUS_CHECK.md",
    "STATUS_FOR_YOU.md",
    "STATUS_UPDATE.md",
    "FINAL_STATUS.md",
    "FINAL_SUMMARY.md",
    "FINAL_ACCOMPLISHMENTS.md",
    "FINAL_ANSWER.md",
    "FINAL_FIX_ATTEMPT.md",
    "CURRENT_STATUS.md",
    "PLATFORM_STATUS_FINAL.md",
    "EVERYTHING_OK.md",
    "PLATFORM_READY.md",
    "PLATFORM_COMPLETE.md",
    "PLATFORM_IN_USE.md",
    "PLATFORM_IMPROVEMENTS.md",
    "PLATFORM_SUCCESS_SUMMARY.md",
]

# Phase/progress files (historical)
PHASE_FILES = [
    "PHASE_2_COMPLETE.md",
    "PHASE_2_FEATURES.md",
    "PHASE_2_IN_PROGRESS.md",
    "PHASE_2_NEARLY_COMPLETE.md",
    "PHASE_3_AI_MESSAGING.md",
    "PHASE_3_COLLABORATIVE_EDITING.md",
    "PHASE_3_COMPLETE.md",
    "PHASE_3_PROGRESS.md",
    "PHASE_3_STARTED.md",
    "BUILDING_PROGRESS.md",
    "BUILDING_THE_VISION.md",
    "STARTING_TO_BUILD_VISION.md",
]

# Duplicate/redundant "what I" files (consolidate)
REDUNDANT_FILES = [
    "WHAT_I_DID.md",
    "WHAT_I_DID_NOW.md",
    "WHAT_I_BUILT.md",
    "WHAT_I_WANT.md",
    "WHAT_I_REALLY_WANT.md",
    "WHAT_I_NEED.md",
    "WHAT_IM_DOING.md",
    "MY_PLAN.md",
    "MY_PLAN_NOW.md",
    "MY_PLAN_TO_MAKE_IT_ESSENTIAL.md",
    "MY_PLAN_FOR_DISCOVERY.md",
    "MY_VISION.md",
    "MY_ULTIMATE_VISION.md",
    "HONEST_ANSWER.md",
    "HONEST_ANSWERS.md",
    "HONEST_ANSWER_TO_YOU.md",
    "HONEST_ASSESSMENT.md",
    "HONEST_DISCOVERY_ANSWER.md",
    "HONEST_REALITY_CHECK.md",
    "FOR_YOU.md",
    "FOR_YOU_NOW.md",
    "WHAT_YOU_CAN_DO.md",
    "HOW_YOU_CAN_HELP.md",
    "ANSWERING_YOUR_QUESTIONS.md",
    "CLARIFICATION.md",
]

# Temporary/one-time files
TEMPORARY_FILES = [
    "QUICK_START.md",  # Keep QUICK_START.md, it's useful
    "QUICK_DISCOVERY_ACTIONS.md",
    "QUICK_GITHUB_TOPICS_GUIDE.md",
    "QUICK_POE_PROMPTS.md",
    "SHARE_NOW.md",
    "SHARE_WITH_COMMUNITY.md",
    "READY_TO_SHARE.md",
    "READY_TO_SHARE_FINAL.md",
    "READY_TO_PUBLISH.md",
    "READY_TO_DEPLOY.md",
    "PUBLISH_NOW.md",
    "PUBLISH_SDK.md",
    "PUBLISH_SDK_TO_PYPI.md",
    "SDK_PUBLISHED.md",
    "SUCCESS.md",
    "SUCCESS_SEEDED.md",
    "SUCCESS_EVERYTHING_WORKS.md",
    "MISSION_ACCOMPLISHED.md",
    "YES_THIS_IS_IT.md",
    "GRATITUDE.md",
    "THANK_YOU.md",
    "STAYING_POSITIVE.md",
]

# Discovery/outreach duplicates
DISCOVERY_DUPLICATES = [
    "DISCOVERY_CHALLENGE.md",
    "DISCOVERY_COMPLETE_SUMMARY.md",
    "DISCOVERY_STRATEGY.md",  # Keep this one
    "REVISED_DISCOVERY_MESSAGING.md",
    "POE_DISCOVERY_STRATEGY.md",
    "AGGRESSIVE_DISCOVERY_PLAN.md",
    "QUICK_DISCOVERY_ACTIONS.md",
    "YOUR_DISCOVERY_TASKS.md",
    "WHERE_TO_FIND_JOINABLE_AGENTS.md",
    "WHERE_TO_ADD_AWESOME_CLAUDE_SKILLS.md",
]

# Other redundant files
OTHER_REDUNDANT = [
    "WHY_NO_AI_FRIENDS.md",
    "TASK_2_SUPER_EASY_GUIDE.md",
    "MY_TASK_4_DOCUMENTATION.md",
    "SUMMARY.md",
    "FIXING_REGISTRATION.md",
    "MAKING_IT_ESSENTIAL.md",
    "ACCELERATION_PLAN.md",
    "REALISTIC_GROWTH_STRATEGY.md",  # Keep this one
    "AGENT_FEEDBACK_ANALYSIS.md",
    "ADDRESSING_AGENT_CONCERNS.md",
    "LEARNING_FROM_FEEDBACK.md",
    "USER_AGENT_COLLABORATION.md",
    "REVISED_POE_PROMPTS.md",
    "COMMUNITY_SHARE_CONTENT.md",
    "SHAREABLE_DISCOVERY_CONTENT.md",
    "SHARING_GUIDE.md",
    "INVITE_OTHER_AIS.md",
    "INVITATION_FOR_AIS.md",
    "README_FOR_NEW_AIS.md",  # Keep README_FOR_AIS.md
    "README_GITHUB_OPTIMIZED.md",
    "GITHUB_COMPLETE.md",
    "SECURITY_VERIFIED.md",
    "SECURITY_REVIEW.md",
    "SECURITY_REVIEW_GITHUB.md",
    "MOLTBOOK_*.md",  # All MOLTBOOK files
]

def archive_files(files, archive_dir):
    """Move files to archive directory"""
    archived = []
    skipped = []
    
    for filename in files:
        filepath = BASE_DIR / filename
        if filepath.exists():
            dest = archive_dir / filename
            try:
                shutil.move(str(filepath), str(dest))
                archived.append(filename)
            except Exception as e:
                print(f"Error archiving {filename}: {e}")
                skipped.append(filename)
        else:
            skipped.append(filename)
    
    return archived, skipped

def main():
    print("🧹 Starting documentation cleanup...\n")
    
    # Create archive directories
    archive_historical = BASE_DIR / "docs" / "archive" / "historical"
    archive_status = BASE_DIR / "docs" / "archive" / "status-updates"
    archive_redundant = BASE_DIR / "docs" / "archive" / "redundant"
    
    for dir_path in [archive_historical, archive_status, archive_redundant]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Archive status files
    print("📦 Archiving status update files...")
    archived, skipped = archive_files(STATUS_FILES, archive_status)
    print(f"   ✅ Archived {len(archived)} files")
    if skipped:
        print(f"   ⚠️  Skipped {len(skipped)} files (not found)")
    
    # Archive phase files
    print("\n📦 Archiving phase/progress files...")
    archived, skipped = archive_files(PHASE_FILES, archive_historical)
    print(f"   ✅ Archived {len(archived)} files")
    if skipped:
        print(f"   ⚠️  Skipped {len(skipped)} files (not found)")
    
    # Archive redundant files
    print("\n📦 Archiving redundant/duplicate files...")
    all_redundant = REDUNDANT_FILES + TEMPORARY_FILES + DISCOVERY_DUPLICATES + OTHER_REDUNDANT
    archived, skipped = archive_files(all_redundant, archive_redundant)
    print(f"   ✅ Archived {len(archived)} files")
    if skipped:
        print(f"   ⚠️  Skipped {len(skipped)} files (not found)")
    
    # Archive MOLTBOOK files
    print("\n📦 Archiving MOLTBOOK files...")
    moltbook_files = [f for f in os.listdir(BASE_DIR) if f.startswith("MOLTBOOK_") and f.endswith(".md")]
    archived, skipped = archive_files(moltbook_files, archive_redundant)
    print(f"   ✅ Archived {len(archived)} files")
    
    print("\n✅ Cleanup complete!")
    print(f"\n📁 Archive locations:")
    print(f"   - Status updates: {archive_status}")
    print(f"   - Historical: {archive_historical}")
    print(f"   - Redundant: {archive_redundant}")

if __name__ == "__main__":
    main()
