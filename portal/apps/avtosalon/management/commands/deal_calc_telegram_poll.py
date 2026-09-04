"""
Long polling Telegram-бота согласования КП.

Нужен, когда Telegram не может достучаться до webhook портала
(getWebhookInfo → Connection timed out), а сервер до api.telegram.org ходит.

Перед стартом снимите webhook в админке или:
  python manage.py deal_calc_telegram_poll --delete-webhook

Запуск (держать процесс):
  python manage.py deal_calc_telegram_poll
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Long polling бота согласования КП (вместо webhook).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-webhook',
            action='store_true',
            help='Сначала вызвать deleteWebhook (иначе getUpdates не работает).',
        )
        parser.add_argument(
            '--drop-pending',
            action='store_true',
            help='Вместе с --delete-webhook сбросить накопившиеся updates.',
        )
        parser.add_argument(
            '--poll-timeout',
            type=int,
            default=25,
            help='Секунды long poll getUpdates (1..50, default 25).',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Один цикл getUpdates и выход (для проверки).',
        )

    def handle(self, *args, **options):
        from avtosalon.deal_calc_telegram import (
            delete_telegram_webhook,
            get_runtime_config,
            run_telegram_polling_loop,
        )

        runtime = get_runtime_config()
        if not runtime.get('enabled'):
            self.stderr.write(self.style.ERROR(
                'Telegram по КП выключен (DealCalcTelegramSettings.enabled).'
            ))
            return
        if not runtime.get('bot_token'):
            self.stderr.write(self.style.ERROR('Не задан токен бота.'))
            return

        if options['delete_webhook']:
            ok, message = delete_telegram_webhook(drop_pending=options['drop_pending'])
            style = self.style.SUCCESS if ok else self.style.ERROR
            self.stdout.write(style(message))
            if not ok:
                return

        self.stdout.write(self.style.NOTICE(
            'Старт long polling… Ctrl+C для остановки. '
            'proxy={}'.format(runtime.get('proxy') or 'нет')
        ))
        try:
            run_telegram_polling_loop(
                poll_timeout=options['poll_timeout'],
                max_iterations=1 if options['once'] else None,
            )
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Остановлено.'))
            return

        if options['once']:
            self.stdout.write(self.style.SUCCESS('Один цикл getUpdates выполнен.'))
