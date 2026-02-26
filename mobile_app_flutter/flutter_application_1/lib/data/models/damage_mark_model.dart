class DamageMarkModel {
  final String? id;
  final String type;
  final String typeName;
  final int x;
  final int y;
  final String text;
  final String? elementName;
  final String? photoPath;
  final String? photoUrl;
  final DateTime date;

  DamageMarkModel({
    this.id,
    required this.type,
    required this.typeName,
    required this.x,
    required this.y,
    required this.text,
    this.elementName,
    this.photoPath,
    this.photoUrl,
    DateTime? date,
  }) : date = date ?? DateTime.now();

  factory DamageMarkModel.fromJson(Map<String, dynamic> json) {
    DateTime? date;
    if (json['date'] != null) {
      try {
        date = DateTime.parse(json['date']);
      } catch (e) {
        date = DateTime.now();
      }
    }

    return DamageMarkModel(
      id: json['id']?.toString(),
      type: json['type'] ?? '',
      typeName: json['type_name'] ?? json['type'] ?? '',
      x: json['x'] ?? 0,
      y: json['y'] ?? 0,
      text: json['text'] ?? '',
      elementName: json['element_name'],
      photoUrl: json['photo_url'],
      date: date,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'type': type,
      'type_name': typeName,
      'x': x,
      'y': y,
      'text': text,
      'element_name': elementName,
      'date': date.toIso8601String(),
    };
  }
}

