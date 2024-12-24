# Generated by Django 5.1.3 on 2024-12-21 09:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0027_llmmodelandkey'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromptModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(choices=[('personality_description', 'Personality Description')], default='personality_description', max_length=50, unique=True)),
                ('prompt_template', models.TextField(help_text='Enter the prompt with placeholders for dynamic fields like {name}, {city}, and {context}.')),
                ('version', models.CharField(help_text="Enter a version identifier (e.g., 'Elaborate', 'Concise', '3 lines').", max_length=50)),
            ],
        ),
    ]
