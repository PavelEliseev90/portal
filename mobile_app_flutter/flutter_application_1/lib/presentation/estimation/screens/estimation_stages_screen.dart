import 'package:flutter/material.dart';
import 'body_inspection_screen.dart';
import 'documents_screen.dart';
import 'complectnost_screen.dart';
import 'kolesa_screen.dart';
import 'test_drive_screen.dart';
import 'proverki_screen.dart';
import 'soglasovanie_screen.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

class EstimationStagesScreen extends StatelessWidget {
  final int rlkId;
  final String? chatId;

  const EstimationStagesScreen({
    super.key,
    required this.rlkId,
    this.chatId,
  });

  void _navigateToStage(BuildContext context, Widget screen) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => screen),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Оценка RLK $rlkId'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Этапы оценки',
            style: AppTextStyles.h2,
          ),
          const SizedBox(height: 24),
          
          // Документы
          _buildStageCard(
            context,
            title: 'Документы',
            icon: Icons.description,
            onTap: () => _navigateToStage(
              context,
              DocumentsScreen(rlkId: rlkId),
            ),
          ),
          
          // Осмотр кузова
          _buildStageCard(
            context,
            title: 'Осмотр кузова',
            icon: Icons.car_repair,
            subtitle: 'Перед, зад, стороны, крыша',
            onTap: () {
              // Показываем диалог выбора типа осмотра
              _showBodyInspectionDialog(context);
            },
          ),
          
          // Осмотр салона
          _buildStageCard(
            context,
            title: 'Осмотр салона',
            icon: Icons.chair,
            onTap: () {
              // TODO: Реализовать экран осмотра салона
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Осмотр салона в разработке')),
              );
            },
          ),
          
          // Комплектность
          _buildStageCard(
            context,
            title: 'Комплектность',
            icon: Icons.checklist,
            onTap: () => _navigateToStage(
              context,
              ComplectnostScreen(rlkId: rlkId),
            ),
          ),
          
          // Колеса
          _buildStageCard(
            context,
            title: 'Колеса',
            icon: Icons.settings,
            onTap: () => _navigateToStage(
              context,
              KolesaScreen(rlkId: rlkId),
            ),
          ),
          
          // Тест-драйв
          _buildStageCard(
            context,
            title: 'Тест-драйв',
            icon: Icons.directions_car,
            onTap: () => _navigateToStage(
              context,
              TestDriveScreen(rlkId: rlkId),
            ),
          ),
          
          // Проверки
          _buildStageCard(
            context,
            title: 'Проверки',
            icon: Icons.verified,
            onTap: () => _navigateToStage(
              context,
              ProverkiScreen(rlkId: rlkId),
            ),
          ),
          
          // Согласование
          _buildStageCard(
            context,
            title: 'Согласование',
            icon: Icons.handshake,
            subtitle: 'Согласование с клиентом',
            onTap: () => _navigateToStage(
              context,
              SoglasovanieScreen(rlkId: rlkId, chatId: chatId),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStageCard(
    BuildContext context, {
    required String title,
    required IconData icon,
    String? subtitle,
    required VoidCallback onTap,
  }) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppColors.primary,
          child: Icon(icon, color: Colors.white),
        ),
        title: Text(title, style: AppTextStyles.body),
        subtitle: subtitle != null ? Text(subtitle) : null,
        trailing: const Icon(Icons.arrow_forward_ios),
        onTap: onTap,
      ),
    );
  }

  void _showBodyInspectionDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Выберите тип осмотра'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.arrow_forward),
              title: const Text('Передняя часть'),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => BodyInspectionScreen(
                      rlkId: rlkId,
                      inspectionType: 'pered',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.arrow_back),
              title: const Text('Задняя часть'),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => BodyInspectionScreen(
                      rlkId: rlkId,
                      inspectionType: 'zad',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.arrow_left),
              title: const Text('Водительская сторона'),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => BodyInspectionScreen(
                      rlkId: rlkId,
                      inspectionType: 'vod',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.arrow_right),
              title: const Text('Пассажирская сторона'),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => BodyInspectionScreen(
                      rlkId: rlkId,
                      inspectionType: 'pass',
                    ),
                  ),
                );
              },
            ),
            ListTile(
              leading: const Icon(Icons.arrow_upward),
              title: const Text('Крыша'),
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => BodyInspectionScreen(
                      rlkId: rlkId,
                      inspectionType: 'up',
                    ),
                  ),
                );
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
        ],
      ),
    );
  }
}

