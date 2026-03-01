import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../constants/app_constants.dart';

class DatabaseHelper {
  static final DatabaseHelper instance = DatabaseHelper._init();
  static Database? _database;

  DatabaseHelper._init();

  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB(AppConstants.databaseName);
    return _database!;
  }

  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, filePath);

    return await openDatabase(
      path,
      version: AppConstants.databaseVersion,
      onCreate: _createDB,
    );
  }

  Future<void> _createDB(Database db, int version) async {
    // Таблица для офлайн RLK
    await db.execute('''
      CREATE TABLE offline_rlks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rlk_id INTEGER UNIQUE,
        data TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        synced_at INTEGER
      )
    ''');

    // Таблица для офлайн осмотров кузова
    await db.execute('''
      CREATE TABLE offline_body_inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rlk_id INTEGER NOT NULL,
        inspection_type TEXT NOT NULL,
        base_image TEXT,
        marks TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        synced_at INTEGER
      )
    ''');

    // Таблица для офлайн осмотров салона
    await db.execute('''
      CREATE TABLE offline_salon_inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rlk_id INTEGER NOT NULL,
        base_image TEXT,
        marks TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at INTEGER NOT NULL,
        synced_at INTEGER
      )
    ''');

    // Таблица для справочников
    await db.execute('''
      CREATE TABLE catalogs_marks (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT,
        synced_at INTEGER NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE catalogs_models (
        id INTEGER PRIMARY KEY,
        mark_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        synced_at INTEGER NOT NULL
      )
    ''');

    await db.execute('''
      CREATE TABLE catalogs_modifications (
        id INTEGER PRIMARY KEY,
        model_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        year_from TEXT,
        year_to TEXT,
        synced_at INTEGER NOT NULL
      )
    ''');

    // Индексы
    await db.execute('CREATE INDEX idx_offline_rlks_status ON offline_rlks(status)');
    await db.execute('CREATE INDEX idx_offline_body_status ON offline_body_inspections(status)');
    await db.execute('CREATE INDEX idx_offline_salon_status ON offline_salon_inspections(status)');
  }

  Future<void> close() async {
    final db = await instance.database;
    await db.close();
  }
}

