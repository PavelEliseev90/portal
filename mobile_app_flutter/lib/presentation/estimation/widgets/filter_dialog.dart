import 'package:flutter/material.dart';
import '../../theme/app_colors.dart';

class FilterDialog extends StatelessWidget {
  final ValueChanged<String> onFilterChanged;

  const FilterDialog({
    Key? key,
    required this.onFilterChanged,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Фильтр'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          ListTile(
            title: const Text('Продолжить оценку'),
            leading: Radio<String>(
              value: '1',
              groupValue: '1',
              onChanged: (value) {
                if (value != null) {
                  onFilterChanged(value);
                  Navigator.pop(context);
                }
              },
            ),
          ),
          ListTile(
            title: const Text('На согласовании'),
            leading: Radio<String>(
              value: '2',
              groupValue: '2',
              onChanged: (value) {
                if (value != null) {
                  onFilterChanged(value);
                  Navigator.pop(context);
                }
              },
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Закрыть'),
        ),
      ],
    );
  }
}

