-- migrations/add_furniture_lock.sql
-- Add furniture lock column to beach_reservations table
-- Allows locking furniture assignments to prevent accidental changes

ALTER TABLE beach_reservations
ADD COLUMN is_furniture_locked INTEGER DEFAULT 0;
