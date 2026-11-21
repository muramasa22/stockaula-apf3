ALTER TABLE movements ADD COLUMN request_key TEXT;
--> statement-breakpoint
CREATE UNIQUE INDEX movements_request_key ON movements(request_key);
