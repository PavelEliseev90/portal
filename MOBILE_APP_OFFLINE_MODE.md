# Офлайн режим для мобильного приложения KorsGroup

## Обзор

Приложение должно работать полностью в офлайн режиме, позволяя проводить оценку автомобилей без подключения к интернету. Все данные сохраняются локально и синхронизируются при восстановлении связи.

---

## 1. АРХИТЕКТУРА ОФЛАЙН РЕЖИМА

### 1.1 Компоненты

```
┌─────────────────────────────────────────┐
│         UI Layer (Presentation)         │
│  - Проверка статуса подключения        │
│  - Индикаторы офлайн режима            │
│  - Обработка ошибок синхронизации      │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│      Sync Manager (Core/Sync)           │
│  - Управление синхронизацией           │
│  - Очередь задач                       │
│  - Автоматическая синхронизация        │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───▼──────────┐      ┌─────────▼────────┐
│  Local DB    │      │  Network API     │
│  (SQLite)    │      │  (Dio)           │
│              │      │                  │
│  - Catalogs  │      │  - POST/PUT      │
│  - Estimates │      │  - GET catalogs  │
│  - Queue     │      │  - Sync data     │
└──────────────┘      └──────────────────┘
```

---

## 2. ЛОКАЛЬНАЯ БАЗА ДАННЫХ

### 2.1 Структура БД

```dart
// lib/core/database/database_helper.dart
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();
  static Database? _database;

  DatabaseHelper._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB('kors_portal.db');
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDB,
    );
  }

  Future<void> _createDB(Database db, int version) async {
    // Справочники
    await db.execute('''
      CREATE TABLE manufacturers (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        updated_at INTEGER
      )
    ''');

    await db.execute('''
      CREATE TABLE models (
        id INTEGER PRIMARY KEY,
        manufacturer_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        updated_at INTEGER,
        FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id)
      )
    ''');

    await db.execute('''
      CREATE TABLE modifications (
        id INTEGER PRIMARY KEY,
        model_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        year INTEGER,
        updated_at INTEGER,
        FOREIGN KEY (model_id) REFERENCES models(id)
      )
    ''');

    await db.execute('''
      CREATE TABLE complectations (
        id INTEGER PRIMARY KEY,
        modification_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        updated_at INTEGER,
        FOREIGN KEY (modification_id) REFERENCES modifications(id)
      )
    ''');

    // Оценки (офлайн)
    await db.execute('''
      CREATE TABLE offline_estimations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rlk_id INTEGER NOT NULL,
        estimation_id INTEGER,
        step INTEGER NOT NULL,
        step_name TEXT NOT NULL,
        data TEXT NOT NULL,
        photos TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        created_at INTEGER NOT NULL,
        updated_at INTEGER NOT NULL,
        synced_at INTEGER
      )
    ''');

    // Очередь синхронизации
    await db.execute('''
      CREATE TABLE sync_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        estimation_id INTEGER NOT NULL,
        rlk_id INTEGER NOT NULL,
        endpoint TEXT NOT NULL,
        method TEXT NOT NULL,
        data TEXT NOT NULL,
        photos TEXT,
        retry_count INTEGER DEFAULT 0,
        max_retries INTEGER DEFAULT 5,
        status TEXT NOT NULL DEFAULT 'pending',
        error_message TEXT,
        created_at INTEGER NOT NULL,
        last_attempt_at INTEGER,
        completed_at INTEGER
      )
    ''');

    // Индексы
    await db.execute('CREATE INDEX idx_offline_estimations_rlk ON offline_estimations(rlk_id)');
    await db.execute('CREATE INDEX idx_offline_estimations_status ON offline_estimations(status)');
    await db.execute('CREATE INDEX idx_sync_queue_status ON sync_queue(status)');
    await db.execute('CREATE INDEX idx_sync_queue_rlk ON sync_queue(rlk_id)');
  }
}
```

---

## 3. СИНХРОНИЗАЦИЯ СПРАВОЧНИКОВ

### 3.1 Сервис синхронизации справочников

