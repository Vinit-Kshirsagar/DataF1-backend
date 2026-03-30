import 'package:dio/dio.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/cache/local_cache.dart';
import 'home_models.dart';

class HomeRepository {
  final Dio _dio;

  HomeRepository({Dio? dio}) : _dio = dio ?? DioClient().dio;

  Future<List<RaceModel>> getRaces(int year) async {
    const key = 'races_2026';
    final cached = await LocalCache.get(key);

    if (cached != null) {
      // Return cached immediately, refresh in background
      _refreshRaces(year, key);
      final list = cached['races'] as List;
      return list
          .map((r) => RaceModel.fromJson(r as Map<String, dynamic>))
          .toList();
    }

    final response = await _dio.get('/races/$year');
    final data = response.data as Map<String, dynamic>;
    await LocalCache.set(key, data);
    final list = data['races'] as List;
    return list
        .map((r) => RaceModel.fromJson(r as Map<String, dynamic>))
        .toList();
  }

  void _refreshRaces(int year, String key) async {
    try {
      final response = await _dio.get('/races/$year');
      await LocalCache.set(key, response.data as Map<String, dynamic>);
    } catch (_) {}
  }

  Future<List<SessionModel>> getSessions(int year, int round) async {
    final response = await _dio.get('/races/$year/$round/sessions');
    final data = response.data as Map<String, dynamic>;
    final list = data['sessions'] as List;
    return list
        .map((s) => SessionModel.fromJson(s as Map<String, dynamic>))
        .toList();
  }

  Future<List<DriverModel>> getDrivers(
      int year, int round, String sessionKey) async {
    final response =
        await _dio.get('/races/$year/$round/sessions/$sessionKey/drivers');
    final data = response.data as Map<String, dynamic>;
    final list = data['drivers'] as List;
    return list
        .map((d) => DriverModel.fromJson(d as Map<String, dynamic>))
        .toList();
  }

  Future<List<MetricModel>> getMetrics() async {
    final response = await _dio.get('/races/metrics');
    final data = response.data as Map<String, dynamic>;
    final list = data['metrics'] as List;
    return list
        .map((m) => MetricModel.fromJson(m as Map<String, dynamic>))
        .toList();
  }
}
