# Generated by Django 5.1.3 on 2025-03-08 22:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resumax_algo", "0002_conversationsthread_conversation"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="conversation",
            name="bot_response",
        ),
        migrations.RemoveField(
            model_name="conversation",
            name="user",
        ),
        migrations.RemoveField(
            model_name="conversation",
            name="user_prompt",
        ),
        migrations.AddField(
            model_name="conversation",
            name="ai_response",
            field=models.TextField(
                default="", help_text="The bot's response", max_length=500
            ),
        ),
        migrations.AddField(
            model_name="conversation",
            name="text_input",
            field=models.TextField(
                default="", help_text="The user's prompt", max_length=500
            ),
        ),
    ]
