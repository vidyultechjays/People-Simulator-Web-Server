# Generated by Django 5.1.3 on 2024-12-11 09:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('simulator', '0017_category_city'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='subcategory',
            unique_together=set(),
        ),
    ]
