# tickets/migrations/0030_create_ticket_application_doc_sql.py
from django.db import migrations

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS `ticket_application_doc` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `other_services_documents_link` BIGINT NOT NULL,
  `file` varchar(255) DEFAULT NULL,
  `status` varchar(255) DEFAULT NULL,
  `uploaded_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `uploaded_by_id` BIGINT DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

DROP_SQL = "DROP TABLE IF EXISTS `ticket_application_doc`;"

class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0029_ticketapplicationdoc'),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_SQL, reverse_sql=DROP_SQL),
    ]
