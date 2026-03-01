import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

final testDriveRepositoryProvider = Provider((ref) => InspectionRepository());

class TestDriveScreen extends ConsumerStatefulWidget {
  final int rlkId;

  const TestDriveScreen({
    Key? key,
    required this.rlkId,
  }) : super(key: key);

  @override
  ConsumerState<TestDriveScreen> createState() => _TestDriveScreenState();
}

class _TestDriveScreenState extends ConsumerState<TestDriveScreen> {
  bool _isSaving = false;

  // Состояния систем (0 - не работает, 1 - работает, 2 - есть замечания, 10 - не выбрано)
  final Map<String, int> _systemStates = {
    'engine': 10,
    'system_og': 10,
    'gear': 10,
    'suspension': 10,
    'airbag': 10,
    'wheel': 10,
    'brake': 10,
    'conditioner': 10,
    'turbo': 10,
    'drive': 10,
    'to': 10,
    'subframe': 10,
  };

  // Комментарии к системам
  final Map<String, String> _systemComments = {};

  Future<void> _saveTestDrive() async {
    setState(() {
      _isSaving = true;
    });

    try {
      final repository = ref.read(testDriveRepositoryProvider);
      // TODO: Реализовать сохранение через API
      // await repository.saveTestDrive(...);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Тест-драйв сохранен')),
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
        title: const Text('Тест-драйв'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Проверка систем',
            style: AppTextStyles.h3,
          ),
          const SizedBox(height: 16),
          
          _buildSystemItem('Двигатель', 'engine'),
          _buildSystemItem('Система выпуска ОГ', 'system_og'),
          _buildSystemItem('КПП', 'gear'),
          _buildSystemItem('Подвеска', 'suspension'),
          _buildSystemItem('Подушка безопасности', 'airbag'),
          _buildSystemItem('Рулевое управление', 'wheel'),
          _buildSystemItem('Тормозная система', 'brake'),
          _buildSystemItem('Кондиционер', 'conditioner'),
          _buildSystemItem('Турбо', 'turbo'),
          _buildSystemItem('Привод', 'drive'),
          _buildSystemItem('ТО', 'to'),
          _buildSystemItem('Подрамник', 'subframe'),

          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isSaving ? null : _saveTestDrive,
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

  Widget _buildSystemItem(String title, String key) {
    final state = _systemStates[key] ?? 10;
    final comment = _systemComments[key] ?? '';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: AppTextStyles.body.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: RadioListTile<int>(
                    title: const Text('Не работает'),
                    value: 0,
                    groupValue: state,
                    onChanged: (value) {
                      setState(() => _systemStates[key] = value ?? 10);
                    },
                  ),
                ),
                Expanded(
                  child: RadioListTile<int>(
                    title: const Text('Работает'),
                    value: 1,
                    groupValue: state,
                    onChanged: (value) {
                      setState(() => _systemStates[key] = value ?? 10);
                    },
                  ),
                ),
                Expanded(
                  child: RadioListTile<int>(
                    title: const Text('Есть замечания'),
                    value: 2,
                    groupValue: state,
                    onChanged: (value) {
                      setState(() => _systemStates[key] = value ?? 10);
                    },
                  ),
                ),
              ],
            ),
            if (state == 2) ...[
              const SizedBox(height: 8),
              TextField(
                decoration: const InputDecoration(
                  labelText: 'Комментарий',
                  hintText: 'Опишите замечания',
                ),
                onChanged: (value) {
                  setState(() => _systemComments[key] = value);
                },
                controller: TextEditingController(text: comment),
                maxLines: 3,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

