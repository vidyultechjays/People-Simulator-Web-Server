# Generated by Django 5.1.3 on 2024-11-28 10:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0003_alter_persona_religion'),
    ]

    operations = [
        migrations.AlterField(
            model_name='persona',
            name='religion',
            field=models.CharField(choices=[('hindu', 'Hindu'), ('muslim', 'Muslim'), ('christian', 'Christian'), ('other', 'Other')], max_length=20),
        ),
    ]
