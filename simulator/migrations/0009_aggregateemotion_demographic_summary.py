# Generated by Django 5.1.3 on 2024-12-05 05:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0008_delete_impactassessmenttask'),
    ]

    operations = [
        migrations.AddField(
            model_name='aggregateemotion',
            name='demographic_summary',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
    ]
