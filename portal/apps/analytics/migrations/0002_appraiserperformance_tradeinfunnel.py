from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppraiserPerformanceSnapshot',
            fields=[
                ('estimation_id', models.PositiveIntegerField(help_text='ID RegInteractivOcenka', primary_key=True, serialize=False)),
                ('rlk_id', models.PositiveIntegerField(blank=True, help_text='ID DocRLK', null=True)),
                ('worksheet_created_at', models.DateTimeField(blank=True, null=True)),
                ('start_estimation', models.DateTimeField(blank=True, null=True)),
                ('end_estimation', models.DateTimeField(blank=True, null=True)),
                ('unit_id', models.PositiveIntegerField(blank=True, null=True)),
                ('unit_name', models.CharField(blank=True, max_length=255)),
                ('unit_source', models.CharField(blank=True, max_length=32)),
                ('staff_id', models.PositiveIntegerField(blank=True, null=True)),
                ('staff_name', models.CharField(blank=True, max_length=255)),
                ('source_type', models.CharField(blank=True, max_length=255)),
                ('status_id', models.PositiveIntegerField(blank=True, null=True)),
                ('status_name', models.CharField(blank=True, max_length=255)),
                ('has_soglasovanie', models.BooleanField(default=False)),
                ('has_diagnostics', models.BooleanField(default=False)),
                ('accepted', models.BooleanField(default=False)),
                ('price_offer', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_agreed', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_reception', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_sale', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_auto_selected', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('diff_vs_auto', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('cost_total', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('duration_estimation_sec', models.IntegerField(blank=True, null=True)),
                ('duration_to_accept_sec', models.IntegerField(blank=True, null=True)),
                ('duration_to_sale_sec', models.IntegerField(blank=True, null=True)),
                ('days_in_stock', models.IntegerField(blank=True, null=True)),
                ('tasks_total', models.IntegerField(blank=True, null=True)),
                ('tasks_closed', models.IntegerField(blank=True, null=True)),
                ('extra_payload', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Витрина оценщиков',
                'verbose_name_plural': 'Витрина оценщиков',
            },
        ),
        migrations.CreateModel(
            name='TradeInFunnelSnapshot',
            fields=[
                ('rlk_id', models.PositiveIntegerField(help_text='ID DocRLK', primary_key=True, serialize=False)),
                ('worksheet_number', models.CharField(blank=True, max_length=255)),
                ('unit_id', models.PositiveIntegerField(blank=True, null=True)),
                ('unit_name', models.CharField(blank=True, max_length=255)),
                ('unit_source', models.CharField(blank=True, max_length=32)),
                ('staff_id', models.PositiveIntegerField(blank=True, null=True)),
                ('staff_name', models.CharField(blank=True, max_length=255)),
                ('analyst_before_id', models.PositiveIntegerField(blank=True, null=True)),
                ('analyst_after_id', models.PositiveIntegerField(blank=True, null=True)),
                ('source_type', models.CharField(blank=True, max_length=255)),
                ('type_reception_id', models.PositiveIntegerField(blank=True, null=True)),
                ('date_work_order', models.DateTimeField(blank=True, null=True)),
                ('date_evaluation', models.DateTimeField(blank=True, null=True)),
                ('date_diagnostic', models.DateTimeField(blank=True, null=True)),
                ('date_acceptance', models.DateTimeField(blank=True, null=True)),
                ('date_sale', models.DateTimeField(blank=True, null=True)),
                ('date_market', models.DateTimeField(blank=True, null=True)),
                ('price_offer', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_agreed_before', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_agreed_after', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_reception', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_sale', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_market', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('cost_total', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('duration_to_evaluation_sec', models.IntegerField(blank=True, null=True)),
                ('duration_to_diagnostic_sec', models.IntegerField(blank=True, null=True)),
                ('duration_to_acceptance_sec', models.IntegerField(blank=True, null=True)),
                ('duration_to_sale_sec', models.IntegerField(blank=True, null=True)),
                ('accepted', models.BooleanField(default=False)),
                ('sold', models.BooleanField(default=False)),
                ('went_to_market', models.BooleanField(default=False)),
                ('stage', models.CharField(blank=True, help_text='Текущая стадия воронки', max_length=64)),
                ('extra_payload', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Витрина воронки Trade-In',
                'verbose_name_plural': 'Витрина воронки Trade-In',
            },
        ),
        migrations.AddIndex(
            model_name='appraiserperformancesnapshot',
            index=models.Index(fields=['worksheet_created_at'], name='analytics_a_worksheet_2b0a6c_idx'),
        ),
        migrations.AddIndex(
            model_name='appraiserperformancesnapshot',
            index=models.Index(fields=['unit_id'], name='analytics_a_unit_i_7fef94_idx'),
        ),
        migrations.AddIndex(
            model_name='appraiserperformancesnapshot',
            index=models.Index(fields=['staff_id'], name='analytics_a_staff_i_d27416_idx'),
        ),
        migrations.AddIndex(
            model_name='appraiserperformancesnapshot',
            index=models.Index(fields=['status_id'], name='analytics_a_status__250a64_idx'),
        ),
        migrations.AddIndex(
            model_name='tradeinfunnelsnapshot',
            index=models.Index(fields=['date_work_order'], name='analytics_t_date_wo_2347c6_idx'),
        ),
        migrations.AddIndex(
            model_name='tradeinfunnelsnapshot',
            index=models.Index(fields=['unit_id'], name='analytics_t_unit_i_1c90be_idx'),
        ),
        migrations.AddIndex(
            model_name='tradeinfunnelsnapshot',
            index=models.Index(fields=['staff_id'], name='analytics_t_staff_i_d25263_idx'),
        ),
        migrations.AddIndex(
            model_name='tradeinfunnelsnapshot',
            index=models.Index(fields=['stage'], name='analytics_t_stage_8e61f0_idx'),
        ),
    ]

