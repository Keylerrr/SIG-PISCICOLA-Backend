# Generated migration for auto-generating pond code

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ponds', '0003_remove_pond_is_active_remove_pond_type_pond_area_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pond',
            name='code',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
