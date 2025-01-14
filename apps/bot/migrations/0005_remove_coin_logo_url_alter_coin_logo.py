# Generated by Django 4.2 on 2024-08-27 12:01

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bot", "0004_alter_coin_logo"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="coin",
            name="logo_url",
        ),
        migrations.AlterField(
            model_name="coin",
            name="logo",
            field=models.ImageField(
                blank=True, null=True, upload_to="coin_logos/", verbose_name="Logo"
            ),
        ),
    ]
