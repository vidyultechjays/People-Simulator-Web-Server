# Generated by Django 5.1.3 on 2024-12-05 07:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0010_remove_aggregateemotion_demographic_summary'),
    ]

    operations = [
        migrations.AddField(
            model_name='aggregateemotion',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='aggregateemotion',
            name='demographic_summary',
            field=models.JSONField(blank=True, default=dict, null=True),
        ),
        migrations.AddField(
            model_name='aggregateemotion',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]