```dart
// lib/core/sync/catalog_sync_service.dart
import 'package:dio/dio.dart';
import '../database/database_helper.dart';
import '../network/api_client.dart';
import '../connectivity/connectivity_service.dart';

class CatalogSyncService {
  final ApiClient _apiClient = ApiClient();
  final DatabaseHelper _db = DatabaseHelper.instance;
  final ConnectivityService _connectivity = ConnectivityService();

  /// Синхронизация всех справочников
  Future<SyncResult> syncAllCatalogs({
    Function(int current, int total)? onProgress,
  }) async {
    if (!await _connectivity.isConnected()) {
      return SyncResult(
        success: false,
        error: 'Нет подключения к интернету',
      );
    }

    try {
      int total = 4;
      int current = 0;

      // 1. Производители
      onProgress?.call(++current, total);
      await _syncManufacturers();

      // 2. Модели
      onProgress?.call(++current, total);
      await _syncModels();

      // 3. Модификации
      onProgress?.call(++current, total);
      await _syncModifications();

      // 4. Комплектации
      onProgress?.call(++current, total);
      await _syncComplectations();

      return SyncResult(success: true);
    } catch (e) {
      return SyncResult(
        success: false,
        error: e.toString(),
      );
    }
  }

  Future<void> _syncManufacturers() async {
    final response = await _apiClient.get('catalogs/manufacturer/');
    final manufacturers = response.data['manufacturers'] as List;

    final db = await _db.database;
    final batch = db.batch();

    for (var manufacturer in manufacturers) {
      batch.insert(
        'manufacturers',
        {
          'id': manufacturer['id'],
          'name': manufacturer['name'],
          'updated_at': DateTime.now().millisecondsSinceEpoch,
        },
        conflictAlgorithm: ConflictAlgorithm.replace,
      );
    }

    await batch.commit(noResult: true);
  }

  Future<void> _syncModels() async {
    final db = await _db.database;
    final manufacturers = await db.query('manufacturers');

    for (var manufacturer in manufacturers) {
      try {
        final response = await _apiClient.get(
          'catalogs/models/${manufacturer['id']}/',
        );
        final models = response.data['models'] as List;

        final batch = db.batch();
        for (var model in models) {
          batch.insert(
            'models',
            {
              'id': model['id'],
              'manufacturer_id': manufacturer['id'],
              'name': model['name'],
              'updated_at': DateTime.now().millisecondsSinceEpoch,
            },
            conflictAlgorithm: ConflictAlgorithm.replace,
          );
        }
        await batch.commit(noResult: true);
      } catch (e) {
        // Продолжаем синхронизацию других производителей
        print('Error syncing models for manufacturer ${manufacturer['id']}: $e');
      }
    }
  }

  Future<void> _syncModifications() async {
    // Аналогично моделям
  }

  Future<void> _syncComplectations() async {
    // Аналогично моделям
  }

  /// Получение производителей из локальной БД
  Future<List<Map<String, dynamic>>> getManufacturers() async {
    final db = await _db.database;
    return await db.query('manufacturers', orderBy: 'name');
  }

  /// Получение моделей из локальной БД
  Future<List<Map<String, dynamic>>> getModels(int manufacturerId) async {
    final db = await _db.database;
    return await db.query(
      'models',
      where: 'manufacturer_id = ?',
      whereArgs: [manufacturerId],
      orderBy: 'name',
    );
  }

  /// Получение модификаций из локальной БД
  Future<List<Map<String, dynamic>>> getModifications(int modelId) async {
    final db = await _db.database;
    return await db.query(
      'modifications',
      where: 'model_id = ?',
      whereArgs: [modelId],
      orderBy: 'year DESC, name',
    );
  }

  /// Получение комплектаций из локальной БД
  Future<List<Map<String, dynamic>>> getComplectations(int modificationId) async {
    final db = await _db.database;
    return await db.query(
      'complectations',
      where: 'modification_id = ?',
      whereArgs: [modificationId],
      orderBy: 'name',
    );
  }
}

class SyncResult {
  final bool success;
  final String? error;

  SyncResult({required this.success, this.error});
}
```

---

## 4. СОХРАНЕНИЕ ОЦЕНКИ В ОФЛАЙН РЕЖИМЕ

### 4.1 DAO для оценок

