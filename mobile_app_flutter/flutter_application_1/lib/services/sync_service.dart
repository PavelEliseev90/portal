import '../core/database/dao/inspection_dao.dart';
import '../core/network/api_client.dart';
import '../core/constants/app_constants.dart';

class SyncService {
  final InspectionDao _inspectionDao = InspectionDao();
  final ApiClient _apiClient = ApiClient();

  Future<SyncResult> syncAll() async {
    final result = SyncResult();
    
    try {
      // Синхронизация осмотров кузова
      final bodyInspections = await _inspectionDao.getPendingBodyInspections();
      for (var inspection in bodyInspections) {
        try {
          await _syncBodyInspection(inspection);
          await _inspectionDao.markAsSynced(
            'offline_body_inspections',
            inspection['id'] as int,
          );
          result.syncedCount++;
        } catch (e) {
          result.errors.add('Body inspection ${inspection['id']}: $e');
        }
      }

      // Синхронизация осмотров салона
      final salonInspections = await _inspectionDao.getPendingSalonInspections();
      for (var inspection in salonInspections) {
        try {
          await _syncSalonInspection(inspection);
          await _inspectionDao.markAsSynced(
            'offline_salon_inspections',
            inspection['id'] as int,
          );
          result.syncedCount++;
        } catch (e) {
          result.errors.add('Salon inspection ${inspection['id']}: $e');
        }
      }

      // Удаляем синхронизированные записи
      await _inspectionDao.deleteSynced('offline_body_inspections');
      await _inspectionDao.deleteSynced('offline_salon_inspections');
    } catch (e) {
      result.errors.add('Sync error: $e');
    }

    return result;
  }

  Future<void> _syncBodyInspection(Map<String, dynamic> inspection) async {
    await _apiClient.post(
      '${AppConstants.bodyInspectionPostEndpoint}/${inspection['rlk_id']}/',
      data: {
        'inspection_type': inspection['inspection_type'],
        'base_image': inspection['base_image'],
        'marks': inspection['marks'],
      },
    );
  }

  Future<void> _syncSalonInspection(Map<String, dynamic> inspection) async {
    await _apiClient.post(
      '${AppConstants.salonInspectionPostEndpoint}/${inspection['rlk_id']}/',
      data: {
        'base_image': inspection['base_image'],
        'marks': inspection['marks'],
      },
    );
  }
}

class SyncResult {
  int syncedCount = 0;
  List<String> errors = [];

  bool get hasErrors => errors.isNotEmpty;
}

