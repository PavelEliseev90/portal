from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Exchange1CErrorLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_create', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Дата')),
                ('exchange_type', models.CharField(db_index=True, help_text='Staffs, Customers, Worksheets и т.д.', max_length=64, verbose_name='Тип (имя массива)')),
                ('data', models.TextField(help_text='JSON элемента массива из пакета 1С', verbose_name='Данные элемента')),
                ('error_description', models.TextField(verbose_name='Описание ошибки')),
            ],
            options={
                'verbose_name': 'Ошибка обмена с 1С',
                'verbose_name_plural': 'Ошибки обмена с 1С',
                'db_table': 'exchange1CErrorLog',
                'ordering': ['-date_create'],
                'indexes': [models.Index(fields=['-date_create', 'exchange_type'], name='exchange1c__date_cr_idx')],
            },
        ),
    ]
