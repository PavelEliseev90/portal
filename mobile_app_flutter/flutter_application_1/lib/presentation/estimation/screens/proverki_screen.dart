import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

final proverkiRepositoryProvider = Provider((ref) => InspectionRepository());

class ProverkiScreen extends ConsumerStatefulWidget {
  final int rlkId;

  const ProverkiScreen({
    Key? key,
    required this.rlkId,
  }) : super(key: key);

  @override
  ConsumerState<ProverkiScreen> createState() => _ProverkiScreenState();
}

class _ProverkiScreenState extends ConsumerState<ProverkiScreen> {
  bool _isSaving = false;

  // Список проверок (можно расширить)
  final List<Map<String, dynamic>> _proverki = [
    {'name': 'Проверка 1', 'checked': false, 'comment': ''},
    {'name': 'Проверка 2', 'checked': false, 'comment': ''},
    {'name': 'Проверка 3', 'checked': false, 'comment': ''},
  ];

  Future<void> _saveProverki() async {
    setState(() {
      _isSaving = true;
    });

    try {
      final repository = ref.read(proverkiRepositoryProvider);
      // TODO: Реализовать сохранение через API
      // await repository.saveProverki(...);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Проверки сохранены')),
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
        title: const Text('Проверки'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Список проверок',
            style: AppTextStyles.h3,
          ),
          const SizedBox(height: 16),
          
          ..._proverki.asMap().entries.map((entry) {
            final index = entry.key;
            final proverka = entry.value;
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: CheckboxListTile(
                title: Text(proverka['name']),
                value: proverka['checked'],
                onChanged: (value) {
                  setState(() {
                    _proverki[index]['checked'] = value ?? false;
                  });
                },
                subtitle: proverka['checked']
                    ? TextField(
                        decoration: const InputDecoration(
                          labelText: 'Комментарий',
                          hintText: 'Добавьте комментарий',
                        ),
                        onChanged: (value) {
                          setState(() {
                            _proverki[index]['comment'] = value;
                          });
                        },
                        controller: TextEditingController(
                          text: proverka['comment'],
                        ),
                      )
                    : null,
              ),
            );
          }),

          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isSaving ? null : _saveProverki,
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
}

