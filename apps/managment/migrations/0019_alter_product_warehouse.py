# Generated by Django 5.1.6 on 2025-03-24 11:00

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('managment', '0018_alter_product_quantity_in_stock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='warehouse',
            field=models.ForeignKey(blank=True, help_text='Warehouse where the product is stored', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='managment.warehouse'),
        ),
    ]
