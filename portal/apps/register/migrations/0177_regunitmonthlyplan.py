# Generated manually to fix migration dependency issue

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('register', '0176_reginteractivocenka_auction_auto_comment_and_more'),
        ('refs', '0118_refservice'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegUnitMonthlyPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField(verbose_name='Год')),
                ('month', models.IntegerField(verbose_name='Месяц')),
                ('intake_plan', models.PositiveIntegerField(default=0, verbose_name='План по приему, шт.')),
                ('sale_plan', models.PositiveIntegerField(default=0, verbose_name='План по продажам, шт.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='refs.refunit', verbose_name='Подразделение')),
            ],
            options={
                'verbose_name': 'План подразделения на месяц',
                'verbose_name_plural': 'Планы подразделений на месяц',
                'db_table': 'regUnitMonthlyPlan',
                'unique_together': {('unit', 'year', 'month')},
            },
        ),
    ]

