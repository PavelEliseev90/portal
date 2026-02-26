import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

final kolesaRepositoryProvider = Provider((ref) => InspectionRepository());

class KolesaScreen extends ConsumerStatefulWidget {
  final int rlkId;

  const KolesaScreen({
    Key? key,
    required this.rlkId,
  }) : super(key: key);

  @override
  ConsumerState<KolesaScreen> createState() => _KolesaScreenState();
}

class _KolesaScreenState extends ConsumerState<KolesaScreen> {
  bool _isSaving = false;

  // Состояния колес
  final Map<String, bool> _kolesaStates = {
    'kolesa1': false,
    'kolesa2': false,
    'kolesa3': false,
    'kolesa4': false,
  };

  // Дополнительные данные для колес
  final Map<String, String> _kolesaData = {
    'kolesa1': '',
    'kolesa2': '',
    'kolesa3': '',
    'kolesa4': '',
  };

  Future<void> _saveKolesa() async {
    setState(() {
      _isSaving = true;
    });

    try {
      final repository = ref.read(kolesaRepositoryProvider);
      // TODO: Реализовать сохранение через API
      // await repository.saveKolesa(...);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Колеса сохранены')),
        );
        Navigator.pop(context);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка сохранения: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Колеса'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Состояние колес',
            style: AppTextStyles.h3,
          ),
          const SizedBox(height: 16),
          
          _buildKolesaItem('Переднее левое', 'kolesa1'),
          _buildKolesaItem('Переднее правое', 'kolesa2'),
          _buildKolesaItem('Заднее левое', 'kolesa3'),
          _buildKolesaItem('Заднее правое', 'kolesa4'),

          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isSaving ? null : _saveKolesa,
            child: _isSaving
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  )
                : const Text('Сохранить'),
          ),
        ],
      ),
    );
  }

  Widget _buildKolesaItem(String title, String key) {
    final isChecked = _kolesaStates[key] ?? false;
    final data = _kolesaData[key] ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CheckboxListTile(
              title: Text(title),
              value: isChecked,
              onChanged: (value) {
                setState(() {
                  _kolesaStates[key] = value ?? false;
                });
              },
            ),
            if (isChecked) ...[
              const SizedBox(height: 8),
              TextField(
                decoration: InputDecoration(
                  labelText: 'Дополнительная информация',
                  hintText: 'Введите данные о колесе',
                ),
                onChanged: (value) {
                  setState(() {
                    _kolesaData[key] = value;
                  });
                },
                controller: TextEditingController(text: data),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

