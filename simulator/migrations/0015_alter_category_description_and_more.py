# Generated by Django 5.1.3 on 2024-12-10 16:05

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0014_category_remove_demographicsubcategory_category_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='personasubcategorymapping',
            name='persona',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subcategory_mappings', to='simulator.persona'),
        ),
        migrations.AlterField(
            model_name='subcategory',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
