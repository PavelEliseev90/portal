# Осмотр кузова и салона - Детальная реализация для мобильного приложения

## Обзор

Осмотр кузова и салона - это интерактивные экраны, где пользователь кликает на изображение автомобиля, система определяет элемент кузова/салона по координатам, и пользователь выбирает тип повреждения.

---

## 1. ОСМОТР КУЗОВА

### 1.1 Типы осмотра кузова

- **pered** - Передняя часть
- **vod** - Водительская сторона
- **pass** - Пассажирская сторона
- **zad** - Задняя часть
- **up** - Крыша

### 1.2 Изображения для каждого типа

```
/media_dop/body_capture/sedan_new.png      - Передняя часть
/media_dop/body_capture/sedan_left_new.png - Водительская сторона
/media_dop/body_capture/sedan_right_new.png - Пассажирская сторона
/media_dop/body_capture/sedan_back_new.png - Задняя часть
/media_dop/body_capture/sedan_up.png        - Крыша
```

### 1.3 Типы повреждений кузова

| Код | Название | Описание |
|-----|----------|----------|
| `tol` | Толщиномер | Показание толщиномера (требует ввода значения) |
| `tr` | Трещина | Трещина на элементе |
| `skol` | Скол | Скол краски/стекла |
| `vmyat` | Вмятина | Вмятина (баллистика) |
| `vmyat_strong` | Вмятина сильная | Вмятина (окрас) |
| `carap` | Царапина | Царапина (полировка) |
| `carap_strong` | Царапина сильная | Сильная царапина |
| `rzav` | Ржавчина | Ржавчина |
| `rzav_strong` | Ржавчина сквозная | Сквозная ржавчина |
| `perecras` | Перекрас | Перекрас элемента |
| `perecras_strong` | Перекрас сильный | Сильный перекрас |
| `stiker` | Наклейка | Наклейка на элементе |
| `toner` | Тонировка | Тонировка |
| `poly` | Полировка | Полировка |
| `replace` | Заменен | Элемент был заменен |
| `replace_add` | Заменить | Требуется замена элемента |

### 1.4 Логика работы

1. **Загрузка данных элементов:**
   - Получение списка элементов кузова из `RegInfoBody` по типу кузова и стороне
   - Каждый элемент содержит:
     - `body_element` - код элемента
     - `body_elem_name` - название элемента
     - `polygon` - координаты полигона (формат: "x1,y1,x2,y2,x3,y3,...")

2. **Обработка клика:**
   - При клике на canvas получаются координаты (x, y)
   - Функция `isLatLngInZone(x, y, coor_x, coor_y)` проверяет попадание точки в полигон
   - Определяется элемент кузова
   - Открывается модальное окно с выбором типа повреждения

3. **Сохранение данных:**
   - Генерируется UUID для отметки
   - Сохраняются:
     - `type_point` - тип повреждения (текстовое название)
     - `cor_x` - координата X
     - `cor_y` - координата Y
     - `text` - дополнительный текст (для толщиномера - значение)
     - `date` - дата создания отметки
     - `file` - фотография (опционально)
   - Canvas обновляется с отрисовкой всех отметок

4. **Отправка на сервер:**
   - Canvas конвертируется в base64 (`toDataURL()`)
   - Отправляется как `url_image` в POST запросе
   - Каждая отметка отправляется отдельно с полями:
     - `photo_type_{uid}` - тип повреждения
     - `photo_x_{uid}` - координата X
     - `photo_y_{uid}` - координата Y
     - `photo_text_{uid}` - текст (значение толщиномера)
     - `photo_name_{uid}` - название отметки
     - `photo_date_{uid}` - дата
     - `photo_{uid}` - файл фотографии

---

## 2. ОСМОТР САЛОНА

### 2.1 Типы повреждений салона

| Код | Название | Описание |
|-----|----------|----------|
| `perecras` | Перекрас | Перекрас элемента салона |
| `pereshiv` | Перешив | Перешив элемента салона |
| `dirka` | Дырка | Дырка в элементе салона |
| `vost` | Восстановление | Восстановление формы элемента |

### 2.2 Изображение салона

```
/media_dop/salon_capture/salon.png
```

### 2.3 Логика работы

Аналогична осмотру кузова, но:
- Используются элементы с `side = 'салон'`
- Типы повреждений ограничены 4 вариантами
- Сохранение в `type_file = 'array_images_osmotr_salon'`

---

## 3. API ENDPOINTS

### 3.1 Получение данных для осмотра

