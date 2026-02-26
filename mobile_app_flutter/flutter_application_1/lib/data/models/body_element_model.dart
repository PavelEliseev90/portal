class BodyElementModel {
  final String name;
  final String code;
  final String bodyElemName;
  final String polygon;
  final List<int> coorX;
  final List<int> coorY;

  BodyElementModel({
    required this.name,
    required this.code,
    required this.bodyElemName,
    required this.polygon,
    required this.coorX,
    required this.coorY,
  });

  factory BodyElementModel.fromJson(Map<String, dynamic> json) {
    return BodyElementModel(
      name: json['name'] ?? '',
      code: json['code'] ?? '',
      bodyElemName: json['body_elem_name'] ?? '',
      polygon: json['polygon'] ?? '',
      coorX: List<int>.from(json['coor_x'] ?? []),
      coorY: List<int>.from(json['coor_y'] ?? []),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'code': code,
      'body_elem_name': bodyElemName,
      'polygon': polygon,
      'coor_x': coorX,
      'coor_y': coorY,
    };
  }
}

