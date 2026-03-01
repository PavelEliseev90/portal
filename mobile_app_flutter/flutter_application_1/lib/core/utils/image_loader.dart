import 'dart:ui' as ui;
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:cached_network_image/cached_network_image.dart';

class ImageLoader {
  /// Загружает изображение из URL и конвертирует в ui.Image
  static Future<ui.Image?> loadImageFromUrl(String url) async {
    try {
      final response = await http.get(Uri.parse(url));
      if (response.statusCode == 200) {
        final Uint8List bytes = response.bodyBytes;
        final codec = await ui.instantiateImageCodec(bytes);
        final frame = await codec.getNextFrame();
        return frame.image;
      }
    } catch (e) {
      print('Error loading image from URL: $e');
    }
    return null;
  }

  /// Загружает изображение из файла
  static Future<ui.Image?> loadImageFromFile(String path) async {
    try {
      final Uint8List bytes = await rootBundle.load(path);
      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      return frame.image;
    } catch (e) {
      print('Error loading image from file: $e');
    }
    return null;
  }

  /// Загружает изображение из bytes
  static Future<ui.Image?> loadImageFromBytes(Uint8List bytes) async {
    try {
      final codec = await ui.instantiateImageCodec(bytes);
      final frame = await codec.getNextFrame();
      return frame.image;
    } catch (e) {
      print('Error loading image from bytes: $e');
    }
    return null;
  }
}

