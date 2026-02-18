# Примеры кода для мобильного приложения KorsGroup

## 1. Настройка API клиента

```dart
// lib/core/network/api_client.dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  static const String baseUrl = 'https://ah.kors-group.com/api/a/v1/';
  late Dio _dio;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  ApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        // Добавляем Basic Auth
        final credentials = await _getCredentials();
        if (credentials != null) {
          options.headers['Authorization'] = 'Basic $credentials';
        }
        return handler.next(options);
      },
      onError: (error, handler) {
        // Обработка ошибок
        return handler.next(error);
      },
    ));
  }

  Future<String?> _getCredentials() async {
    final username = await _storage.read(key: 'username');
    final password = await _storage.read(key: 'password');
    if (username != null && password != null) {
      final credentials = base64Encode(utf8.encode('$username:$password'));
      return credentials;
    }
    return null;
  }

  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) {
    return _dio.get(path, queryParameters: queryParameters);
  }

  Future<Response> post(String path, {dynamic data}) {
    return _dio.post(path, data: data);
  }
}
```

---

## 2. Модель данных

```dart
// lib/data/models/rlk_model.dart
class RlkModel {
  final int slug;
  final int? estimation;
  final String? estimationVin;
  final String? estimationModificationName;
  final String? estimationModelName;
  final String? estimationMarkName;
  final int? estimationYear;
  final String? unitName;
  final String? estimationStartFormated;
  final String? date;
  final String? staffName;
  final String? customerName;
  final int? priceReception;
  final String? number;

  RlkModel({
    required this.slug,
    this.estimation,
    this.estimationVin,
    this.estimationModificationName,
    this.estimationModelName,
    this.estimationMarkName,
    this.estimationYear,
    this.unitName,
    this.estimationStartFormated,
    this.date,
    this.staffName,
    this.customerName,
    this.priceReception,
    this.number,
  });

  factory RlkModel.fromJson(Map<String, dynamic> json) {
    return RlkModel(
      slug: json['slug'] as int,
      estimation: json['estimation'] as int?,
      estimationVin: json['estimation_vin'] as String?,
      estimationModificationName: json['estimation_modification_name'] as String?,
      estimationModelName: json['estimation_model_name'] as String?,
      estimationMarkName: json['estimation_mark_name'] as String?,
      estimationYear: json['estimation_year'] as int?,
      unitName: json['unit_name'] as String?,
      estimationStartFormated: json['estimation_start_formated'] as String?,
      date: json['date'] as String?,
      staffName: json['staff_name'] as String?,
      customerName: json['customer_name'] as String?,
      priceReception: json['price_reception'] as int?,
      number: json['number'] as String?,
    );
  }
}
```

---

## 3. Репозиторий

```dart
// lib/data/repositories/rlk_repository.dart
import 'package:dio/dio.dart';
import '../models/rlk_model.dart';
import '../../core/network/api_client.dart';

class RlkRepository {
  final ApiClient _apiClient = ApiClient();

  Future<List<RlkModel>> getRlkEco({int? type}) async {
    try {
      final response = await _apiClient.get(
        'rlk_eco/',
        queryParameters: type != null ? {'type': type} : null,
      );

      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final objects = data['objects'] as List;
        return objects.map((json) => RlkModel.fromJson(json)).toList();
      } else {
        throw Exception('Failed to load RLK list');
      }
    } catch (e) {
      throw Exception('Error: $e');
    }
  }

  Future<RlkModel> getRlkDetail(int rlkId) async {
    try {
      final response = await _apiClient.get('staff_rlk/$rlkId/');
      
      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        final object = data['object'] as Map<String, dynamic>;
        return RlkModel.fromJson(object);
      } else {
        throw Exception('Failed to load RLK detail');
      }
    } catch (e) {
      throw Exception('Error: $e');
    }
  }
}
```

---

## 4. Экран авторизации

```dart
// lib/presentation/auth/screens/login_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../../../core/constants/app_colors.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({Key? key}) : super(key: key);

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PortalColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Логотип
                  Icon(
                    Icons.car_repair,
                    size: 80,
                    color: PortalColors.primary,
                  ),
                  const SizedBox(height: 32),
                  
                  // Заголовок
                  Text(
                    'KorsGroup Portal',
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: PortalColors.primary,
                    ),
                  ),
                  const SizedBox(height: 48),
                  
                  // Поле логина
                  TextFormField(
                    controller: _usernameController,
                    decoration: InputDecoration(
                      labelText: 'Логин',
                      prefixIcon: const Icon(Icons.person),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Введите логин';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  
                  // Поле пароля
                  TextFormField(
                    controller: _passwordController,
                    obscureText: _obscurePassword,
                    decoration: InputDecoration(
                      labelText: 'Пароль',
                      prefixIcon: const Icon(Icons.lock),
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword ? Icons.visibility : Icons.visibility_off,
                        ),
                        onPressed: () {
                          setState(() {
                            _obscurePassword = !_obscurePassword;
                          });
                        },
                      ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Введите пароль';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 32),
                  
                  // Кнопка входа
                  Consumer<AuthProvider>(
                    builder: (context, authProvider, child) {
                      return SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          onPressed: authProvider.isLoading
                              ? null
                              : () => _handleLogin(authProvider),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: PortalColors.primary,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                          child: authProvider.isLoading
                              ? const CircularProgressIndicator(color: Colors.white)
                              : const Text(
                                  'Войти',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                        ),
                      );
                    },
                  ),
                  
                  // Ошибка
                  Consumer<AuthProvider>(
                    builder: (context, authProvider, child) {
                      if (authProvider.error != null) {
                        return Padding(
                          padding: const EdgeInsets.only(top: 16),
                          child: Text(
                            authProvider.error!,
                            style: const TextStyle(color: Colors.red),
                          ),
                        );
                      }
                      return const SizedBox.shrink();
                    },
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _handleLogin(AuthProvider authProvider) async {
    if (_formKey.currentState!.validate()) {
      final success = await authProvider.login(
        _usernameController.text,
        _passwordController.text,
      );
      
      if (success && mounted) {
        Navigator.of(context).pushReplacementNamed('/home');
      }
    }
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }
}
```

