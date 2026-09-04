# Generated manually
# Параллельные листья после 0024_profiles_telegram_chat_id:
#   0025_alter_profiles_telegram_chat_id  (на сервере / другой копии)
#   0025_profiles_telegram_notify_prefs   (настройки уведомлений бота)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0025_alter_profiles_telegram_chat_id'),
        ('profiles', '0025_profiles_telegram_notify_prefs'),
    ]

    operations = [
    ]
