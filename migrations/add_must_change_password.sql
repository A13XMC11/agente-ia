-- Add must_change_password flag to usuarios table
-- Set to true when admin creates a client with a temporary password
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS must_change_password boolean DEFAULT false;
