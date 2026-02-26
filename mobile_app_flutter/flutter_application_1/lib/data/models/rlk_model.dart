class RlkModel {
  final int id;
  final int estimationId;
  final String number;
  final String vin;
  final String mark;
  final String model;
  final String modification;
  final String year;
  final String unitName;
  final String customerName;
  final String staffName;
  final String date;
  final String startEstimation;
  final double priceReception;

  RlkModel({
    required this.id,
    required this.estimationId,
    required this.number,
    required this.vin,
    required this.mark,
    required this.model,
    required this.modification,
    required this.year,
    required this.unitName,
    required this.customerName,
    required this.staffName,
    required this.date,
    required this.startEstimation,
    required this.priceReception,
  });

  factory RlkModel.fromJson(Map<String, dynamic> json) {
    return RlkModel(
      id: json['id'] ?? 0,
      estimationId: json['estimation_id'] ?? 0,
      number: json['number'] ?? '',
      vin: json['vin'] ?? '',
      mark: json['mark'] ?? '',
      model: json['model'] ?? '',
      modification: json['modification'] ?? '',
      year: json['year']?.toString() ?? '',
      unitName: json['unit_name'] ?? '',
      customerName: json['customer_name'] ?? '',
      staffName: json['staff_name'] ?? '',
      date: json['date'] ?? '',
      startEstimation: json['start_estimation'] ?? '',
      priceReception: (json['price_reception'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'estimation_id': estimationId,
      'number': number,
      'vin': vin,
      'mark': mark,
      'model': model,
      'modification': modification,
      'year': year,
      'unit_name': unitName,
      'customer_name': customerName,
      'staff_name': staffName,
      'date': date,
      'start_estimation': startEstimation,
      'price_reception': priceReception,
    };
  }
}

