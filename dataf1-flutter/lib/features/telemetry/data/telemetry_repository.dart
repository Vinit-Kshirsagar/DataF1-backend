import 'package:dio/dio.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/cache/local_cache.dart';
import 'telemetry_models.dart';

class TelemetryRepository {
  final Dio _dio;

  TelemetryRepository({Dio? dio}) : _dio = dio ?? DioClient().dio;

  String _cacheKey({
    required int year,
    required int round,
    required String session,
    required String driver,
    required String metric,
    required int lapNumber,
  }) =>
      'telemetry_${year}_${round}_${session}_${driver}_${metric}_$lapNumber';

  /// Fetch telemetry with stale-while-revalidate:
  /// 1. Return cached data immediately if available
  /// 2. Fetch fresh data in background
  /// 3. Update cache with fresh data
  Future<TelemetryData> getTelemetry({
    required int year,
    required int round,
    required String session,
    required String driver,
    required String metric,
    int lapNumber = 0,
    void Function(TelemetryData fresh)? onFreshData,
  }) async {
    final key = _cacheKey(
      year: year,
      round: round,
      session: session,
      driver: driver,
      metric: metric,
      lapNumber: lapNumber,
    );

    // Check local cache first
    final cached = await LocalCache.get(key);
    final isFresh = await LocalCache.isFresh(key);

    if (cached != null) {
      final cachedData = TelemetryData.fromJson(cached);

      if (!isFresh && onFreshData != null) {
        // Stale — fetch fresh in background
        _fetchAndCache(
          year: year,
          round: round,
          session: session,
          driver: driver,
          metric: metric,
          lapNumber: lapNumber,
          key: key,
          onFreshData: onFreshData,
        );
      }

      return cachedData;
    }

    // No cache — fetch and wait
    return _fetchAndCache(
      year: year,
      round: round,
      session: session,
      driver: driver,
      metric: metric,
      lapNumber: lapNumber,
      key: key,
      onFreshData: onFreshData,
    );
  }

  Future<TelemetryData> _fetchAndCache({
    required int year,
    required int round,
    required String session,
    required String driver,
    required String metric,
    required int lapNumber,
    required String key,
    void Function(TelemetryData)? onFreshData,
  }) async {
    final response = await _dio.post('/telemetry/', data: {
      'year': year,
      'round': round,
      'session': session,
      'driver': driver,
      'metric': metric,
      'lap_number': lapNumber,
    });
    final data = TelemetryData.fromJson(
        response.data as Map<String, dynamic>);
    await LocalCache.set(key, response.data as Map<String, dynamic>);
    onFreshData?.call(data);
    return data;
  }

  Future<ComparisonData> getComparison({
    required int year,
    required int round,
    required String session,
    required String driver1,
    required String driver2,
    required String metric,
    int lapNumber = 0,
  }) async {
    final response = await _dio.post('/telemetry/compare', data: {
      'year': year,
      'round': round,
      'session': session,
      'driver1': driver1,
      'driver2': driver2,
      'metric': metric,
      'lap_number': lapNumber,
    });
    return ComparisonData.fromJson(
        response.data as Map<String, dynamic>);
  }
}
