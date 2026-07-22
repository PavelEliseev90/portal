from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auction_avito', '0008_merge_outcome_and_weights'),
    ]

    operations = [
        migrations.CreateModel(
            name='AvitoAutoBidDecision',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lot_id_ext', models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name='lotId')),
                ('lot_offer_id_ext', models.BigIntegerField(blank=True, db_index=True, null=True, verbose_name='lotOfferId')),
                ('should_bid', models.BooleanField(db_index=True, default=False)),
                ('filters_ok', models.BooleanField(default=False)),
                ('reason', models.CharField(blank=True, default='', max_length=500)),
                ('reason_category', models.CharField(blank=True, db_index=True, default='', max_length=40)),
                ('mode', models.CharField(blank=True, default='', max_length=30)),
                ('buyout_price', models.PositiveIntegerField(blank=True, null=True)),
                ('min_available_bid', models.PositiveIntegerField(blank=True, null=True)),
                ('max_bid', models.PositiveIntegerField(blank=True, null=True)),
                ('our_bid', models.PositiveIntegerField(blank=True, null=True)),
                ('next_bid', models.PositiveIntegerField(blank=True, null=True)),
                ('bid_amount', models.PositiveIntegerField(blank=True, null=True)),
                ('year', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('mileage', models.PositiveIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('lot', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='auto_bid_decisions',
                    to='auction_avito.avitolot',
                )),
                ('offer', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='auto_bid_decisions',
                    to='auction_avito.avitolotoffer',
                )),
            ],
            options={
                'verbose_name': 'Решение автоставки',
                'verbose_name_plural': 'Решения автоставок',
                'db_table': 'avitoAutoBidDecision',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='avitoautobiddecision',
            index=models.Index(fields=['created_at', 'reason_category'], name='avitoAutoBi_created_5e8a1c_idx'),
        ),
        migrations.AddIndex(
            model_name='avitoautobiddecision',
            index=models.Index(fields=['should_bid', 'created_at'], name='avitoAutoBi_should__a1b2c3_idx'),
        ),
    ]
