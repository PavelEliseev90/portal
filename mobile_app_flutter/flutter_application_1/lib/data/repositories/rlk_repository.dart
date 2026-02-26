import '../../core/network/api_client.dart';
import '../../core/constants/app_constants.dart';
import '../models/rlk_model.dart';

class RlkRepository {
  final ApiClient _apiClient = ApiClient();

  Future<List<RlkModel>> getRlks({
    String type = '1',
    String? search,
  }) async {
    final queryParams = <String, dynamic>{
      'type': type,
    };
    if (search != null && search.isNotEmpty) {
      queryParams['search'] = search;
    }

    final response = await _apiClient.get(
      AppConstants.rlkEcoEndpoint,
      queryParameters: queryParams,
    );

    if (response.data['success'] == true) {
      final List<dynamic> rlksJson = response.data['rlks'] ?? [];
      return rlksJson.map((json) => RlkModel.fromJson(json)).toList();
    } else {
      throw Exception(response.data['error'] ?? 'Ошибка получения RLK');
    }
  }
}

