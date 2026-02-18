import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

final complectnostRepositoryProvider = Provider((ref) => InspectionRepository());

class ComplectnostScreen extends ConsumerStatefulWidget {
  final int rlkId;

  const ComplectnostScreen({
    Key? key,
    required this.rlkId,
  }) : super(key: key);

  @override
  ConsumerState<ComplectnostScreen> createState() => _ComplectnostScreenState();
}

class _ComplectnostScreenState extends ConsumerState<ComplectnostScreen> {
  bool _isSaving = false;

  // Состояния элементов комплектности
  bool _prikur = false;
  bool _ognet = false;
  bool _kovrik = false;
  bool _tros = false;
  bool _domkrat = false;
  bool _znakAv = false;
  bool _ballKey = false;
  bool _zapas = false;
  bool _aptechka = false;

  Future<void> _saveComplectnost() async {
    setState(() {
      _isSaving = true;
    });

    try {
      final repository = ref.read(complectnostRepositoryProvider);
      // TODO: Реализовать сохранение через API
      // await repository.saveComplectnost(...);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Комплектность сохранена')),
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
        title: const Text('Комплектность'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Элементы комплектности',
            style: AppTextStyles.h3,
          ),
          const SizedBox(height: 16),
          
          _buildCheckboxTile('Прикуриватель', _prikur, (value) {
            setState(() => _prikur = value);
          }),
          _buildCheckboxTile('Огнетушитель', _ognet, (value) {
            setState(() => _ognet = value);
          }),
          _buildCheckboxTile('Коврик', _kovrik, (value) {
            setState(() => _kovrik = value);
          }),
          _buildCheckboxTile('Трос', _tros, (value) {
            setState(() => _tros = value);
          }),
          _buildCheckboxTile('Домкрат', _domkrat, (value) {
            setState(() => _domkrat = value);
          }),
          _buildCheckboxTile('Знак аварийной остановки', _znakAv, (value) {
            setState(() => _znakAv = value);
          }),
          _buildCheckboxTile('Баллонный ключ', _ballKey, (value) {
            setState(() => _ballKey = value);
          }),
          _buildCheckboxTile('Запасное колесо', _zapas, (value) {
            setState(() => _zapas = value);
          }),
          _buildCheckboxTile('Аптечка', _aptechka, (value) {
            setState(() => _aptechka = value);
          }),

          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isSaving ? null : _saveComplectnost,
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

  Widget _buildCheckboxTile(String title, bool value, ValueChanged<bool> onChanged) {
    return CheckboxListTile(
      title: Text(title),
      value: value,
      onChanged: (newValue) => onChanged(newValue ?? false),
    );
  }
}

