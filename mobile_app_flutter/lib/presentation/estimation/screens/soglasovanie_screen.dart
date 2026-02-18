import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../data/repositories/inspection_repository.dart';
import '../../../core/network/websocket_service.dart';
import '../../auth/screens/login_screen.dart';
import '../screens/chat_screen.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

final soglasovanieRepositoryProvider = Provider((ref) => InspectionRepository());

class SoglasovanieScreen extends ConsumerStatefulWidget {
  final int rlkId;
  final String? chatId;

  const SoglasovanieScreen({
    Key? key,
    required this.rlkId,
    this.chatId,
  }) : super(key: key);

  @override
  ConsumerState<SoglasovanieScreen> createState() => _SoglasovanieScreenState();
}

class _SoglasovanieScreenState extends ConsumerState<SoglasovanieScreen> {
  bool _isSaving = false;
  bool _isAgreed = false;
  String _comment = '';

  Future<void> _saveSoglasovanie() async {
    setState(() {
      _isSaving = true;
    });

    try {
      final repository = ref.read(soglasovanieRepositoryProvider);
      // TODO: Реализовать сохранение через API
      // await repository.saveSoglasovanie(...);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Согласование сохранено')),
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

  void _openChat() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ChatScreen(
          rlkId: widget.rlkId,
          chatId: widget.chatId ?? 'rlk_${widget.rlkId}',
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Согласование'),
        actions: [
          IconButton(
            icon: const Icon(Icons.chat),
            onPressed: _openChat,
            tooltip: 'Открыть чат',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Согласование оценки',
            style: AppTextStyles.h3,
          ),
          const SizedBox(height: 16),
          
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Статус согласования',
                    style: AppTextStyles.body.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  SwitchListTile(
                    title: const Text('Согласовано'),
                    value: _isAgreed,
                    onChanged: (value) {
                      setState(() {
                        _isAgreed = value;
                      });
                    },
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Комментарий',
                    style: AppTextStyles.body.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    decoration: const InputDecoration(
                      hintText: 'Введите комментарий к согласованию',
                    ),
                    onChanged: (value) {
                      setState(() {
                        _comment = value;
                      });
                    },
                    controller: TextEditingController(text: _comment),
                    maxLines: 5,
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.chat_bubble_outline),
              title: const Text('Чат для согласования'),
              subtitle: const Text('Обсудите детали оценки с клиентом'),
              trailing: const Icon(Icons.arrow_forward_ios),
              onTap: _openChat,
            ),
          ),

          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _isSaving ? null : _saveSoglasovanie,
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
        ],
      ),
    );
  }
}