```dart
// lib/core/database/dao/estimation_dao.dart
import '../database_helper.dart';
import 'dart:convert';

class EstimationDao {
  final DatabaseHelper _db = DatabaseHelper.instance;

  /// Сохранение этапа оценки локально
  Future<int> saveEstimationStep({
    required int rlkId,
    int? estimationId,
    required int step,
    required String stepName,
    required Map<String, dynamic> data,
    List<String>? photoPaths,
  }) async {
    final db = await _db.database;
    
    return await db.insert(
      'offline_estimations',
      {
        'rlk_id': rlkId,
        'estimation_id': estimationId,
        'step': step,
        'step_name': stepName,
        'data': jsonEncode(data),
        'photos': photoPaths != null ? jsonEncode(photoPaths) : null,
        'status': 'draft',
        'created_at': DateTime.now().millisecondsSinceEpoch,
        'updated_at': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  /// Получение всех несинхронизированных оценок
  Future<List<Map<String, dynamic>>> getPendingEstimations() async {
    final db = await _db.database;
    return await db.query(
      'offline_estimations',
      where: 'status != ?',
      whereArgs: ['synced'],
      orderBy: 'created_at DESC',
    );
  }

  /// Получение оценки по RLK ID
  Future<List<Map<String, dynamic>>> getEstimationsByRlk(int rlkId) async {
    final db = await _db.database;
    return await db.query(
      'offline_estimations',
      where: 'rlk_id = ?',
      whereArgs: [rlkId],
      orderBy: 'step',
    );
  }

  /// Обновление статуса оценки
  Future<void> updateEstimationStatus(int id, String status) async {
    final db = await _db.database;
    await db.update(
      'offline_estimations',
      {
        'status': status,
        'synced_at': status == 'synced' 
          ? DateTime.now().millisecondsSinceEpoch 
          : null,
        'updated_at': DateTime.now().millisecondsSinceEpoch,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }
}
```

---

## 5. ОЧЕРЕДЬ СИНХРОНИЗАЦИИ

### 5.1 DAO для очереди

```dart
// lib/core/database/dao/sync_queue_dao.dart
import '../database_helper.dart';
import 'dart:convert';

class SyncQueueDao {
  final DatabaseHelper _db = DatabaseHelper.instance;

  /// Добавление задачи в очередь
  Future<int> addToQueue({
    required int estimationId,
    required int rlkId,
    required String endpoint,
    required String method,
    required Map<String, dynamic> data,
    List<String>? photoPaths,
  }) async {
    final db = await _db.database;
    
    return await db.insert(
      'sync_queue',
      {
        'estimation_id': estimationId,
        'rlk_id': rlkId,
        'endpoint': endpoint,
        'method': method,
        'data': jsonEncode(data),
        'photos': photoPaths != null ? jsonEncode(photoPaths) : null,
        'status': 'pending',
        'retry_count': 0,
        'max_retries': 5,
        'created_at': DateTime.now().millisecondsSinceEpoch,
      },
    );
  }

  /// Получение следующей задачи из очереди
  Future<Map<String, dynamic>?> getNextPendingTask() async {
    final db = await _db.database;
    final results = await db.query(
      'sync_queue',
      where: 'status = ? AND retry_count < max_retries',
      whereArgs: ['pending'],
      orderBy: 'created_at ASC',
      limit: 1,
    );
    
    return results.isNotEmpty ? results.first : null;
  }

  /// Обновление статуса задачи
  Future<void> updateTaskStatus(
    int id,
    String status, {
    String? errorMessage,
  }) async {
    final db = await _db.database;
    await db.update(
      'sync_queue',
      {
        'status': status,
        'error_message': errorMessage,
        'last_attempt_at': DateTime.now().millisecondsSinceEpoch,
        'completed_at': status == 'completed' 
          ? DateTime.now().millisecondsSinceEpoch 
          : null,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  /// Увеличение счетчика повторов
  Future<void> incrementRetryCount(int id) async {
    final db = await _db.database;
    final task = await db.query(
      'sync_queue',
      where: 'id = ?',
      whereArgs: [id],
    );
    
    if (task.isNotEmpty) {
      await db.update(
        'sync_queue',
        {
          'retry_count': (task.first['retry_count'] as int) + 1,
          'last_attempt_at': DateTime.now().millisecondsSinceEpoch,
        },
        where: 'id = ?',
        whereArgs: [id],
      );
    }
  }

  /// Получение статистики очереди
  Future<Map<String, int>> getQueueStats() async {
    final db = await _db.database;
    
    final pending = await db.rawQuery(
      'SELECT COUNT(*) as count FROM sync_queue WHERE status = ?',
      ['pending'],
    );
    
    final failed = await db.rawQuery(
      'SELECT COUNT(*) as count FROM sync_queue WHERE status = ?',
      ['failed'],
    );
    
    return {
      'pending': pending.first['count'] as int,
      'failed': failed.first['count'] as int,
    };
  }
}
```

---

## 6. МЕНЕДЖЕР СИНХРОНИЗАЦИИ

### 6.1 Сервис синхронизации

