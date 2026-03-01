import 'package:sqflite/sqflite.dart';
import '../database_helper.dart';
import 'dart:convert';

class InspectionDao {
  final DatabaseHelper _db = DatabaseHelper.instance;

  Future<int> saveBodyInspection({
    required int rlkId,
    required String inspectionType,
    required String? baseImage,
    required List<Map<String, dynamic>> marks,
  }) async {
    final db = await _db.database;

    return await db.insert(
      'offline_body_inspections',
      {
        'rlk_id': rlkId,
        'inspection_type': inspectionType,
        'base_image': baseImage,
        'marks': jsonEncode(marks),
        'status': 'draft',
        'created_at': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<int> saveSalonInspection({
    required int rlkId,
    required String? baseImage,
    required List<Map<String, dynamic>> marks,
  }) async {
    final db = await _db.database;

    return await db.insert(
      'offline_salon_inspections',
      {
        'rlk_id': rlkId,
        'base_image': baseImage,
        'marks': jsonEncode(marks),
        'status': 'draft',
        'created_at': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<Map<String, dynamic>>> getPendingBodyInspections() async {
    final db = await _db.database;
    final results = await db.query(
      'offline_body_inspections',
      where: 'status != ?',
      whereArgs: ['synced'],
      orderBy: 'created_at DESC',
    );

    return results.map((row) {
      return {
        'id': row['id'],
        'rlk_id': row['rlk_id'],
        'inspection_type': row['inspection_type'],
        'base_image': row['base_image'],
        'marks': jsonDecode(row['marks'] as String),
        'status': row['status'],
        'created_at': row['created_at'],
      };
    }).toList();
  }

  Future<List<Map<String, dynamic>>> getPendingSalonInspections() async {
    final db = await _db.database;
    final results = await db.query(
      'offline_salon_inspections',
      where: 'status != ?',
      whereArgs: ['synced'],
      orderBy: 'created_at DESC',
    );

    return results.map((row) {
      return {
        'id': row['id'],
        'rlk_id': row['rlk_id'],
        'base_image': row['base_image'],
        'marks': jsonDecode(row['marks'] as String),
        'status': row['status'],
        'created_at': row['created_at'],
      };
    }).toList();
  }

  Future<void> markAsSynced(String table, int id) async {
    final db = await _db.database;
    await db.update(
      table,
      {
        'status': 'synced',
        'synced_at': DateTime.now().millisecondsSinceEpoch,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteSynced(String table) async {
    final db = await _db.database;
    await db.delete(
      table,
      where: 'status = ?',
      whereArgs: ['synced'],
    );
  }
}

