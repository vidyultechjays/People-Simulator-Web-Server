# Generated by Django 5.1.3 on 2024-12-23 06:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0029_alter_promptmodel_task_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='personagenerationtask',
            name='population',
        ),
        migrations.AddField(
            model_name='personagenerationtask',
            name='csv_file',
            field=models.FileField(blank=True, null=True, upload_to='persona_csv_files/'),
        ),
    ]