```dart
// lib/core/sync/sync_manager.dart
import 'package:dio/dio.dart';
import '../database/dao/sync_queue_dao.dart';
import '../database/dao/estimation_dao.dart';
import '../network/api_client.dart';
import '../connectivity/connectivity_service.dart';
import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class SyncManager {
  final SyncQueueDao _queueDao = SyncQueueDao();
  final EstimationDao _estimationDao = EstimationDao();
  final ApiClient _apiClient = ApiClient();
  final ConnectivityService _connectivity = ConnectivityService();

  bool _isSyncing = false;

  /// Запуск синхронизации
  Future<SyncResult> startSync({
    Function(int current, int total)? onProgress,
  }) async {
    if (_isSyncing) {
      return SyncResult(success: false, error: 'Синхронизация уже выполняется');
    }

    if (!await _connectivity.isConnected()) {
      return SyncResult(success: false, error: 'Нет подключения к интернету');
    }

    _isSyncing = true;

    try {
      final stats = await _queueDao.getQueueStats();
      final total = stats['pending']! + stats['failed']!;
      int current = 0;

      while (true) {
        final task = await _queueDao.getNextPendingTask();
        if (task == null) break;

        onProgress?.call(++current, total);

        final result = await _processTask(task);
        
        if (!result.success) {
          await _queueDao.incrementRetryCount(task['id'] as int);
          if (task['retry_count'] as int >= task['max_retries'] as int) {
            await _queueDao.updateTaskStatus(
              task['id'] as int,
              'failed',
              errorMessage: result.error,
            );
          }
        } else {
          await _queueDao.updateTaskStatus(task['id'] as int, 'completed');
          await _estimationDao.updateEstimationStatus(
            task['estimation_id'] as int,
            'synced',
          );
        }
      }

      return SyncResult(success: true);
    } catch (e) {
      return SyncResult(success: false, error: e.toString());
    } finally {
      _isSyncing = false;
    }
  }

  Future<SyncResult> _processTask(Map<String, dynamic> task) async {
    try {
      final endpoint = task['endpoint'] as String;
      final method = task['method'] as String;
      final data = jsonDecode(task['data'] as String) as Map<String, dynamic>;
      final photoPaths = task['photos'] != null
        ? List<String>.from(jsonDecode(task['photos'] as String))
        : null;

      Response response;

      if (photoPaths != null && photoPaths.isNotEmpty) {
        // Загрузка с фотографиями
        final formData = await _createFormData(data, photoPaths);
        response = await _apiClient.post(endpoint, data: formData);
      } else {
        // Обычный запрос
        if (method == 'POST') {
          response = await _apiClient.post(endpoint, data: data);
        } else {
          response = await _apiClient.put(endpoint, data: data);
        }
      }

      if (response.statusCode == 200 || response.statusCode == 201) {
        return SyncResult(success: true);
      } else {
        return SyncResult(
          success: false,
          error: 'HTTP ${response.statusCode}',
        );
      }
    } catch (e) {
      return SyncResult(success: false, error: e.toString());
    }
  }

  Future<FormData> _createFormData(
    Map<String, dynamic> data,
    List<String> photoPaths,
  ) async {
    final formData = FormData();

    // Добавляем текстовые данные
    data.forEach((key, value) {
      formData.fields.add(MapEntry(key, value.toString()));
    });

    // Добавляем фотографии
    for (var photoPath in photoPaths) {
      final file = File(photoPath);
      if (await file.exists()) {
        formData.files.add(
          MapEntry(
            'file',
            await MultipartFile.fromFile(photoPath),
          ),
        );
      }
    }

    return formData;
  }

  /// Автоматическая синхронизация при восстановлении интернета
  void startAutoSync() {
    _connectivity.onConnectivityChanged.listen((isConnected) {
      if (isConnected && !_isSyncing) {
        startSync();
      }
    });
  }
}
```

---

## 7. UI ДЛЯ ОФЛАЙН РЕЖИМА

### 7.1 Индикатор офлайн режима

```dart
// lib/presentation/shared/widgets/offline_indicator.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/connectivity/connectivity_service.dart';
import '../../../core/constants/app_colors.dart';

class OfflineIndicator extends StatelessWidget {
  const OfflineIndicator({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Consumer<ConnectivityService>(
      builder: (context, connectivity, child) {
        if (connectivity.isConnected) {
          return const SizedBox.shrink();
        }

        return Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
          color: PortalColors.warning,
          child: Row(
            children: [
              const Icon(Icons.cloud_off, color: Colors.white),
              const SizedBox(width: 8),
              const Text(
                'Работа в офлайн режиме',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
```

