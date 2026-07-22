from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from car_preparation.models import RefCarPreparationWork, RefPreparationMaterial
from register.models import RegPodgotovkaWork

from .models import (
    EstimationPlanLine,
    EstimationRule,
    LegacyWorkMapping,
    PreparationMaterialProfile,
    PreparationPart,
    PreparationPartCompatibility,
    PreparationService,
    PreparationServiceOffering,
    PreparationServiceProvider,
    PreparationWorkPackage,
    PreparationWorkPackageLine,
)
from .transfer import TransferError, _hours_to_minutes, resolve_car_for_snapshot


class CatalogValidationTests(SimpleTestCase):
    """Проверки clean() без обращения к БД."""

    def test_material_profile_rejects_negative_process_loss(self):
        profile = PreparationMaterialProfile(
            code='MAT-001',
            process_loss_percent=Decimal('-1.00'),
        )
        with self.assertRaises(ValidationError):
            profile.clean()

    def test_part_compatibility_requires_scope(self):
        part = PreparationPart(code='PART-001', name='Стекло')
        compat = PreparationPartCompatibility(part=part)
        with self.assertRaises(ValidationError):
            compat.clean()

    def test_part_compatibility_rejects_inverted_years(self):
        part = PreparationPart(code='PART-001', name='Стекло')
        compat = PreparationPartCompatibility(
            part=part,
            year_from=2024,
            year_to=2020,
        )
        compat.mark_id = 1
        with self.assertRaises(ValidationError):
            compat.clean()

    def test_provider_rejects_inverted_contract_dates(self):
        provider = PreparationServiceProvider(
            code='PRV-001',
            name='Подрядчик',
            contract_valid_from=date.today(),
            contract_valid_to=date.today() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            provider.clean()

    def test_offering_rejects_inverted_valid_dates(self):
        offering = PreparationServiceOffering(
            code='OFF-001',
            valid_from=date.today(),
            valid_to=date.today() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            offering.clean()

    def test_package_line_requires_matching_reference(self):
        package = PreparationWorkPackage(code='PKG-1', name='Покраска крыла без ремонта')
        line = PreparationWorkPackageLine(
            package=package,
            line_type=PreparationWorkPackageLine.LINE_WORK,
        )
        with self.assertRaises(ValidationError):
            line.clean()

    def test_published_in_house_package_requires_repair_zone(self):
        package = PreparationWorkPackage(
            code='PKG-1',
            name='Покраска',
            route_type=PreparationWorkPackage.ROUTE_IN_HOUSE,
            status=PreparationWorkPackage.STATUS_PUBLISHED,
        )
        with self.assertRaises(ValidationError):
            package.clean()

    def test_plan_line_work_requires_work_ref(self):
        line = EstimationPlanLine(
            line_type=EstimationPlanLine.LINE_WORK,
            name='Покраска',
        )
        with self.assertRaises(ValidationError):
            line.clean()


class TransferHelperTests(SimpleTestCase):
    def test_hours_to_minutes(self):
        self.assertEqual(_hours_to_minutes(1.5), 90)
        self.assertEqual(_hours_to_minutes(None), 0)

    def test_resolve_car_requires_vin(self):
        snapshot = MagicMock()
        snapshot.car_id = None
        snapshot.car = None
        snapshot.vin = ''
        snapshot.estimation_id = None
        with self.assertRaises(TransferError):
            resolve_car_for_snapshot(snapshot)


class CatalogModelTests(TestCase):
    """Интеграционные проверки ограничений на БД."""

    def setUp(self):
        self.legacy_work = RegPodgotovkaWork.objects.create(
            name='Покраска крыла',
            name_group='Кузов',
        )
        self.target_work = RefCarPreparationWork.objects.create(
            name='Покраска крыла',
            code='WORK-PAINT-WING',
        )
        self.material = RefPreparationMaterial.objects.create(
            name='Грунт',
            code='MAT-PRIMER',
            uom='л',
        )

    def test_legacy_work_mapping_is_one_to_one(self):
        LegacyWorkMapping.objects.create(
            legacy_work=self.legacy_work,
            target_work=self.target_work,
            review_status=LegacyWorkMapping.REVIEW_STATUS_DRAFT,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                LegacyWorkMapping.objects.create(
                    legacy_work=self.legacy_work,
                    target_work=self.target_work,
                )

    def test_work_package_with_lines(self):
        package = PreparationWorkPackage.objects.create(
            code='PKG-PAINT-WING',
            name='Покраска крыла без ремонта',
            section=PreparationWorkPackage.SECTION_EXTERIOR,
            route_type=PreparationWorkPackage.ROUTE_IN_HOUSE,
            status=PreparationWorkPackage.STATUS_DRAFT,
        )
        line = PreparationWorkPackageLine.objects.create(
            package=package,
            line_type=PreparationWorkPackageLine.LINE_WORK,
            work=self.target_work,
            coverage_key='paint-wing',
            norm_hours=Decimal('1.50'),
        )
        self.assertEqual(package.lines.count(), 1)
        self.assertEqual(line.work_id, self.target_work.id)


class PackageApplyHelpersTests(SimpleTestCase):
    def test_hours_to_minutes(self):
        from .package_apply import PackageApplyError, _hours_to_minutes

        self.assertEqual(_hours_to_minutes(1.5), 90)
        self.assertEqual(_hours_to_minutes(0), 0)
        self.assertEqual(_hours_to_minutes(None), 0)
        self.assertTrue(issubclass(PackageApplyError, Exception))


class RulesEngineSimpleTests(SimpleTestCase):
    def test_rule_matches_and_conditions(self):
        from .rules_engine import rule_matches

        rule = EstimationRule(
            code='R1',
            name='Test',
            section='exterior',
            element_code='wing_fl',
            damage_type='dent',
            min_damage_count=1,
            price_group='2000',
        )
        ok, _ = rule_matches(rule, {
            'section': 'exterior',
            'element_code': 'wing_fl',
            'damage_type': 'dent',
            'damage_count': 2,
            'price_group': '2000',
        })
        self.assertTrue(ok)

        ok, reason = rule_matches(rule, {
            'section': 'exterior',
            'element_code': 'wing_fl',
            'damage_type': 'scratch',
            'damage_count': 2,
            'price_group': '2000',
        })
        self.assertFalse(ok)
        self.assertIn('повреждение', reason)

    def test_body_types_multi_match(self):
        from .rules_engine import rule_matches

        rule = EstimationRule(
            code='BODY',
            name='Седан/хэтч',
            min_damage_count=0,
            body_type='Седан, Хэтчбек',
        )
        self.assertTrue(rule_matches(rule, {'body_type': 'седан'})[0])
        self.assertTrue(rule_matches(rule, {'body_type': 'Хэтчбек'})[0])
        ok, reason = rule_matches(rule, {'body_type': 'универсал'})
        self.assertFalse(ok)
        self.assertIn('кузов', reason)

        rule2 = EstimationRule(code='BODY2', name='IDs', min_damage_count=0)
        rule2._body_types = [
            {'id': 1, 'name': 'Седан'},
            {'id': 2, 'name': 'Хэтчбек'},
        ]
        self.assertTrue(rule_matches(rule2, {'body_type_id': 2})[0])
        self.assertFalse(rule_matches(rule2, {'body_type_id': 9, 'body_type': 'купе'})[0])

    def test_empty_body_types_match_any(self):
        """Пустой список кузовов в правиле = применяется ко всем (в т.ч. без кузова в фактах)."""
        from .rules_engine import rule_matches

        rule = EstimationRule(code='ANY', name='Любой кузов', min_damage_count=0, body_type='')
        rule._body_types = []
        self.assertTrue(rule_matches(rule, {})[0])
        self.assertTrue(rule_matches(rule, {'body_type': 'седан'})[0])
        self.assertTrue(rule_matches(rule, {'body_type_id': 5, 'body_type': 'купе'})[0])

        rule2 = EstimationRule(code='ANY2', name='Без M2M', min_damage_count=0, body_type='')
        self.assertTrue(rule_matches(rule2, {})[0])

    def test_condition_scratch_gt3_and_no_dents(self):
        from .models import EstimationRuleCondition
        from .rules_engine import rule_matches

        rule = EstimationRule(
            code='SCR',
            name='Много царапин без вмятин',
            min_damage_count=0,
        )
        rule._conditions = [
            EstimationRuleCondition(
                join_op='and',
                field='damage_type_count',
                damage_type='scratch',
                operator='gt',
                value='3',
                is_active=True,
            ),
            EstimationRuleCondition(
                join_op='and',
                field='damage_type_count',
                damage_type='dent',
                operator='absent',
                value='',
                is_active=True,
            ),
        ]

        ok, _ = rule_matches(rule, {
            'damage_counts': {'scratch': 4, 'dent': 0},
        })
        self.assertTrue(ok)

        ok, reason = rule_matches(rule, {
            'damage_counts': {'scratch': 4, 'dent': 1},
        })
        self.assertFalse(ok)
        self.assertIn('условия', reason)

        ok, _ = rule_matches(rule, {
            'damage_counts': {'scratch': 3, 'dent': 0},
        })
        self.assertFalse(ok)

    def test_condition_or_chain(self):
        from .models import EstimationRuleCondition
        from .rules_engine import rule_matches

        rule = EstimationRule(code='OR1', name='OR', min_damage_count=0)
        rule._conditions = [
            EstimationRuleCondition(
                field='damage_type_count',
                damage_type='scratch',
                operator='gte',
                value='5',
                join_op='and',
                is_active=True,
            ),
            EstimationRuleCondition(
                field='damage_type_count',
                damage_type='dent',
                operator='gte',
                value='2',
                join_op='or',
                is_active=True,
            ),
        ]
        self.assertTrue(rule_matches(rule, {'damage_counts': {'scratch': 5, 'dent': 0}})[0])
        self.assertTrue(rule_matches(rule, {'damage_counts': {'scratch': 0, 'dent': 2}})[0])
        self.assertFalse(rule_matches(rule, {'damage_counts': {'scratch': 1, 'dent': 1}})[0])

    def test_windshield_flags_four_variants(self):
        from .rules_engine import rule_matches

        base = dict(
            code='WS',
            name='Лобовое',
            element_code='windshield',
            damage_type='crack',
            min_damage_count=0,
        )
        plain = EstimationRule(
            **base,
            windshield_heat='no',
            windshield_projection='no',
        )
        heat = EstimationRule(
            **base,
            windshield_heat='yes',
            windshield_projection='no',
        )
        hud = EstimationRule(
            **base,
            windshield_heat='no',
            windshield_projection='yes',
        )
        both = EstimationRule(
            **base,
            windshield_heat='yes',
            windshield_projection='yes',
        )

        facts_both = {
            'element_code': 'windshield',
            'damage_type': 'crack',
            'damage_count': 1,
            'windshield_heat': True,
            'windshield_projection': True,
        }
        self.assertTrue(rule_matches(both, facts_both)[0])
        self.assertFalse(rule_matches(plain, facts_both)[0])
        self.assertFalse(rule_matches(heat, facts_both)[0])
        self.assertFalse(rule_matches(hud, facts_both)[0])

        facts_heat = dict(facts_both, windshield_projection=False)
        self.assertTrue(rule_matches(heat, facts_heat)[0])
        self.assertFalse(rule_matches(both, facts_heat)[0])
        self.assertFalse(rule_matches(plain, facts_heat)[0])

        # «Любое» не фильтрует по флагу
        any_heat = EstimationRule(**base, windshield_heat='', windshield_projection='yes')
        self.assertTrue(rule_matches(any_heat, {
            'element_code': 'windshield',
            'damage_type': 'crack',
            'damage_count': 1,
            'windshield_heat': False,
            'windshield_projection': True,
        })[0])
        self.assertTrue(rule_matches(any_heat, {
            'element_code': 'windshield',
            'damage_type': 'crack',
            'damage_count': 1,
            'windshield_heat': True,
            'windshield_projection': True,
        })[0])

    def test_cleaning_level_and_salon_type(self):
        from .rules_engine import rule_matches

        rule = EstimationRule(
            code='CLN',
            name='Химчистка кожа',
            cleaning_level=EstimationRule.CLEANING_HARD,
            salon_type=EstimationRule.SALON_LEATHER,
        )
        self.assertTrue(rule_matches(rule, {
            'cleaning_level': '1',
            'salon_type': '1',
        })[0])
        self.assertTrue(rule_matches(rule, {
            'cleaning_int': 1,
            'type_salon_int': 1,
        })[0])
        self.assertFalse(rule_matches(rule, {
            'cleaning_level': '3',
            'salon_type': '1',
        })[0])
        self.assertFalse(rule_matches(rule, {
            'cleaning_level': '1',
            'salon_type': '0',
        })[0])

        any_rule = EstimationRule(code='ANY', name='Любая химчистка')
        self.assertTrue(rule_matches(any_rule, {'cleaning_level': '2', 'salon_type': '0'})[0])

    def test_diagnostic_system_and_status(self):
        from .rules_engine import rule_matches

        rule = EstimationRule(
            code='ENG',
            name='Двигатель замечания',
            diagnostic_system=EstimationRule.DIAG_SYSTEM_ENGINE,
            diagnostic_status=EstimationRule.DIAG_STATUS_REMARKS,
        )
        self.assertTrue(rule_matches(rule, {
            'diagnostic_system': 'engine',
            'diagnostic_status': '2',
        })[0])
        self.assertTrue(rule_matches(rule, {
            'engine': 2,
        })[0])
        self.assertFalse(rule_matches(rule, {
            'engine': 0,
        })[0])
        self.assertFalse(rule_matches(rule, {
            'gear': 2,
        })[0])

    def test_line_cost_work_uses_hour_rate(self):
        from .rules_engine import _line_cost

        line = PreparationWorkPackageLine(
            line_type=PreparationWorkPackageLine.LINE_WORK,
            norm_hours=Decimal('1.5'),
            quantity=Decimal('1'),
            unit_cost=Decimal('0'),
        )
        self.assertEqual(_line_cost(line, Decimal('1000')), Decimal('1500'))

    def test_line_cost_material_uses_unit_cost(self):
        from .rules_engine import _line_cost

        line = PreparationWorkPackageLine(
            line_type=PreparationWorkPackageLine.LINE_MATERIAL,
            quantity=Decimal('2'),
            unit_cost=Decimal('250'),
            norm_hours=Decimal('0'),
        )
        self.assertEqual(_line_cost(line, Decimal('1000')), Decimal('500'))

