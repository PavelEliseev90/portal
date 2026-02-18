import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../../core/network/api_client.dart';
import '../../core/constants/app_constants.dart';
import '../models/user_model.dart';

class AuthRepository {
  final ApiClient _apiClient = ApiClient();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<UserModel> login(String username, String password) async {
    // Создаем Basic Auth токен
    final credentials = base64Encode(utf8.encode('$username:$password'));
    await _storage.write(key: AppConstants.authTokenKey, value: credentials);

    final response = await _apiClient.post(
      AppConstants.loginEndpoint,
      data: {
        'username': username,
        'password': password,
      },
    );

    if (response.data['success'] == true) {
      final user = UserModel.fromJson(response.data['user']);
      await _storage.write(
        key: AppConstants.userDataKey,
        value: jsonEncode(user.toJson()),
      );
      return user;
    } else {
      throw Exception(response.data['error'] ?? 'Ошибка авторизации');
    }
  }

  Future<UserModel?> getCurrentUser() async {
    try {
      final userData = await _storage.read(key: AppConstants.userDataKey);
      if (userData != null) {
        return UserModel.fromJson(jsonDecode(userData));
      }
      return null;
    } catch (e) {
      return null;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: AppConstants.authTokenKey);
    await _storage.delete(key: AppConstants.userDataKey);
  }

  Future<bool> isAuthenticated() async {
    final token = await _storage.read(key: AppConstants.authTokenKey);
    return token != null;
  }
}

