import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/network/websocket_service.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../auth/screens/login_screen.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

final websocketProvider = Provider.family<WebSocketService, String>((ref, roomName) {
  final service = WebSocketService();
  service.connect(roomName);
  ref.onDispose(() {
    service.disconnect();
  });
  return service;
});

class ChatScreen extends ConsumerStatefulWidget {
  final int rlkId;
  final String chatId;

  const ChatScreen({
    Key? key,
    required this.rlkId,
    required this.chatId,
  }) : super(key: key);

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final List<ChatMessage> _messages = [];
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _initWebSocket();
  }

  void _initWebSocket() {
    final roomName = 'rlk_${widget.rlkId}';
    final wsService = ref.read(websocketProvider(roomName));
    
    wsService.messageStream.listen((data) {
      setState(() {
        _messages.add(ChatMessage.fromJson(data));
      });
      _scrollToBottom();
    });
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _sendMessage() async {
    if (_messageController.text.isEmpty) return;

    final user = await ref.read(authRepositoryProvider).getCurrentUser();
    if (user == null) return;

    final roomName = 'rlk_${widget.rlkId}';
    final wsService = ref.read(websocketProvider(roomName));

    try {
      wsService.sendMessage(
        chatId: widget.chatId,
        name: user.username,
        chat: roomName,
        message: _messageController.text,
        username: user.username,
        lastName: user.lastName,
        firstName: user.firstName,
        psevdoName: user.ecoName,
        eco: user.eco,
      );

      _messageController.clear();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка отправки: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final roomName = 'rlk_${widget.rlkId}';
    final wsService = ref.watch(websocketProvider(roomName));

    return Scaffold(
      appBar: AppBar(
        title: Text('Чат - RLK ${widget.rlkId}'),
        actions: [
          Icon(
            wsService.isConnected ? Icons.wifi : Icons.wifi_off,
            color: wsService.isConnected ? Colors.green : Colors.red,
          ),
          const SizedBox(width: 16),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                return ChatBubble(message: message);
              },
            ),
          ),
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.grey.withOpacity(0.2),
                  spreadRadius: 1,
                  blurRadius: 5,
                ),
              ],
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Введите сообщение...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                    ),
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: _sendMessage,
                  color: AppColors.primary,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }
}

class ChatMessage {
  final String message;
  final String username;
  final String firstName;
  final String lastName;
  final String psevdoName;
  final bool eco;
  final DateTime timestamp;

  ChatMessage({
    required this.message,
    required this.username,
    required this.firstName,
    required this.lastName,
    required this.psevdoName,
    required this.eco,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      message: json['message'] ?? '',
      username: json['username'] ?? '',
      firstName: json['first_name'] ?? '',
      lastName: json['last_name'] ?? '',
      psevdoName: json['psevdo_name'] ?? '',
      eco: json['eco'] ?? false,
    );
  }
}

class ChatBubble extends StatelessWidget {
  final ChatMessage message;

  const ChatBubble({super.key, required this.message});

  @override
  Widget build(BuildContext context) {
    final isMe = true; // TODO: Определить по текущему пользователю

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment:
            isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
        children: [
          if (!isMe) ...[
            CircleAvatar(
              radius: 16,
              child: Text(message.firstName[0].toUpperCase()),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: isMe ? AppColors.primary : Colors.grey[200],
                borderRadius: BorderRadius.circular(20),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (!isMe)
                    Text(
                      message.psevdoName.isNotEmpty
                          ? message.psevdoName
                          : '${message.firstName} ${message.lastName}',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                        color: isMe ? Colors.white70 : Colors.black87,
                      ),
                    ),
                  Text(
                    message.message,
                    style: TextStyle(
                      color: isMe ? Colors.white : Colors.black87,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${message.timestamp.hour}:${message.timestamp.minute.toString().padLeft(2, '0')}',
                    style: TextStyle(
                      fontSize: 10,
                      color: isMe ? Colors.white70 : Colors.black54,
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (isMe) ...[
            const SizedBox(width: 8),
            CircleAvatar(
              radius: 16,
              child: Text(message.firstName[0].toUpperCase()),
            ),
          ],
        ],
      ),
    );
  }
}

