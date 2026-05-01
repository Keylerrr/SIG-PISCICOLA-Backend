# Generated migration for renaming Estanque to Pond and adding foreign key to Farm

import django.core.validators
import django.utils.timezone
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('farm', '0002_remove_farm_deleted_at_farm_manager'),
        ('ponds', '0001_initial'),
    ]

    operations = [
        # Delete the old unique constraint
        migrations.AlterUniqueTogether(
            name='estanque',
            unique_together=set(),
        ),
        migrations.RemoveConstraint(
            model_name='estanque',
            name='unique_codigo_por_granja',
        ),
        # Rename model
        migrations.RenameModel(
            old_name='Estanque',
            new_name='Pond',
        ),
        # Change db_table
        migrations.AlterModelTable(
            name='pond',
            table='pond',
        ),
        # Rename fields
        migrations.RenameField(
            model_name='pond',
            old_name='codigo',
            new_name='code',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='nombre',
            new_name='name',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='tipo',
            new_name='type',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='estado',
            new_name='status',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='capacidad',
            new_name='capacity',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='descripcion',
            new_name='description',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='activo_interruptor',
            new_name='is_active',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='fecha_creacion',
            new_name='created_at',
        ),
        migrations.RenameField(
            model_name='pond',
            old_name='fecha_actualizacion',
            new_name='updated_at',
        ),
        # Remove granja_id IntegerField
        migrations.RemoveField(
            model_name='pond',
            name='granja_id',
        ),
        # Add farm ForeignKey
        migrations.AddField(
            model_name='pond',
            name='farm',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='ponds', to='farm.farm'),
            preserve_default=False,
        ),
        # Update choices for type and status fields
        migrations.AlterField(
            model_name='pond',
            name='type',
            field=models.CharField(choices=[('pond', 'Pond'), ('cage', 'Cage')], default='pond', max_length=20),
        ),
        migrations.AlterField(
            model_name='pond',
            name='status',
            field=models.CharField(choices=[('active', 'Active'), ('in_use', 'In Use'), ('cleaning', 'Cleaning'), ('inactive', 'Inactive')], default='active', max_length=20),
        ),
        # Update ordering
        migrations.AlterModelOptions(
            name='pond',
            options={'ordering': ['-created_at']},
        ),
        # Add new unique constraint
        migrations.AddConstraint(
            model_name='pond',
            constraint=models.UniqueConstraint(fields=('farm', 'code'), name='unique_code_per_farm'),
        ),
    ]
