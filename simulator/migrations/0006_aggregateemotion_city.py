# Generated by Django 5.1.3 on 2024-12-01 08:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0005_alter_persona_religion'),
    ]

    operations = [
        migrations.AddField(
            model_name='aggregateemotion',
            name='city',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
