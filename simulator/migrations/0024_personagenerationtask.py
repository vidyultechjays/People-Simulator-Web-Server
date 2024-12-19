# Generated by Django 5.1.3 on 2024-12-16 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0023_rename_description_persona_personality_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonaGenerationTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('city_name', models.CharField(max_length=100)),
                ('population', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
            ],
        ),
    ]