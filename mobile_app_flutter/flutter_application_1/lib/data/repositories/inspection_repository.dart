import 'dart:convert';
import 'dart:typed_data';
import 'package:image/image.dart' as img;
import '../../core/network/api_client.dart';
import '../../core/constants/app_constants.dart';
import '../models/body_element_model.dart';
import '../models/damage_mark_model.dart';

class InspectionRepository {
  final ApiClient _apiClient = ApiClient();

  Future<Map<String, dynamic>> getBodyElements(
    int rlkId,
    String inspectionType,
  ) async {
    final response = await _apiClient.get(
      '${AppConstants.bodyElementsEndpoint}/$rlkId/$inspectionType/',
    );

    if (response.data['success'] == true) {
      return {
        'elements': (response.data['elements'] as List)
            .map((e) => BodyElementModel.fromJson(e))
            .toList(),
        'existingMarks': (response.data['existing_marks'] as List)
            .map((e) => DamageMarkModel.fromJson(e))
            .toList(),
        'baseImageUrl': response.data['base_image_url'] ?? '',
      };
    } else {
      throw Exception(response.data['error'] ?? 'Ошибка получения элементов');
    }
  }

  Future<void> saveBodyInspection({
    required int rlkId,
    required String inspectionType,
    required String baseImageBase64,
    required List<DamageMarkModel> marks,
  }) async {
    final marksJson = marks.map((mark) {
      final json = mark.toJson();
      // Добавляем base64 фото если есть
      if (mark.photoPath != null) {
        // Здесь нужно конвертировать фото в base64
        // json['photo'] = base64Photo;
      }
      return json;
    }).toList();

    final response = await _apiClient.post(
      '${AppConstants.bodyInspectionPostEndpoint}/$rlkId/',
      data: {
        'inspection_type': inspectionType,
        'base_image': baseImageBase64,
        'marks': marksJson,
      },
    );

    if (response.data['success'] != true) {
      throw Exception(response.data['error'] ?? 'Ошибка сохранения осмотра');
    }
  }

  Future<Map<String, dynamic>> getSalonElements(int rlkId) async {
    final response = await _apiClient.get(
      '${AppConstants.salonElementsEndpoint}/$rlkId/',
    );

    if (response.data['success'] == true) {
      return {
        'elements': (response.data['elements'] as List)
            .map((e) => BodyElementModel.fromJson(e))
            .toList(),
        'existingMarks': (response.data['existing_marks'] as List)
            .map((e) => DamageMarkModel.fromJson(e))
            .toList(),
        'baseImageUrl': response.data['base_image_url'] ?? '',
      };
    } else {
      throw Exception(response.data['error'] ?? 'Ошибка получения элементов');
    }
  }

  Future<void> saveSalonInspection({
    required int rlkId,
    required String baseImageBase64,
    required List<DamageMarkModel> marks,
  }) async {
    final marksJson = marks.map((mark) => mark.toJson()).toList();

    final response = await _apiClient.post(
      '${AppConstants.salonInspectionPostEndpoint}/$rlkId/',
      data: {
        'base_image': baseImageBase64,
        'marks': marksJson,
      },
    );

    if (response.data['success'] != true) {
      throw Exception(response.data['error'] ?? 'Ошибка сохранения осмотра');
    }
  }

  String imageToBase64(Uint8List imageBytes) {
    return base64Encode(imageBytes);
  }

  String imageToBase64DataUrl(Uint8List imageBytes, String mimeType) {
    final base64 = imageToBase64(imageBytes);
    return 'data:$mimeType;base64,$base64';
  }
}

