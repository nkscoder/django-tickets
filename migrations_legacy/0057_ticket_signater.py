import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0056_fix_missing_signater_tables'),
    ]


    operations = [
        migrations.AddField(
            model_name='ticket',
            name='signater',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tickets',
                to='tickets.signater',
            ),
        ),
    ]