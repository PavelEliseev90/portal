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
    // TODO: Загрузить и отрисовать фоновое изображение
    // if (backgroundImage != null) {
    //   canvas.drawImageRect(
    //     backgroundImage!,
    //     Rect.fromLTWH(0, 0, backgroundImage!.width.toDouble(), backgroundImage!.height.toDouble()),
    //     Rect.fromLTWH(0, 0, size.width, size.height),
    //     Paint(),
    //   );
    // }

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

