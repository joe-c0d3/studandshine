# Generated by Django 5.1.5 on 2025-06-06 16:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_passwordreset_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='passwordreset',
            name='user',
        ),
    ]
