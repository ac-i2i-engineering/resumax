# Generated by Django 5.1.3 on 2025-03-08 23:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("resumax_algo", "0003_remove_conversation_bot_response_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="conversation",
            old_name="text_input",
            new_name="prompt",
        ),
        migrations.RenameField(
            model_name="conversation",
            old_name="ai_response",
            new_name="response",
        ),
    ]
