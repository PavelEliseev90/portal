import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../../data/models/body_element_model.dart';
import '../../../data/models/damage_mark_model.dart';
import '../widgets/body_inspection_widget.dart';
import '../../theme/app_colors.dart';

final inspectionRepositoryProvider =
    Provider((ref) => InspectionRepository());

final bodyElementsProvider = FutureProvider.family<Map<String, dynamic>, Map<String, dynamic>>(
  (ref, params) async {
    final repository = ref.read(inspectionRepositoryProvider);
    return await repository.getBodyElements(
      params['rlkId'] as int,
      params['type'] as String,
    );
  },
);

class BodyInspectionScreen extends ConsumerStatefulWidget {
  final int rlkId;
  final String inspectionType; // pered, vod, pass, zad, up

  const BodyInspectionScreen({
    Key? key,
    required this.rlkId,
    required this.inspectionType,
  }) : super(key: key);

  @override
  ConsumerState<BodyInspectionScreen> createState() =>
      _BodyInspectionScreenState();
}

class _BodyInspectionScreenState
    extends ConsumerState<BodyInspectionScreen> {
  String _getTitle() {
    switch (widget.inspectionType) {
      case 'pered':
        return 'Передняя часть';
      case 'vod':
        return 'Водительская сторона';
      case 'pass':
        return 'Пассажирская сторона';
      case 'zad':
        return 'Задняя часть';
      case 'up':
        return 'Крыша';
      default:
        return 'Осмотр кузова';
    }
  }

  @override
  Widget build(BuildContext context) {
    final elementsAsync = ref.watch(
      bodyElementsProvider({
        'rlkId': widget.rlkId,
        'type': widget.inspectionType,
      }),
    );

    return Scaffold(
      appBar: AppBar(
        title: Text(_getTitle()),
      ),
      body: elementsAsync.when(
        data: (data) {
          final elements = data['elements'] as List<BodyElementModel>;
          final existingMarks =
              data['existingMarks'] as List<DamageMarkModel>;
          final baseImageUrl = data['baseImageUrl'] as String;

          return BodyInspectionWidget(
            rlkId: widget.rlkId,
            inspectionType: widget.inspectionType,
            elements: elements,
            existingMarks: existingMarks,
            baseImageUrl: baseImageUrl,
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline,
                size: 64,
                color: AppColors.danger,
              ),
              const SizedBox(height: 16),
              Text('Ошибка загрузки: $error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () {
                  ref.invalidate(bodyElementsProvider({
                    'rlkId': widget.rlkId,
                    'type': widget.inspectionType,
                  }));
                },
                child: const Text('Повторить'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

