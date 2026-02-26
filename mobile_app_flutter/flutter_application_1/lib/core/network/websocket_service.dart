import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../constants/app_constants.dart';

class WebSocketService {
  WebSocketChannel? _channel;
  final String baseUrl = AppConstants.wsBaseUrl;
  StreamController<Map<String, dynamic>>? _messageController;
  Stream<Map<String, dynamic>>? _messageStream;
  bool _isConnected = false;

  Stream<Map<String, dynamic>> get messageStream {
    _messageController ??= StreamController<Map<String, dynamic>>.broadcast();
    _messageStream ??= _messageController!.stream;
    return _messageStream!;
  }

  bool get isConnected => _isConnected;

  Future<void> connect(String roomName) async {
    try {
      final url = '$baseUrl/$roomName/';
      _channel = WebSocketChannel.connect(Uri.parse(url));

      _channel!.stream.listen(
        (message) {
          try {
            final data = jsonDecode(message) as Map<String, dynamic>;
            _messageController?.add(data);
          } catch (e) {
            print('Error parsing WebSocket message: $e');
          }
        },
        onError: (error) {
          print('WebSocket error: $error');
          _isConnected = false;
          _messageController?.addError(error);
        },
        onDone: () {
          print('WebSocket closed');
          _isConnected = false;
        },
        cancelOnError: false,
      );

      _isConnected = true;
    } catch (e) {
      print('Error connecting to WebSocket: $e');
      _isConnected = false;
      rethrow;
    }
  }

  void sendMessage({
    required String chatId,
    required String name,
    required String chat,
    required String message,
    required String username,
    required String lastName,
    required String firstName,
    required String psevdoName,
    required bool eco,
  }) {
    if (!_isConnected || _channel == null) {
      throw Exception('WebSocket not connected');
    }

    final messageData = {
      'chat_id': chatId,
      'name': name,
      'chat': chat,
      'message': message,
      'username': username,
      'last_name': lastName,
      'first_name': firstName,
      'psevdo_name': psevdoName,
      'eco': eco,
    };

    _channel!.sink.add(jsonEncode(messageData));
  }

  Future<void> disconnect() async {
    await _channel?.sink.close();
    _isConnected = false;
    await _messageController?.close();
    _messageController = null;
    _messageStream = null;
  }

  Future<void> reconnect(String roomName) async {
    await disconnect();
    await connect(roomName);
  }
}

