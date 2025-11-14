import pytest
import geopandas as gpd
import json
import tempfile
import os
from pathlib import Path
from shapely.geometry import Point, Polygon, LineString
import shutil

# Import your converter module (adjust import based on your file name)
# from convert import convert_shapefile, MetricsCollector, NullCollector, JsonLogCollector

# Mock implementation for testing (replace with actual imports)
class MockMetricsCollector:
    def __init__(self):
        self.events = []
    
    def record_conversion_start(self):
        self.events.append('start')
    
    def record_conversion_success(self, duration, metadata):
        self.events.append(('success', duration, metadata))
    
    def record_conversion_failure(self, error):
        self.events.append(('failure', error))
    
    def record_read_time(self, duration):
        self.events.append(('read', duration))
    
    def record_write_time(self, duration):
        self.events.append(('write', duration))
    
    def record_feature_count(self, count):
        self.events.append(('feature_count', count))
    
    def record_file_sizes(self, input_mb, output_mb):
        self.events.append(('file_sizes', input_mb, output_mb))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_point_shapefile(temp_dir):
    """Create a simple point shapefile for testing"""
    data = {
        'name': ['Location A', 'Location B', 'Location C'],
        'value': [100, 200, 300],
        'geometry': [
            Point(-122.4194, 37.7749),  # San Francisco
            Point(-118.2437, 34.0522),  # Los Angeles
            Point(-73.9352, 40.7306)    # New York
        ]
    }
    gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    shp_path = os.path.join(temp_dir, 'test_points.shp')
    gdf.to_file(shp_path)
    
    return shp_path, gdf


@pytest.fixture
def sample_polygon_shapefile(temp_dir):
    """Create a polygon shapefile for testing"""
    data = {
        'region': ['North', 'South'],
        'area': [1000, 2000],
        'geometry': [
            Polygon([(-122, 37), (-122, 38), (-121, 38), (-121, 37)]),
            Polygon([(-118, 34), (-118, 35), (-117, 35), (-117, 34)])
        ]
    }
    gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    shp_path = os.path.join(temp_dir, 'test_polygons.shp')
    gdf.to_file(shp_path)
    
    return shp_path, gdf


@pytest.fixture
def sample_line_shapefile(temp_dir):
    """Create a line shapefile for testing"""
    data = {
        'road': ['Highway 1', 'Route 66'],
        'length': [150, 200],
        'geometry': [
            LineString([(-122, 37), (-122, 38), (-121, 38)]),
            LineString([(-118, 34), (-117, 35)])
        ]
    }
    gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
    
    shp_path = os.path.join(temp_dir, 'test_lines.shp')
    gdf.to_file(shp_path)
    
    return shp_path, gdf


class TestBasicConversion:
    """Test basic conversion functionality"""
    
    def test_convert_point_shapefile(self, sample_point_shapefile, temp_dir):
        """Test converting a simple point shapefile"""
        shp_path, original_gdf = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        # Perform conversion
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        # Read back the GeoJSON
        result_gdf = gpd.read_file(output_path)
        
        # Assertions
        assert len(result_gdf) == len(original_gdf)
        assert result_gdf.crs == original_gdf.crs
        assert list(result_gdf['name']) == list(original_gdf['name'])
        assert all(result_gdf.geometry.geom_type == 'Point')
    
    def test_convert_polygon_shapefile(self, sample_polygon_shapefile, temp_dir):
        """Test converting a polygon shapefile"""
        shp_path, original_gdf = sample_polygon_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        
        assert len(result_gdf) == len(original_gdf)
        assert all(result_gdf.geometry.geom_type == 'Polygon')
        assert list(result_gdf['region']) == list(original_gdf['region'])
    
    def test_convert_line_shapefile(self, sample_line_shapefile, temp_dir):
        """Test converting a line shapefile"""
        shp_path, original_gdf = sample_line_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        
        assert len(result_gdf) == len(original_gdf)
        assert all(result_gdf.geometry.geom_type == 'LineString')


class TestDataIntegrity:
    """Test that data is preserved during conversion"""
    
    def test_attribute_preservation(self, sample_point_shapefile, temp_dir):
        """Test that all attributes are preserved"""
        shp_path, original_gdf = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        
        # Check all columns are present
        assert set(result_gdf.columns) == set(original_gdf.columns)
        
        # Check values are preserved
        for col in ['name', 'value']:
            assert list(result_gdf[col]) == list(original_gdf[col])
    
    def test_geometry_precision(self, sample_point_shapefile, temp_dir):
        """Test that geometry coordinates are preserved with acceptable precision"""
        shp_path, original_gdf = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        
        # Check coordinates are within acceptable tolerance (6 decimal places)
        for orig_geom, result_geom in zip(original_gdf.geometry, result_gdf.geometry):
            assert orig_geom.equals_exact(result_geom, tolerance=1e-6)
    
    def test_crs_preservation(self, sample_point_shapefile, temp_dir):
        """Test that CRS is preserved"""
        shp_path, original_gdf = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        
        assert result_gdf.crs == original_gdf.crs


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_empty_shapefile(self, temp_dir):
        """Test converting an empty shapefile"""
        empty_gdf = gpd.GeoDataFrame(
            {'name': [], 'geometry': []},
            crs='EPSG:4326'
        )
        shp_path = os.path.join(temp_dir, 'empty.shp')
        empty_gdf.to_file(shp_path)
        
        output_path = os.path.join(temp_dir, 'output.geojson')
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        assert len(result_gdf) == 0
    
    def test_missing_file(self, temp_dir):
        """Test handling of missing input file"""
        non_existent = os.path.join(temp_dir, 'does_not_exist.shp')
        
        with pytest.raises(Exception):
            gpd.read_file(non_existent)
    
    def test_large_feature_count(self, temp_dir):
        """Test conversion with many features"""
        n_features = 1000
        data = {
            'id': list(range(n_features)),
            'geometry': [Point(i * 0.01, i * 0.01) for i in range(n_features)]
        }
        gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
        
        shp_path = os.path.join(temp_dir, 'large.shp')
        gdf.to_file(shp_path)
        
        output_path = os.path.join(temp_dir, 'output.geojson')
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        assert len(result_gdf) == n_features
    
    def test_special_characters_in_attributes(self, temp_dir):
        """Test handling of special characters in attribute values"""
        data = {
            'name': ['Test™', 'Café', '日本語', 'Test\nNewline'],
            'geometry': [Point(i, i) for i in range(4)]
        }
        gdf = gpd.GeoDataFrame(data, crs='EPSG:4326')
        
        shp_path = os.path.join(temp_dir, 'special_chars.shp')
        gdf.to_file(shp_path)
        
        output_path = os.path.join(temp_dir, 'output.geojson')
        gdf_read = gpd.read_file(shp_path)
        gdf_read.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        assert len(result_gdf) == 4


