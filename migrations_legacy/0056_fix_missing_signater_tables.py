from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
    ("tickets", "0055_signater_ticketactiontrace_office_file_no_and_more"),
]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS signater (
                    id BIGSERIAL PRIMARY KEY,
                    ranks VARCHAR(100) NOT NULL,
                    status VARCHAR(20) NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ticket_signater (
                    id BIGSERIAL PRIMARY KEY,
                    action_type VARCHAR(255) NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    signater_id BIGINT NOT NULL REFERENCES signater(id) DEFERRABLE INITIALLY DEFERRED,
                    ticket_id BIGINT NOT NULL REFERENCES tickets_ticket(id) DEFERRABLE INITIALLY DEFERRED,
                    user_id BIGINT NOT NULL REFERENCES "UserManagement_customuser"(id) DEFERRABLE INITIALLY DEFERRED
                );

                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = 'unique_ticket_user_signater_action_type'
                    ) THEN
                        ALTER TABLE ticket_signater
                        ADD CONSTRAINT unique_ticket_user_signater_action_type
                        UNIQUE (ticket_id, user_id, action_type);
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS ticket_signater CASCADE;
                DROP TABLE IF EXISTS signater CASCADE;
            """,
        ),
    ]