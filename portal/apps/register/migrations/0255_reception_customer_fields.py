# Generated manually for RegInteractivOcenkaReception customer fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0254_reception_pts_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_type',
            field=models.CharField(
                blank=True,
                choices=[('fl', 'Физическое лицо'), ('ul', 'Юридическое лицо'), ('ip', 'ИП')],
                default='',
                max_length=8,
                verbose_name='Тип клиента',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_inn',
            field=models.CharField(blank=True, default='', max_length=12, verbose_name='ИНН'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_kpp',
            field=models.CharField(blank=True, default='', max_length=9, verbose_name='КПП'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_ogrn',
            field=models.CharField(blank=True, default='', max_length=15, verbose_name='ОГРН / ОГРНИП'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_company_name',
            field=models.CharField(
                blank=True, default='', max_length=512, verbose_name='Наименование организации / ИП',
            ),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_legal_address',
            field=models.CharField(blank=True, default='', max_length=512, verbose_name='Юридический адрес'),
        ),
        migrations.AddField(
            model_name='reginteractivocenkareception',
            name='customer_vat_rate',
            field=models.CharField(
                blank=True,
                choices=[
                    ('', '—'),
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
