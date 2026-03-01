import 'dart:convert';
import 'dart:typed_data';

class ImageUtils {
  static String imageToBase64(Uint8List imageBytes) {
    return base64Encode(imageBytes);
  }

  static String imageToBase64DataUrl(Uint8List imageBytes, String mimeType) {
    final base64 = imageToBase64(imageBytes);
    return 'data:$mimeType;base64,$base64';
  }
}