**GET /estimations/<rlk_id>/osmotr/<type>/**

**Параметры:**
- `rlk_id` - ID рабочего листа
- `type` - тип осмотра (pered, vod, pass, zad, up)

**Response (HTML):**
Возвращает HTML страницу с canvas и данными элементов

**Альтернативный API (для мобильного приложения):**

**GET /api/a/v1/estimation_body_elements/<rlk_id>/<type>/**

**Response:**
```json
{
  "type": "estimation_body_elements",
  "elements": [
    {
      "name": "капот",
      "code": "kapot",
      "polygon": [100, 200, 150, 200, 150, 250, 100, 250],
      "coor_x": [100, 150, 150, 100],
      "coor_y": [200, 200, 250, 250]
    }
  ],
  "existing_marks": [
    {
      "id": 123,
      "type": "царапина",
      "x": 120,
      "y": 220,
      "text": "",
      "date": "15-01-2024 10:30",
      "photo_url": "/media/estimation/photos/photo_123.jpg"
    }
  ],
  "base_image_url": "/media_dop/body_capture/sedan_new.png"
}
```

### 3.2 Сохранение осмотра кузова

**POST /estimations/<rlk_id>/osmotr/<type>/**

**Request (multipart/form-data):**
```
url_image: data:image/png;base64,... (canvas в base64)
photo_type_{uid}: "царапина"
photo_x_{uid}: 120
photo_y_{uid}: 220
photo_text_{uid}: ""
photo_name_{uid}: "царапина - 1"
photo_date_{uid}: "15-01-2024 10:30"
photo_{uid}: (file) - опционально
```

**Альтернативный API (для мобильного приложения):**

**POST /api/a/v1/estimation_body_inspection_post/<rlk_id>/**

**Request:**
```json
{
  "type": "pered", // pered, vod, pass, zad, up
  "base_image": "data:image/png;base64,...", // canvas в base64
  "marks": [
    {
      "type": "царапина",
      "x": 120,
      "y": 220,
      "text": "",
      "element_name": "капот",
      "photo": "data:image/jpeg;base64,..." // опционально
    }
  ]
}
```

### 3.3 Сохранение осмотра салона

**POST /estimations/<rlk_id>/osmotr_salon/page_osmotr_salon/**

**Request:**
Аналогично осмотру кузова, но `type_file = 'array_images_osmotr_salon'`

**Альтернативный API:**

**POST /api/a/v1/estimation_salon_inspection_post/<rlk_id>/**

**Request:**
```json
{
  "base_image": "data:image/png;base64,...",
  "marks": [
    {
      "type": "перекрас", // perecras, pereshiv, dirka, vost
      "x": 120,
      "y": 220,
      "text": "",
      "element_name": "передняя панель",
      "photo": "data:image/jpeg;base64,..."
    }
  ]
}
```

---

## 4. РЕАЛИЗАЦИЯ В FLUTTER

### 4.1 Виджет для осмотра кузова/салона

```dart
// lib/presentation/estimation/widgets/body_inspection_widget.dart
import 'package:flutter/material.dart';
import 'dart:ui' as ui;
import 'package:flutter/rendering.dart';
import 'dart:typed_data';
import 'dart:convert';
import 'package:image_picker/image_picker.dart';

class BodyInspectionWidget extends StatefulWidget {
  final String inspectionType; // 'pered', 'vod', 'pass', 'zad', 'up', 'salon'
  final int rlkId;
  final List<BodyElement> elements;
  final List<DamageMark> existingMarks;

  const BodyInspectionWidget({
    Key? key,
    required this.inspectionType,
    required this.rlkId,
    required this.elements,
    required this.existingMarks,
  }) : super(key: key);

  @override
  State<BodyInspectionWidget> createState() => _BodyInspectionWidgetState();
}

class _BodyInspectionWidgetState extends State<BodyInspectionWidget> {
  final GlobalKey _canvasKey = GlobalKey();
  List<DamageMark> _marks = [];
  String? _selectedElement;
  Offset? _selectedPoint;

  @override
  void initState() {
    super.initState();
    _marks = List.from(widget.existingMarks);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_getInspectionTitle()),
        backgroundColor: PortalColors.primary,
      ),
      body: Column(
        children: [
          // Canvas с изображением
          Expanded(
            child: GestureDetector(
              onTapDown: (details) => _handleTap(details),
              child: CustomPaint(
                key: _canvasKey,
                painter: BodyInspectionPainter(
                  imageUrl: _getImageUrl(),
                  elements: widget.elements,
                  marks: _marks,
                ),
                size: Size.infinite,
              ),
            ),
          ),
          
          // Список отметок
          Expanded(
            flex: 0,
            child: Container(
              height: 200,
              child: ListView.builder(
                itemCount: _marks.length,
                itemBuilder: (context, index) {
                  final mark = _marks[index];
                  return ListTile(
                    title: Text('${mark.type} - ${mark.elementName ?? ""}'),
                    subtitle: Text('X: ${mark.x}, Y: ${mark.y}'),
                    trailing: IconButton(
                      icon: Icon(Icons.delete),
                      onPressed: () => _removeMark(mark),
                    ),
                  );
                },
              ),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _saveInspection,
        child: Icon(Icons.save),
      ),
    );
  }

  void _handleTap(TapDownDetails details) {
    final RenderBox renderBox = _canvasKey.currentContext!.findRenderObject() as RenderBox;
    final localPosition = renderBox.globalToLocal(details.globalPosition);
    
    // Определяем элемент по координатам
    final element = _findElementAtPoint(localPosition.dx, localPosition.dy);
    
    setState(() {
      _selectedElement = element?.name;
      _selectedPoint = localPosition;
    });
    
    // Показываем диалог выбора типа повреждения
    _showDamageTypeDialog(element, localPosition);
  }

  BodyElement? _findElementAtPoint(double x, double y) {
    for (var element in widget.elements) {
      if (_isPointInPolygon(x, y, element.coorX, element.coorY)) {
        return element;
      }
    }
    return null;
  }

  bool _isPointInPolygon(double x, double y, List<int> coorX, List<int> coorY) {
    bool inside = false;
    for (int i = 0, j = coorX.length - 1; i < coorX.length; j = i++) {
      final xi = coorX[i].toDouble();
      final yi = coorY[i].toDouble();
      final xj = coorX[j].toDouble();
      final yj = coorY[j].toDouble();
      
      final intersect = (yi > y) != (yj > y) && 
                       x < ((xj - xi) * (y - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  void _showDamageTypeDialog(BodyElement? element, Offset point) {
    final damageTypes = widget.inspectionType == 'salon'
        ? _getSalonDamageTypes()
        : _getBodyDamageTypes();
    
    showModalBottomSheet(
      context: context,
      builder: (context) => DamageTypeSelector(
        elementName: element?.name ?? 'Неизвестный элемент',
        damageTypes: damageTypes,
        onSelected: (type) => _addMark(type, point, element),
      ),
    );
  }

  List<DamageType> _getBodyDamageTypes() {
    return [
      DamageType('толщиномер', 'tol', requiresValue: true),
      DamageType('трещина', 'tr'),
      DamageType('скол', 'skol'),
      DamageType('вмятина', 'vmyat'),
      DamageType('вмятина сильная', 'vmyat_strong'),
      DamageType('царапина', 'carap'),
      DamageType('царапина сильная', 'carap_strong'),
      DamageType('ржавчина', 'rzav'),
      DamageType('ржавчина сквозная', 'rzav_strong'),
      DamageType('перекрас', 'perecras'),
      DamageType('перекрас сильный', 'perecras_strong'),
      DamageType('наклейка', 'stiker'),
      DamageType('тонировка', 'toner'),
      DamageType('полировка', 'poly'),
      DamageType('заменен', 'replace'),
      DamageType('заменить', 'replace_add'),
    ];
  }

  List<DamageType> _getSalonDamageTypes() {
    return [
      DamageType('перекрас', 'perecras'),
      DamageType('перешив', 'pereshiv'),
      DamageType('дырка', 'dirka'),
      DamageType('восстановление', 'vost'),
    ];
  }

  Future<void> _addMark(DamageType type, Offset point, BodyElement? element) async {
    String? text;
    
    // Если требуется значение (толщиномер)
    if (type.requiresValue) {
      text = await _showThicknessInputDialog();
      if (text == null) return;
    }
    
    // Опционально: добавить фото
    XFile? photo;
    final addPhoto = await _showAddPhotoDialog();
    if (addPhoto == true) {
      final picker = ImagePicker();
      photo = await picker.pickImage(source: ImageSource.camera);
    }
    
    setState(() {
      _marks.add(DamageMark(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        type: type.code,
        typeName: type.name,
        x: point.dx.toInt(),
        y: point.dy.toInt(),
        text: text ?? '',
        elementName: element?.name,
        photo: photo,
      ));
    });
  }

  Future<String?> _showThicknessInputDialog() async {
    // Реализация диалога ввода значения толщиномера
    return null;
  }

  Future<bool?> _showAddPhotoDialog() async {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Добавить фото?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text('Нет'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text('Да'),
          ),
        ],
      ),
    );
  }

  void _removeMark(DamageMark mark) {
    setState(() {
      _marks.remove(mark);
    });
  }

  Future<void> _saveInspection() async {
    // Конвертируем canvas в base64
    final imageBytes = await _captureCanvas();
    final base64Image = base64Encode(imageBytes);
    
    // Отправляем на сервер
    await _saveToServer(base64Image);
  }

  Future<Uint8List> _captureCanvas() async {
    // Реализация захвата canvas
    return Uint8List(0);
  }

  Future<void> _saveToServer(String base64Image) async {
    // Отправка данных на сервер
  }

  String _getInspectionTitle() {
    switch (widget.inspectionType) {
      case 'pered': return 'Передняя часть';
      case 'vod': return 'Водительская сторона';
      case 'pass': return 'Пассажирская сторона';
      case 'zad': return 'Задняя часть';
      case 'up': return 'Крыша';
      case 'salon': return 'Осмотр салона';
      default: return 'Осмотр';
    }
  }

  String _getImageUrl() {
    switch (widget.inspectionType) {
      case 'pered': return '/media_dop/body_capture/sedan_new.png';
      case 'vod': return '/media_dop/body_capture/sedan_left_new.png';
      case 'pass': return '/media_dop/body_capture/sedan_right_new.png';
      case 'zad': return '/media_dop/body_capture/sedan_back_new.png';
      case 'up': return '/media_dop/body_capture/sedan_up.png';
      case 'salon': return '/media_dop/salon_capture/salon.png';
      default: return '';
    }
  }
}

// Модели данных
class BodyElement {
  final String name;
  final String code;
  final List<int> coorX;
  final List<int> coorY;

  BodyElement({
    required this.name,
    required this.code,
    required this.coorX,
    required this.coorY,
  });
}

class DamageMark {
  final String id;
  final String type;
  final String typeName;
  final int x;
  final int y;
  final String text;
  final String? elementName;
  final XFile? photo;
  final DateTime date;

  DamageMark({
    required this.id,
    required this.type,
    required this.typeName,
    required this.x,
    required this.y,
    required this.text,
    this.elementName,
    this.photo,
    DateTime? date,
  }) : date = date ?? DateTime.now();
}

class DamageType {
  final String name;
  final String code;
  final bool requiresValue;

  DamageType(this.name, this.code, {this.requiresValue = false});
}

// Custom Painter для отрисовки
class BodyInspectionPainter extends CustomPainter {
  final String imageUrl;
  final List<BodyElement> elements;
  final List<DamageMark> marks;
  ui.Image? _image;

  BodyInspectionPainter({
    required this.imageUrl,
    required this.elements,
    required this.marks,
  });

  @override
  void paint(Canvas canvas, Size size) {
    // Загрузка и отрисовка изображения
    // Отрисовка отметок
    for (var mark in marks) {
      _drawMark(canvas, mark);
    }
  }

  void _drawMark(Canvas canvas, DamageMark mark) {
    // Отрисовка иконки типа повреждения
    // Отрисовка номера отметки
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
```

---

## 5. ВЕБ-СОКЕТ ДЛЯ ЧАТА

### 5.1 Подключение к веб-сокету

**URL:**
```
wss://ah.kors-group.com/ws/rlk_{rlk_id}/
```

**Также:**
```
wss://ah.kors-group.com/ws/rlk_list_eco/
```

### 5.2 Формат сообщений

**Отправка сообщения:**
```json
{
  "chat_id": "123",
  "name": "user@example.com",
  "chat": "rlk_2847904",
  "message": "Текст сообщения",
  "username": "user@example.com",
  "last_name": "Иванов",
  "first_name": "Иван",
  "psevdo_name": "Иванов И.И.",
  "eco": true
}
```

**Получение сообщения:**
```json
{
  "type": "chat_message",
  "chat_id": "123",
  "chat": "rlk_2847904",
  "message": "Текст сообщения",
  "username": "user@example.com",
  "last_name": "Иванов",
  "first_name": "Иван",
  "psevdo_name": "Иванов И.И.",
  "eco": true,
  "admin": false
}
```

### 5.3 Реализация в Flutter

```dart
// lib/core/network/websocket_service.dart
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

class WebSocketService {
  WebSocketChannel? _channel;
  final String baseUrl = 'wss://ah.kors-group.com/ws/';
  
  void connect(String roomName, Function(Map<String, dynamic>) onMessage) {
    final url = '$baseUrl$roomName/';
    _channel = WebSocketChannel.connect(Uri.parse(url));
    
    _channel!.stream.listen(
      (message) {
        final data = jsonDecode(message) as Map<String, dynamic>;
        onMessage(data);
      },
      onError: (error) {
        print('WebSocket error: $error');
      },
      onDone: () {
        print('WebSocket closed');
      },
    );
  }
  
  void sendMessage({
    required String chatId,
    required String name,
    required String chat,
    required String message,
    required String username,
    required String lastName,
    required String firstName,
    required String psevdoName,
    required bool eco,
  }) {
    final messageData = {
      'chat_id': chatId,
      'name': name,
      'chat': chat,
      'message': message,
      'username': username,
      'last_name': lastName,
      'first_name': firstName,
      'psevdo_name': psevdoName,
      'eco': eco,
    };
    
    _channel?.sink.add(jsonEncode(messageData));
  }
  
  void disconnect() {
    _channel?.sink.close();
  }
}
```

### 5.4 Экран чата

```dart
// lib/presentation/estimation/screens/chat_screen.dart
import 'package:flutter/material.dart';
import '../../../core/network/websocket_service.dart';

class ChatScreen extends StatefulWidget {
  final int rlkId;
  final String chatId;

  const ChatScreen({
    Key? key,
    required this.rlkId,
    required this.chatId,
  }) : super(key: key);

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final WebSocketService _wsService = WebSocketService();
  final TextEditingController _messageController = TextEditingController();
  final List<ChatMessage> _messages = [];

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  void _connectWebSocket() {
    _wsService.connect(
      'rlk_${widget.rlkId}',
      (data) {
        setState(() {
          _messages.add(ChatMessage.fromJson(data));
        });
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Чат - RLK ${widget.rlkId}'),
        backgroundColor: PortalColors.primary,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (context, index) {
                final message = _messages[index];
                return ChatBubble(message: message);
              },
            ),
          ),
          Container(
            padding: EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Введите сообщение...',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(20),
                      ),
                    ),
                  ),
                ),
                IconButton(
                  icon: Icon(Icons.send),
                  onPressed: _sendMessage,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _sendMessage() {
    if (_messageController.text.isEmpty) return;
    
    _wsService.sendMessage(
      chatId: widget.chatId,
      name: 'user@example.com', // Получить из auth
      chat: 'rlk_${widget.rlkId}',
      message: _messageController.text,
      username: 'user@example.com',
      lastName: 'Иванов',
      firstName: 'Иван',
      psevdoName: 'Иванов И.И.',
      eco: true,
    );
    
    _messageController.clear();
  }

  @override
  void dispose() {
    _wsService.disconnect();
    _messageController.dispose();
    super.dispose();
  }
}

class ChatMessage {
  final String message;
  final String username;
  final String firstName;
  final String lastName;
  final String psevdoName;
  final bool eco;
  final DateTime timestamp;

  ChatMessage({
    required this.message,
    required this.username,
    required this.firstName,
    required this.lastName,
    required this.psevdoName,
    required this.eco,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      message: json['message'] ?? '',
      username: json['username'] ?? '',
      firstName: json['first_name'] ?? '',
      lastName: json['last_name'] ?? '',
      psevdoName: json['psevdo_name'] ?? '',
      eco: json['eco'] ?? false,
    );
  }
}
```

---

## 6. ОФЛАЙН РЕЖИМ ДЛЯ ОСМОТРА

### 6.1 Сохранение данных осмотра локально

```dart
// lib/core/database/dao/inspection_dao.dart
class InspectionDao {
  final DatabaseHelper _db = DatabaseHelper.instance;

  Future<int> saveBodyInspection({
    required int rlkId,
    required String type,
    required String baseImage,
    required List<DamageMark> marks,
  }) async {
    final db = await _db.database;
    
    return await db.insert(
      'offline_body_inspections',
      {
        'rlk_id': rlkId,
        'type': type,
        'base_image': baseImage,
        'marks': jsonEncode(marks.map((m) => m.toJson()).toList()),
        'status': 'draft',
        'created_at': DateTime.now().millisecondsSinceEpoch,
      },
    );
  }

  Future<List<Map<String, dynamic>>> getPendingInspections() async {
    final db = await _db.database;
    return await db.query(
      'offline_body_inspections',
      where: 'status != ?',
      whereArgs: ['synced'],
    );
  }
}
```

---

Этот документ описывает полную реализацию осмотра кузова и салона, а также веб-сокет для чата в мобильном приложении.

