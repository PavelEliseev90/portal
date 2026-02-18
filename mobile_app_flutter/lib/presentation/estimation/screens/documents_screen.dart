import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

final documentsRepositoryProvider = Provider((ref) => InspectionRepository());

class DocumentsScreen extends ConsumerStatefulWidget {
  final int rlkId;

  const DocumentsScreen({
    Key? key,
    required this.rlkId,
  }) : super(key: key);

  @override
  ConsumerState<DocumentsScreen> createState() => _DocumentsScreenState();
}

class _DocumentsScreenState extends ConsumerState<DocumentsScreen> {
  final _formKey = GlobalKey<FormState>();
  bool _isSaving = false;

  // Поля формы
  final _customerFamilyController = TextEditingController();
  final _customerNameController = TextEditingController();
  final _customerPatronymicController = TextEditingController();
  final _customerPhoneController = TextEditingController();
  final _plateNumberController = TextEditingController();
  final _engineNumberController = TextEditingController();
  final _ptsNumberController = TextEditingController();
  final _ptsColorController = TextEditingController();
  final _stsNumberController = TextEditingController();
  final _countOwnersController = TextEditingController();
  final _countKeysController = TextEditingController();

  DateTime? _ptsDate;
  DateTime? _stsDate;
  int? _organizationId;
  int? _filialId;
  int? _unitId;
  int? _storeId;
  int? _typeReceptionId;
  String? _typeDrive;

  @override
  void dispose() {
    _customerFamilyController.dispose();
    _customerNameController.dispose();
    _customerPatronymicController.dispose();
    _customerPhoneController.dispose();
    _plateNumberController.dispose();
    _engineNumberController.dispose();
    _ptsNumberController.dispose();
    _ptsColorController.dispose();
    _stsNumberController.dispose();
    _countOwnersController.dispose();
    _countKeysController.dispose();
    super.dispose();
  }

  Future<void> _selectDate(BuildContext context, bool isPts) async {
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(1900),
      lastDate: DateTime.now(),
    );
    if (picked != null) {
      setState(() {
        if (isPts) {
          _ptsDate = picked;
        } else {
          _stsDate = picked;
        }
      });
    }
  }

  Future<void> _saveDocuments() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isSaving = true;
    });

    try {
      final repository = ref.read(documentsRepositoryProvider);
      // TODO: Реализовать сохранение через API
      // await repository.saveDocuments(...);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Документы сохранены')),
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
        title: const Text('Документы'),
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Данные клиента
            Text(
              'Данные клиента',
              style: AppTextStyles.h3,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _customerFamilyController,
              decoration: const InputDecoration(
                labelText: 'Фамилия',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _customerNameController,
              decoration: const InputDecoration(
                labelText: 'Имя',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _customerPatronymicController,
              decoration: const InputDecoration(
                labelText: 'Отчество',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _customerPhoneController,
              decoration: const InputDecoration(
                labelText: 'Телефон',
              ),
              keyboardType: TextInputType.phone,
            ),
            const SizedBox(height: 24),

            // Данные автомобиля
            Text(
              'Данные автомобиля',
              style: AppTextStyles.h3,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _plateNumberController,
              decoration: const InputDecoration(
                labelText: 'Гос. номер',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _engineNumberController,
              decoration: const InputDecoration(
                labelText: 'Номер двигателя',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _ptsNumberController,
              decoration: const InputDecoration(
                labelText: 'Номер ПТС',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _ptsColorController,
              decoration: const InputDecoration(
                labelText: 'Цвет по ПТС',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _stsNumberController,
              decoration: const InputDecoration(
                labelText: 'Номер СТС',
              ),
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _countOwnersController,
              decoration: const InputDecoration(
                labelText: 'Количество владельцев',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 8),
            TextFormField(
              controller: _countKeysController,
              decoration: const InputDecoration(
                labelText: 'Количество ключей',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),

            // Даты
            ListTile(
              title: Text(_ptsDate == null
                  ? 'Дата ПТС'
                  : 'Дата ПТС: ${_ptsDate!.day}.${_ptsDate!.month}.${_ptsDate!.year}'),
              trailing: const Icon(Icons.calendar_today),
              onTap: () => _selectDate(context, true),
            ),
            ListTile(
              title: Text(_stsDate == null
                  ? 'Дата СТС'
                  : 'Дата СТС: ${_stsDate!.day}.${_stsDate!.month}.${_stsDate!.year}'),
              trailing: const Icon(Icons.calendar_today),
              onTap: () => _selectDate(context, false),
            ),

            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: _isSaving ? null : _saveDocuments,
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
      ),
    );
  }
}

