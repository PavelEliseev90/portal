import 'package:flutter/material.dart';
import 'dart:ui' as ui;
import '../../../data/models/damage_mark_model.dart';

class CanvasPainter extends CustomPainter {
  final ui.Image? backgroundImage;
  final List<DamageMarkModel> marks;
  final String baseImageUrl;

  CanvasPainter({
    this.backgroundImage,
    required this.marks,
    required this.baseImageUrl,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Отрисовка фонового изображения
    if (backgroundImage != null) {
      final imageWidth = backgroundImage!.width.toDouble();
      final imageHeight = backgroundImage!.height.toDouble();
      
      // Вычисляем масштаб для подгонки изображения под размер canvas
      final scaleX = size.width / imageWidth;
      final scaleY = size.height / imageHeight;
      final scale = scaleX < scaleY ? scaleX : scaleY;
      
      final scaledWidth = imageWidth * scale;
      final scaledHeight = imageHeight * scale;
      final offsetX = (size.width - scaledWidth) / 2;
      final offsetY = (size.height - scaledHeight) / 2;
      
      canvas.drawImageRect(
        backgroundImage!,
        Rect.fromLTWH(0, 0, imageWidth, imageHeight),
        Rect.fromLTWH(offsetX, offsetY, scaledWidth, scaledHeight),
        Paint(),
      );
    } else if (baseImageUrl.isNotEmpty) {
      // Если изображение еще не загружено, показываем индикатор загрузки
      final paint = Paint()..color = Colors.grey[300]!;
      canvas.drawRect(Rect.fromLTWH(0, 0, size.width, size.height), paint);
      
      final textPainter = TextPainter(
        text: const TextSpan(
          text: 'Загрузка изображения...',
          style: TextStyle(color: Colors.grey, fontSize: 16),
        ),
        textDirection: TextDirection.ltr,
      );
      textPainter.layout();
      textPainter.paint(
        canvas,
        Offset((size.width - textPainter.width) / 2, (size.height - textPainter.height) / 2),
      );
    }

    // Отрисовка отметок
    for (int i = 0; i < marks.length; i++) {
      final mark = marks[i];
      _drawMark(canvas, mark, i + 1);
    }
  }

  void _drawMark(Canvas canvas, DamageMarkModel mark, int number) {
    final paint = Paint()
      ..color = Colors.grey
      ..style = PaintingStyle.fill;

    // Отрисовка иконки типа повреждения (упрощенная версия - круг)
    canvas.drawCircle(
      Offset(mark.x.toDouble(), mark.y.toDouble()),
      16,
      paint,
    );

    // Отрисовка номера отметки
    final textPainter = TextPainter(
      text: TextSpan(
        text: number.toString(),
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.bold,
        ),
      ),
      textDirection: TextDirection.ltr,
    );
    textPainter.layout();
    textPainter.paint(
      canvas,
      Offset(mark.x.toDouble() - 6, mark.y.toDouble() - 6),
    );

    // Отрисовка значения толщиномера если есть
    if (mark.type == 'tol' && mark.text.isNotEmpty) {
      final valuePainter = TextPainter(
        text: TextSpan(
          text: mark.text,
          style: const TextStyle(
            color: Colors.black,
            fontSize: 12,
            fontWeight: FontWeight.bold,
          ),
        ),
        textDirection: TextDirection.ltr,
      );
      valuePainter.layout();
      valuePainter.paint(
        canvas,
        Offset(mark.x.toDouble() + 20, mark.y.toDouble()),
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

