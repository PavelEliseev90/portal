import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/rendering.dart';
import 'dart:ui' as ui;
import 'dart:typed_data';
import 'package:image_picker/image_picker.dart';
import '../../../data/models/body_element_model.dart';
import '../../../data/models/damage_mark_model.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../../core/database/dao/inspection_dao.dart';
import '../../../core/utils/image_utils.dart';
import '../../../core/utils/image_loader.dart';
import 'damage_type_selector.dart';
import 'canvas_painter.dart';
import '../../theme/app_colors.dart';

class BodyInspectionWidget extends StatefulWidget {
  final int rlkId;
  final String inspectionType;
  final List<BodyElementModel> elements;
  final List<DamageMarkModel> existingMarks;
  final String baseImageUrl;

  const BodyInspectionWidget({
    Key? key,
    required this.rlkId,
    required this.inspectionType,
    required this.elements,
    required this.existingMarks,
    required this.baseImageUrl,
  }) : super(key: key);

  @override
  State<BodyInspectionWidget> createState() => _BodyInspectionWidgetState();
}

class _BodyInspectionWidgetState extends State<BodyInspectionWidget> {
  final GlobalKey _canvasKey = GlobalKey();
  final GlobalKey _repaintBoundaryKey = GlobalKey();
  final InspectionRepository _repository = InspectionRepository();
  final InspectionDao _dao = InspectionDao();
  