class TestMetricsCollection:
    """Test metrics collection functionality"""
    
    def test_metrics_recorded(self, sample_point_shapefile, temp_dir):
        """Test that metrics are properly recorded"""
        shp_path, _ = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        metrics = MockMetricsCollector()
        
        # Simulate conversion with metrics
        metrics.record_conversion_start()
        gdf = gpd.read_file(shp_path)
        metrics.record_feature_count(len(gdf))
        gdf.to_file(output_path, driver='GeoJSON')
        metrics.record_conversion_success(1.0, {'test': 'data'})
        
        # Check metrics were recorded
        assert 'start' in metrics.events
        assert any(event[0] == 'feature_count' for event in metrics.events)
        assert any(event[0] == 'success' for event in metrics.events)
    
    def test_json_metrics_output(self, sample_point_shapefile, temp_dir):
        """Test JSON metrics output format"""
        metrics_file = os.path.join(temp_dir, 'metrics.jsonl')
        
        # Simulate JSON metrics collection
        with open(metrics_file, 'w') as f:
            metrics_data = {
                'timestamp': '2024-01-01 12:00:00',
                'feature_count': 3,
                'duration_seconds': 1.5,
                'input_size_mb': 0.001,
                'output_size_mb': 0.002
            }
            f.write(json.dumps(metrics_data) + '\n')
        
        # Verify JSON can be read back
        with open(metrics_file, 'r') as f:
            line = f.readline()
            data = json.loads(line)
            assert data['feature_count'] == 3
            assert data['duration_seconds'] == 1.5


class TestOutputFormat:
    """Test output GeoJSON format compliance"""
    
    def test_valid_geojson_structure(self, sample_point_shapefile, temp_dir):
        """Test that output is valid GeoJSON"""
        shp_path, _ = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf = gpd.read_file(shp_path)
        gdf.to_file(output_path, driver='GeoJSON')
        
        # Read as JSON and verify structure
        with open(output_path, 'r') as f:
            geojson = json.load(f)
        
        assert geojson['type'] == 'FeatureCollection'
        assert 'features' in geojson
        assert len(geojson['features']) == 3
        
        for feature in geojson['features']:
            assert feature['type'] == 'Feature'
            assert 'geometry' in feature
            assert 'properties' in feature
    
    def test_geojson_coordinates_format(self, sample_point_shapefile, temp_dir):
        """Test that coordinates are in correct format"""
        shp_path, _ = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf = gpd.read_file(shp_path)
        gdf.to_file(output_path, driver='GeoJSON')
        
        with open(output_path, 'r') as f:
            geojson = json.load(f)
        
        for feature in geojson['features']:
            coords = feature['geometry']['coordinates']
            assert isinstance(coords, list)
            assert len(coords) == 2  # [lon, lat] for points
            assert all(isinstance(c, (int, float)) for c in coords)


class TestRegressionBaseline:
    """Regression tests comparing against known good outputs"""
    
    def test_output_matches_baseline(self, sample_point_shapefile, temp_dir):
        """Test that output matches a known baseline"""
        shp_path, original_gdf = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        gdf = gpd.read_file(shp_path)
        gdf.to_file(output_path, driver='GeoJSON')
        
        result_gdf = gpd.read_file(output_path)
        
        # Compare key metrics
        baseline_metrics = {
            'feature_count': 3,
            'geometry_type': 'Point',
            'crs': 'EPSG:4326',
            'columns': ['name', 'value', 'geometry']
        }
        
        assert len(result_gdf) == baseline_metrics['feature_count']
        assert all(result_gdf.geometry.geom_type == baseline_metrics['geometry_type'])
        assert str(result_gdf.crs) == baseline_metrics['crs']
        assert set(result_gdf.columns) == set(baseline_metrics['columns'])


# Performance benchmarks (optional, requires pytest-benchmark)
class TestPerformance:
    """Performance regression tests"""
    
    def test_conversion_performance(self, sample_point_shapefile, temp_dir, benchmark):
        """Benchmark conversion performance"""
        shp_path, _ = sample_point_shapefile
        output_path = os.path.join(temp_dir, 'output.geojson')
        
        def convert():
            gdf = gpd.read_file(shp_path)
            gdf.to_file(output_path, driver='GeoJSON')
        
        # This will fail without pytest-benchmark installed
        # benchmark(convert)
        
        # Alternative: simple timing assertion
        import time
        start = time.time()
        convert()
        duration = time.time() - start
        
        # Assert conversion completes in reasonable time
        assert duration < 5.0  # Should complete in under 5 seconds


if __name__ == '__main__':
    pytest.main([__file__, '-v'])