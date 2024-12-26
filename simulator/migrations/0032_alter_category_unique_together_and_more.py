# Generated by Django 4.2.17 on 2024-12-25 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0031_rawpersonamodel'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='category',
            unique_together={('name', 'city')},
        ),
        migrations.AlterUniqueTogether(
            name='subcategory',
            unique_together={('category', 'name', 'city')},
        ),
        migrations.AddIndex(
            model_name='category',
            index=models.Index(fields=['name', 'city'], name='simulator_c_name_c304d1_idx'),
        ),
        migrations.AddIndex(
            model_name='subcategory',
            index=models.Index(fields=['category', 'name', 'city'], name='simulator_s_categor_f8eb7d_idx'),
        ),
    ]