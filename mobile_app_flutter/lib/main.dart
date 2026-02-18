import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'presentation/theme/app_theme.dart';
import 'presentation/auth/screens/login_screen.dart';
import 'presentation/estimation/screens/rlk_list_screen.dart';
import 'presentation/estimation/screens/body_inspection_screen.dart';
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
        '/body-inspection': (context) {
          final args = ModalRoute.of(context)!.settings.arguments as Map;
          return BodyInspectionScreen(
            rlkId: args['rlkId'] as int,
            inspectionType: args['inspectionType'] as String,
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

