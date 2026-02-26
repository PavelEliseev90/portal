import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'presentation/theme/app_theme.dart';
import 'presentation/auth/screens/login_screen.dart';
import 'presentation/estimation/screens/rlk_list_screen.dart';
import 'presentation/estimation/screens/body_inspection_screen.dart';
import 'presentation/estimation/screens/documents_screen.dart';
import 'presentation/estimation/screens/complectnost_screen.dart';
import 'presentation/estimation/screens/kolesa_screen.dart';
import 'presentation/estimation/screens/test_drive_screen.dart';
import 'presentation/estimation/screens/proverki_screen.dart';
import 'presentation/estimation/screens/soglasovanie_screen.dart';
import 'presentation/estimation/screens/estimation_stages_screen.dart';
import 'presentation/estimation/screens/chat_screen.dart';
import 'data/repositories/auth_repository.dart';

void main() {
  runApp(
    const ProviderScope(
      child: MyApp(),
    ),
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'KorsGroup Mobile',
      theme: AppTheme.lightTheme,
      debugShowCheckedModeBanner: false,
      initialRoute: '/',
      routes: {
        '/': (context) => const LoginScreen(),
        '/rlk-list': (context) => const RlkListScreen(),
        '/estimation-stages': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return EstimationStagesScreen(
            rlkId: args['rlkId'] as int,
            chatId: args['chatId'] as String?,
          );
        },
        '/body-inspection': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return BodyInspectionScreen(
            rlkId: args['rlkId'] as int,
            inspectionType: args['inspectionType'] as String,
          );
        },
        '/documents': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return DocumentsScreen(rlkId: args['rlkId'] as int);
        },
        '/complectnost': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return ComplectnostScreen(rlkId: args['rlkId'] as int);
        },
        '/kolesa': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return KolesaScreen(rlkId: args['rlkId'] as int);
        },
        '/test-drive': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return TestDriveScreen(rlkId: args['rlkId'] as int);
        },
        '/proverki': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return ProverkiScreen(rlkId: args['rlkId'] as int);
        },
        '/soglasovanie': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return SoglasovanieScreen(
            rlkId: args['rlkId'] as int,
            chatId: args['chatId'] as String?,
          );
        },
        '/chat': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return ChatScreen(
            rlkId: args['rlkId'] as int,
            chatId: args['chatId'] as String,
          );
        },
      },
    );
  }
}

