from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='InteractivePricingSnapshot',
            fields=[
                ('estimation_id', models.PositiveIntegerField(help_text='ID записи RegInteractivOcenka', primary_key=True, serialize=False)),
                ('rlk_id', models.PositiveIntegerField(blank=True, help_text='ID рабочего листа DocRLK', null=True)),
                ('start_estimation', models.DateTimeField()),
                ('end_estimation', models.DateTimeField(blank=True, null=True)),
                ('unit_id', models.PositiveIntegerField(blank=True, null=True)),
                ('unit_name', models.CharField(blank=True, max_length=255)),
                ('unit_source', models.CharField(blank=True, help_text='unit | unit_dc | page_documents__unit', max_length=32)),
                ('staff_id', models.PositiveIntegerField(blank=True, null=True)),
                ('staff_name', models.CharField(blank=True, max_length=255)),
                ('analyst_before_id', models.PositiveIntegerField(blank=True, null=True)),
                ('analyst_before_name', models.CharField(blank=True, max_length=255)),
                ('analyst_after_id', models.PositiveIntegerField(blank=True, null=True)),
                ('analyst_after_name', models.CharField(blank=True, max_length=255)),
                ('type_reception_id', models.PositiveIntegerField(blank=True, null=True)),
                ('status_id', models.PositiveIntegerField(blank=True, null=True)),
                ('status_name', models.CharField(blank=True, max_length=255)),
                ('model_name', models.CharField(blank=True, max_length=255)),
                ('vin', models.CharField(blank=True, max_length=64)),
                ('price_auto_1', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_auto_2', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_auto_3', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_auto_selected', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_before_kd', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_after_kd', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('diff_before', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('diff_after', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_auto_bcp', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_bcp', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_reception', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('price_sale', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('cost_podgotovka', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('cost_ss', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('cost_mcu', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('cost_recovery', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('cost_total', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ('has_soglasovanie', models.BooleanField(default=False)),
                ('has_diagnostics', models.BooleanField(default=False)),
                ('duration_estimation_sec', models.IntegerField(blank=True, null=True)),
                ('duration_sogl_before_sec', models.IntegerField(blank=True, null=True)),
                ('duration_diagnostics_sec', models.IntegerField(blank=True, null=True)),
                ('duration_sogl_after_sec', models.IntegerField(blank=True, null=True)),
                ('extra_payload', models.JSONField(blank=True, null=True, help_text='Дополнительные предрасчитанные данные')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Витрина интерактивных согласований',
                'verbose_name_plural': 'Витрина интерактивных согласований',
            },
        ),
        migrations.AddIndex(
            model_name='interactivepricingsnapshot',
            index=models.Index(fields=['start_estimation'], name='analytics_i_start_e_6f4f74_idx'),
        ),
        migrations.AddIndex(
            model_name='interactivepricingsnapshot',
            index=models.Index(fields=['unit_id'], name='analytics_i_unit_i_3dcf64_idx'),
        ),
        migrations.AddIndex(
            model_name='interactivepricingsnapshot',
            index=models.Index(fields=['staff_id'], name='analytics_i_staff_i_365f64_idx'),
        ),
        migrations.AddIndex(
            model_name='interactivepricingsnapshot',
            index=models.Index(fields=['analyst_before_id'], name='analytics_i_analyst_4b1df8_idx'),
        ),
        migrations.AddIndex(
            model_name='interactivepricingsnapshot',
            index=models.Index(fields=['analyst_after_id'], name='analytics_i_analyst_b3951a_idx'),
        ),
        migrations.AddIndex(
            model_name='interactivepricingsnapshot',
            index=models.Index(fields=['type_reception_id'], name='analytics_i_type_re_26a4eb_idx'),
        ),
        migrations.AddIndex(
            model_name='interactivepricingsnapshot',
            index=models.Index(fields=['status_id'], name='analytics_i_status_i_932d18_idx'),
        ),
    ]

