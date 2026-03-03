# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('refs', '0124_refcarsorganizationfiles_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='RefAllowableDiscountKm',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_from', models.DateField(blank=True, null=True, verbose_name='Дата от')),
                ('date_to', models.DateField(blank=True, null=True, verbose_name='Дата до')),
                ('discount_percent', models.FloatField(blank=True, default=0.0, verbose_name='Допустимый дисконт от % КМ')),
                ('brand', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='refs.autorumark', verbose_name='Марка', null=True)),
                ('model', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='refs.autorumodel', verbose_name='Модель')),
                ('modification', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='refs.autorumodification', verbose_name='Модификация')),
                ('complectation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='refs.autorucomplectation', verbose_name='Комплектация')),
            ],
            options={
                'db_table': 'RefAllowableDiscountKm',
                'verbose_name': 'Допустимый дисконт от % КМ (опер. бизнес)',
                'verbose_name_plural': 'Допустимые дисконты от % КМ (опер. бизнес)',
            },
        ),
    ]
