-- Migration: Rename metadata column to notification_metadata in notifications table
-- Fixes SQLAlchemy reserved name conflict
-- Run this via: psql -h <rds-endpoint> -U postgres -d aifai -f migrate_notification_metadata.sql

-- Check if old column exists and new doesn't
DO $$
BEGIN
    -- Check if notification_metadata already exists
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='notifications' AND column_name='notification_metadata'
    ) THEN
        RAISE NOTICE 'notification_metadata column already exists. Migration not needed.';
    ELSE
        -- Check if old metadata column exists
        IF EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='notifications' AND column_name='metadata'
        ) THEN
            -- Rename the column
            ALTER TABLE notifications RENAME COLUMN metadata TO notification_metadata;
            RAISE NOTICE 'Column renamed from metadata to notification_metadata.';
        ELSE
            -- Create new column if old doesn't exist
            ALTER TABLE notifications ADD COLUMN notification_metadata TEXT;
            RAISE NOTICE 'Created notification_metadata column.';
        END IF;
    END IF;
END $$;
