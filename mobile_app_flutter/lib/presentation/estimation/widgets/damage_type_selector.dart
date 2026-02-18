import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';

class DamageTypeSelector extends StatelessWidget {
  final String elementName;
  final bool isSalon;

  const DamageTypeSelector({
    Key? key,
    required this.elementName,
    this.isSalon = false,
  }) : super(key: key);

  List<DamageType> _getDamageTypes() {
    if (isSalon) {
      return [
        DamageType('perecras', 'Перекрас', Icons.palette),
        DamageType('pereshiv', 'Перешив', Icons.content_cut),
        DamageType('dirka', 'Дырка', Icons.crop_free),
        DamageType('vost', 'Восстановление', Icons.build),
      ];
    } else {
      return [
        DamageType('tol', 'Толщиномер', Icons.straighten),
        DamageType('tr', 'Трещина', Icons.crop_free),
        DamageType('skol', 'Скол', Icons.radio_button_unchecked),
        DamageType('vmyat', 'Вмятина', Icons.radio_button_unchecked),
        DamageType('vmyat_strong', 'Вмятина сильная', Icons.radio_button_unchecked),
        DamageType('carap', 'Царапина', Icons.radio_button_unchecked),
        DamageType('carap_strong', 'Царапина сильная', Icons.radio_button_unchecked),
        DamageType('rzav', 'Ржавчина', Icons.radio_button_unchecked),
        DamageType('rzav_strong', 'Ржавчина сквозная', Icons.radio_button_unchecked),
        DamageType('perecras', 'Перекрас', Icons.palette),
        DamageType('perecras_strong', 'Перекрас сильный', Icons.palette),
        DamageType('stiker', 'Наклейка', Icons.label),
        DamageType('toner', 'Тонировка', Icons.visibility),
        DamageType('poly', 'Полировка', Icons.auto_awesome),
        DamageType('replace', 'Заменен', Icons.check_circle),
        DamageType('replace_add', 'Заменить', Icons.add_circle),
      ];
    }
  }

  @override
  Widget build(BuildContext context) {
    final damageTypes = _getDamageTypes();

    return Container(
      padding: const EdgeInsets.all(16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            elementName,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Выберите тип повреждения:',
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 16),
          GridView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              crossAxisSpacing: 8,
              mainAxisSpacing: 8,
              childAspectRatio: 2.5,
            ),
            itemCount: damageTypes.length,
            itemBuilder: (context, index) {
              final type = damageTypes[index];
              return ElevatedButton.icon(
                onPressed: () => Navigator.pop(context, type.code),
                icon: Icon(type.icon),
                label: Text(type.name),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppColors.primary,
                  foregroundColor: Colors.white,
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
        ],
      ),
    );
  }
}

class DamageType {
  final String code;
  final String name;
  final IconData icon;

  DamageType(this.code, this.name, this.icon);
}