  List<DamageMarkModel> _marks = [];
  ui.Image? _backgroundImage;
  bool _isLoading = false;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _marks = List.from(widget.existingMarks);
    _loadBackgroundImage();
  }

  Future<void> _loadBackgroundImage() async {
    if (widget.baseImageUrl.isEmpty) return;
    
    try {
      setState(() {
        _isLoading = true;
      });
      
      final image = await ImageLoader.loadImageFromUrl(widget.baseImageUrl);
      
      if (mounted) {
        setState(() {
          _backgroundImage = image;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  void _handleTap(TapDownDetails details, Size canvasSize) {
    final RenderBox? renderBox =
        _canvasKey.currentContext?.findRenderObject() as RenderBox?;
    if (renderBox == null) return;

    final localPosition = renderBox.globalToLocal(details.globalPosition);
    
    // Определяем элемент по координатам
    final element = _findElementAtPoint(localPosition.dx, localPosition.dy);
    
    // Показываем диалог выбора типа повреждения
    _showDamageTypeDialog(element, localPosition, canvasSize);
  }

  BodyElementModel? _findElementAtPoint(double x, double y) {
    for (var element in widget.elements) {
      if (_isPointInPolygon(x, y, element.coorX, element.coorY)) {
        return element;
      }
    }
    return null;
  }

  bool _isPointInPolygon(double x, double y, List<int> coorX, List<int> coorY) {
    bool inside = false;
    for (int i = 0, j = coorX.length - 1; i < coorX.length; j = i++) {
      final xi = coorX[i].toDouble();
      final yi = coorY[i].toDouble();
      final xj = coorX[j].toDouble();
      final yj = coorY[j].toDouble();
      
      final intersect = (yi > y) != (yj > y) &&
          x < ((xj - xi) * (y - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  Future<void> _showDamageTypeDialog(
    BodyElementModel? element,
    Offset point,
    Size canvasSize,
  ) async {
    final damageType = await showModalBottomSheet<String>(
      context: context,
      builder: (context) => DamageTypeSelector(
        elementName: element?.bodyElemName ?? 'Неизвестный элемент',
        isSalon: false,
      ),
    );

    if (damageType != null) {
      await _addMark(damageType, point, element, canvasSize);
    }
  }

  Future<void> _addMark(
    String damageType,
    Offset point,
    BodyElementModel? element,
    Size canvasSize,
  ) async {
    String? text;
    
    // Если требуется значение (толщиномер)
    if (damageType == 'tol') {
      text = await _showThicknessInputDialog();
      if (text == null) return;
    }
    
    // Опционально: добавить фото
    XFile? photo;
    final addPhoto = await _showAddPhotoDialog();
    if (addPhoto == true) {
      final picker = ImagePicker();
      photo = await picker.pickImage(source: ImageSource.camera);
    }
    
    setState(() {
      _marks.add(DamageMarkModel(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        type: damageType,
        typeName: _getDamageTypeName(damageType),
        x: point.dx.toInt(),
        y: point.dy.toInt(),
        text: text ?? '',
        elementName: element?.bodyElemName,
        photoPath: photo?.path,
      ));
    });
  }

  String _getDamageTypeName(String type) {
    final names = {
      'tol': 'толщиномер',
      'tr': 'трещина',
      'skol': 'скол',
      'vmyat': 'вмятина',
      'vmyat_strong': 'вмятина сильная',
      'carap': 'царапина',
      'carap_strong': 'царапина сильная',
      'rzav': 'ржавчина',
      'rzav_strong': 'ржавчина сквозная',
      'perecras': 'перекрас',
      'perecras_strong': 'перекрас сильный',
      'stiker': 'наклейка',
      'toner': 'тонировка',
      'poly': 'полировка',
      'replace': 'заменен',
      'replace_add': 'заменить',
    };
    return names[type] ?? type;
  }

  Future<String?> _showThicknessInputDialog() async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Значение толщиномера'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            hintText: 'Введите значение',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () {
              if (controller.text.isNotEmpty) {
                Navigator.pop(context, controller.text);
              }
            },
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  Future<bool?> _showAddPhotoDialog() async {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Добавить фото?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Нет'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Да'),
          ),
        ],
      ),
    );
  }

  void _removeMark(DamageMarkModel mark) {
    setState(() {
      _marks.remove(mark);
    });
  }

  Future<void> _saveInspection() async {
    setState(() {
      _isSaving = true;
    });

    try {
      // Конвертируем canvas в base64
      final imageBytes = await _captureCanvas();
      final base64Image = ImageUtils.imageToBase64DataUrl(
        imageBytes,
        'image/png',
      );

      // Сохраняем отметки
      final marksJson = _marks.map((mark) {
        final json = mark.toJson();
        // TODO: Добавить base64 фото если есть
        return json;
      }).toList();

      // Пытаемся сохранить онлайн
      try {
        await _repository.saveBodyInspection(
          rlkId: widget.rlkId,
          inspectionType: widget.inspectionType,
          baseImageBase64: base64Image,
          marks: _marks,
        );
      } catch (e) {
        // Если нет интернета, сохраняем офлайн
        await _dao.saveBodyInspection(
          rlkId: widget.rlkId,
          inspectionType: widget.inspectionType,
          baseImage: base64Image,
          marks: marksJson,
        );
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Осмотр сохранен')),
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

  Future<Uint8List> _captureCanvas() async {
    try {
      final RenderRepaintBoundary? boundary = 
          _repaintBoundaryKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
      
      if (boundary == null) {
        throw Exception('RepaintBoundary not found');
      }

      final ui.Image image = await boundary.toImage(pixelRatio: 2.0);
      final ByteData? byteData = await image.toByteData(format: ui.ImageByteFormat.png);
      
      if (byteData == null) {
        throw Exception('Failed to convert image to bytes');
      }

      return byteData.buffer.asUint8List();
    } catch (e) {
      print('Error capturing canvas: $e');
      // Возвращаем пустой массив если не удалось захватить
      return Uint8List(0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Canvas с изображением
        Expanded(
          child: GestureDetector(
            onTapDown: (details) {
              final size = MediaQuery.of(context).size;
              _handleTap(details, size);
            },
            child: RepaintBoundary(
              key: _repaintBoundaryKey,
              child: CustomPaint(
                key: _canvasKey,
                painter: CanvasPainter(
                  backgroundImage: _backgroundImage,
                  marks: _marks,
                  baseImageUrl: widget.baseImageUrl,
                ),
                size: Size.infinite,
              ),
            ),
          ),
        ),
        
        // Список отметок
        Container(
          height: 200,
          padding: const EdgeInsets.all(8),
          child: ListView.builder(
            itemCount: _marks.length,
            itemBuilder: (context, index) {
              final mark = _marks[index];
              return ListTile(
                leading: CircleAvatar(
                  backgroundColor: AppColors.primary,
                  child: Text('${index + 1}'),
                ),
                title: Text('${mark.typeName} - ${mark.elementName ?? ""}'),
                subtitle: Text('X: ${mark.x}, Y: ${mark.y}'),
                trailing: IconButton(
                  icon: const Icon(Icons.delete),
                  onPressed: () => _removeMark(mark),
                ),
              );
            },
          ),
        ),
        
        // Кнопка сохранения
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: ElevatedButton(
            onPressed: _isSaving ? null : _saveInspection,
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
        ),
      ],
    );
  }
}

