import 'package:dio/dio.dart';

class NetworkException implements Exception {
  final String message;
  final int? statusCode;

  NetworkException(this.message, [this.statusCode]);

  factory NetworkException.fromDioError(DioException error) {
    switch (error.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return NetworkException('Превышено время ожидания', null);
      case DioExceptionType.badResponse:
        return NetworkException(
          error.response?.data['error'] ?? 'Ошибка сервера',
          error.response?.statusCode,
        );
      case DioExceptionType.cancel:
        return NetworkException('Запрос отменен', null);
      case DioExceptionType.unknown:
        return NetworkException('Нет подключения к интернету', null);
      default:
        return NetworkException('Неизвестная ошибка', null);
    }
  }

  @override
  String toString() => message;
}

