class AppConstants {
  // API Base URL
  static const String baseUrl = 'https://ah.kors-group.com';
  static const String apiBaseUrl = '$baseUrl/api/a/v2';
  
  // WebSocket
  static const String wsBaseUrl = 'wss://ah.kors-group.com/ws';
  
  // API Endpoints
  static const String loginEndpoint = '/login_in/';
  static const String loginInfoEndpoint = '/login_info/';
  static const String rlkEcoEndpoint = '/rlk_eco/';
  static const String bodyElementsEndpoint = '/estimation_body_elements';
  static const String bodyInspectionPostEndpoint = '/estimation_body_inspection_post';
  static const String salonElementsEndpoint = '/estimation_salon_elements';
  static const String salonInspectionPostEndpoint = '/estimation_salon_inspection_post';
  static const String catalogsMarksEndpoint = '/catalogs/marks/';
  static const String catalogsModelsEndpoint = '/catalogs/models';
  static const String catalogsModificationsEndpoint = '/catalogs/modifications';
  static const String offlineSyncEndpoint = '/offline_sync/';
  
  // Database
  static const String databaseName = 'korsgroup.db';
  static const int databaseVersion = 1;
  
  // Storage Keys
  static const String authTokenKey = 'auth_token';
  static const String userDataKey = 'user_data';
  static const String lastSyncKey = 'last_sync';
}

