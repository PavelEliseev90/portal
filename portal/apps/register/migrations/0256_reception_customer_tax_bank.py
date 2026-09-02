# Generated manually for RegInteractivOcenkaReception tax and bank fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0255_reception_customer_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_tax_system',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', '—'),
                    ('osn', 'ОСН (общая)'),
                    ('usn_income', 'УСН «Доходы»'),
                    ('usn_income_expense', 'УСН «Доходы минус расходы»'),
                    ('psn', 'ПСН (патент)'),
                    ('eshn', 'ЕСХН'),
                    ('npd', 'НПД'),
                ],
                default='',
                max_length=32,
                verbose_name='Система налогообложения',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_email',
            field=models.CharField(blank=True, default='', max_length=250, verbose_name='Email'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_contact_person',
            field=models.CharField(blank=True, default='', max_length=250, verbose_name='Контактное лицо'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_actual_address',
            field=models.CharField(blank=True, default='', max_length=512, verbose_name='Фактический адрес'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_bank_name',
            field=models.CharField(blank=True, default='', max_length=512, verbose_name='Банк'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_bank_bik',
            field=models.CharField(blank=True, default='', max_length=9, verbose_name='БИК'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_bank_account',
            field=models.CharField(blank=True, default='', max_length=20, verbose_name='Расчётный счёт'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_bank_corr_account',
            field=models.CharField(
                blank=True, default='', max_length=20, verbose_name='Корреспондентский счёт',
            ),
        ),
        migrations.AlterField(
            model_name='reginteractivocenkareception',
            name='customer_vat_rate',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', '—'),
                    ('22', '22%'),
                    ('20', '20%'),
                    ('10', '10%'),
                    ('7', '7%'),
                    ('5', '5%'),
                    ('0', '0%'),
                    ('none', 'Без НДС'),
                ],
                default='',
                max_length=16,
                verbose_name='Ставка НДС',
            ),
        ),
    ]