### 7.2 Экран синхронизации справочников

```dart
// lib/presentation/settings/screens/sync_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../../core/sync/catalog_sync_service.dart';
import '../../../core/constants/app_colors.dart';

class SyncScreen extends StatefulWidget {
  const SyncScreen({Key? key}) : super(key: key);

  @override
  State<SyncScreen> createState() => _SyncScreenState();
}

class _SyncScreenState extends State<SyncScreen> {
  final CatalogSyncService _syncService = CatalogSyncService();
  bool _isSyncing = false;
  int _current = 0;
  int _total = 0;
  String? _error;

  Future<void> _syncCatalogs() async {
    setState(() {
      _isSyncing = true;
      _error = null;
    });

    final result = await _syncService.syncAllCatalogs(
      onProgress: (current, total) {
        setState(() {
          _current = current;
          _total = total;
        });
      },
    );

    setState(() {
      _isSyncing = false;
      if (!result.success) {
        _error = result.error;
      }
    });

    if (result.success && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Справочники успешно обновлены')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Синхронизация справочников'),
        backgroundColor: PortalColors.primary,
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Обновление справочников',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Загрузите актуальные данные о марках, моделях, модификациях и комплектациях автомобилей для работы в офлайн режиме.',
                    ),
                    const SizedBox(height: 16),
                    if (_isSyncing) ...[
                      LinearProgressIndicator(
                        value: _total > 0 ? _current / _total : null,
                      ),
                      const SizedBox(height: 8),
                      Text('Загрузка: $_current из $_total'),
                    ],
                    if (_error != null) ...[
                      const SizedBox(height: 8),
                      Text(
                        _error!,
                        style: const TextStyle(color: Colors.red),
                      ),
                    ],
                    const SizedBox(height: 16),
                    ElevatedButton(
                      onPressed: _isSyncing ? null : _syncCatalogs,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: PortalColors.primary,
                        minimumSize: const Size(double.infinity, 50),
                      ),
                      child: _isSyncing
                        ? const CircularProgressIndicator(color: Colors.white)
                        : const Text('Обновить справочники'),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

---

## 8. ИНТЕГРАЦИЯ В ПРИЛОЖЕНИЕ

### 8.1 Проверка подключения

```dart
// lib/core/connectivity/connectivity_service.dart
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

class ConnectivityService extends ChangeNotifier {
  final Connectivity _connectivity = Connectivity();
  bool _isConnected = true;

  bool get isConnected => _isConnected;

  ConnectivityService() {
    _init();
  }

  Future<void> _init() async {
    _checkConnectivity();
    _connectivity.onConnectivityChanged.listen((result) {
      _checkConnectivity();
    });
  }

  Future<void> _checkConnectivity() async {
    final result = await _connectivity.checkConnectivity();
    _isConnected = result != ConnectivityResult.none;
    notifyListeners();
  }

  Stream<bool> get onConnectivityChanged {
    return _connectivity.onConnectivityChanged.map((result) {
      _isConnected = result != ConnectivityResult.none;
      notifyListeners();
      return _isConnected;
    });
  }
}
```

### 8.2 Сохранение при работе в офлайн

```dart
// В каждом экране оценки
Future<void> _saveStep() async {
  final connectivity = Provider.of<ConnectivityService>(context);
  
  if (connectivity.isConnected) {
    // Сохраняем на сервер
    await _saveToServer();
  } else {
    // Сохраняем локально и добавляем в очередь
    await _saveLocally();
    await _addToSyncQueue();
  }
}
```

---

## 9. ФОНОВАЯ СИНХРОНИЗАЦИЯ

### 9.1 Настройка WorkManager

```dart
// lib/main.dart
import 'package:workmanager/workmanager.dart';

@pragma('vm:entry-point')
void callbackDispatcher() {
  Workmanager().executeTask((task, inputData) async {
    final syncManager = SyncManager();
    await syncManager.startSync();
    return Future.value(true);
  });
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Инициализация WorkManager
  await Workmanager().initialize(
    callbackDispatcher,
    isInDebugMode: false,
  );
  
  // Периодическая синхронизация каждые 15 минут
  await Workmanager().registerPeriodicTask(
    "sync-task",
    "syncEstimations",
    frequency: const Duration(minutes: 15),
    constraints: Constraints(
      networkType: NetworkType.connected,
    ),
  );
  
  runApp(MyApp());
}
```

---

Этот документ описывает полную реализацию офлайн режима для мобильного приложения.