---

## 5. Экран списка RLK

```dart
// lib/presentation/estimation/screens/rlk_list_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/rlk_list_provider.dart';
import '../widgets/rlk_card.dart';
import '../widgets/search_bar.dart';
import '../../../core/constants/app_colors.dart';

class RlkListScreen extends StatefulWidget {
  const RlkListScreen({Key? key}) : super(key: key);

  @override
  State<RlkListScreen> createState() => _RlkListScreenState();
}

class _RlkListScreenState extends State<RlkListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<RlkListProvider>().loadRlkList();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: PortalColors.background,
      appBar: AppBar(
        title: const Text('Рабочие листы'),
        backgroundColor: PortalColors.primary,
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: () => _showFilterDialog(context),
          ),
        ],
      ),
      body: Column(
        children: [
          // Поиск
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: SearchBar(
              onSearch: (query) {
                context.read<RlkListProvider>().search(query);
              },
            ),
          ),
          
          // Список
          Expanded(
            child: Consumer<RlkListProvider>(
              builder: (context, provider, child) {
                if (provider.isLoading) {
                  return const Center(child: CircularProgressIndicator());
                }
                
                if (provider.error != null) {
                  return Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(provider.error!),
                        ElevatedButton(
                          onPressed: () => provider.loadRlkList(),
                          child: const Text('Повторить'),
                        ),
                      ],
                    ),
                  );
                }
                
                if (provider.rlkList.isEmpty) {
                  return const Center(
                    child: Text('Нет рабочих листов'),
                  );
                }
                
                return RefreshIndicator(
                  onRefresh: () => provider.loadRlkList(),
                  child: ListView.builder(
                    itemCount: provider.rlkList.length,
                    itemBuilder: (context, index) {
                      final rlk = provider.rlkList[index];
                      return RlkCard(
                        rlk: rlk,
                        onTap: () {
                          Navigator.pushNamed(
                            context,
                            '/estimation/start',
                            arguments: rlk.slug,
                          );
                        },
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showFilterDialog(BuildContext context) {
    // Реализация диалога фильтров
  }
}
```

---

## 6. Виджет карточки RLK

```dart
// lib/presentation/estimation/widgets/rlk_card.dart
import 'package:flutter/material.dart';
import '../../../data/models/rlk_model.dart';
import '../../../core/constants/app_colors.dart';

class RlkCard extends StatelessWidget {
  final RlkModel rlk;
  final VoidCallback onTap;

  const RlkCard({
    Key? key,
    required this.rlk,
    required this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
      ),
      elevation: 2,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Номер RLK и дата
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    rlk.number ?? 'RLK-${rlk.slug}',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: PortalColors.primary,
                    ),
                  ),
                  if (rlk.date != null)
                    Text(
                      rlk.date!,
                      style: TextStyle(
                        fontSize: 12,
                        color: PortalColors.secondary,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              
              // Клиент
              if (rlk.customerName != null)
                Text(
                  'Клиент: ${rlk.customerName}',
                  style: const TextStyle(fontSize: 14),
                ),
              
              // Автомобиль
              if (rlk.estimationMarkName != null)
                Text(
                  '${rlk.estimationMarkName} ${rlk.estimationModelName ?? ''} ${rlk.estimationYear ?? ''}',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              
              // VIN
              if (rlk.estimationVin != null)
                Text(
                  'VIN: ${rlk.estimationVin}',
                  style: TextStyle(
                    fontSize: 12,
                    color: PortalColors.secondary,
                  ),
                ),
              
              const SizedBox(height: 8),
              
              // Подразделение
              if (rlk.unitName != null)
                Row(
                  children: [
                    const Icon(Icons.location_on, size: 16),
                    const SizedBox(width: 4),
                    Text(
                      rlk.unitName!,
                      style: TextStyle(
                        fontSize: 12,
                        color: PortalColors.secondary,
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ),
    );
  }
}
```

---

## 7. Provider для авторизации

```dart
// lib/presentation/auth/providers/auth_provider.dart
import 'package:flutter/foundation.dart';
import '../../../data/repositories/auth_repository.dart';
import '../../../core/storage/secure_storage.dart';

class AuthProvider extends ChangeNotifier {
  final AuthRepository _authRepository = AuthRepository();
  final SecureStorage _storage = SecureStorage();
  
  bool _isLoading = false;
  String? _error;
  bool _isAuthenticated = false;

  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _isAuthenticated;

  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final user = await _authRepository.login(username, password);
      
      if (user != null) {
        await _storage.saveCredentials(username, password);
        await _storage.saveUser(user);
        _isAuthenticated = true;
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _error = 'Ошибка авторизации';
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _storage.clear();
    _isAuthenticated = false;
    notifyListeners();
  }

  Future<void> checkAuth() async {
    final credentials = await _storage.getCredentials();
    if (credentials != null) {
      _isAuthenticated = true;
      notifyListeners();
    }
  }
}
```

---

Эти примеры кода можно использовать как основу для разработки мобильного приложения.

