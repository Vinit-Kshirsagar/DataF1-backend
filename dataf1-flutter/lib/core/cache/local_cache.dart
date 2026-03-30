import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

/// Local on-device cache for stale-while-revalidate pattern.
/// Shows last successful response instantly while fresh data loads.
class LocalCache {
  static const _prefix = 'dataf1_cache_';
  static const _tsPrefix = 'dataf1_ts_';
  static const _freshDuration = Duration(minutes: 5);

  static Future<void> set(String key, Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_prefix$key', jsonEncode(data));
    await prefs.setInt(
        '$_tsPrefix$key', DateTime.now().millisecondsSinceEpoch);
  }

  static Future<Map<String, dynamic>?> get(String key) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('$_prefix$key');
    if (raw == null) return null;
    try {
      return jsonDecode(raw) as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  static Future<bool> isFresh(String key) async {
    final prefs = await SharedPreferences.getInstance();
    final ts = prefs.getInt('$_tsPrefix$key');
    if (ts == null) return false;
    final age = DateTime.now().millisecondsSinceEpoch - ts;
    return age < _freshDuration.inMilliseconds;
  }

  static Future<void> clear(String key) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('$_prefix$key');
    await prefs.remove('$_tsPrefix$key');
  }
}
