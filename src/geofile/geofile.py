import geopandas as gpd
import argparse
import os
import time
import json
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

# Abstract metrics interface
class MetricsCollector(ABC):
    @abstractmethod
    def record_conversion_start(self):
        pass
    
    @abstractmethod
    def record_conversion_success(self, duration: float, metadata: Dict[str, Any]):
        pass
    
    @abstractmethod
    def record_conversion_failure(self, error: str):
        pass
    
    @abstractmethod
    def record_read_time(self, duration: float):
        pass
    
    @abstractmethod
    def record_write_time(self, duration: float):
        pass
    
    @abstractmethod
    def record_feature_count(self, count: int):
        pass
    
    @abstractmethod
    def record_file_sizes(self, input_mb: float, output_mb: float):
        pass

# Prometheus implementation
class PrometheusCollector(MetricsCollector):
    def __init__(self, port: int = 8000):
        from prometheus_client import Counter, Histogram, Gauge, start_http_server
        
        self.conversion_counter = Counter(
            'shapefile_conversions_total', 
            'Total number of shapefile conversions',
            ['status']
        )
        self.conversion_duration = Histogram(
            'shapefile_conversion_duration_seconds', 
            'Time taken to convert shapefile',
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
        )
        self.read_duration = Histogram(
            'shapefile_read_duration_seconds',
            'Time taken to read shapefile'
        )
        self.write_duration = Histogram(
            'shapefile_write_duration_seconds',
            'Time taken to write GeoJSON'
        )
        self.feature_count_gauge = Gauge(
            'shapefile_feature_count', 
            'Number of features in the shapefile'
        )
        self.input_size_gauge = Gauge(
            'shapefile_input_size_mb',
            'Input shapefile size in MB'
        )
        self.output_size_gauge = Gauge(
            'shapefile_output_size_mb', 
            'Output GeoJSON file size in MB'
        )
        
        start_http_server(port)
        print(f"Prometheus metrics available at http://localhost:{port}/metrics")
    
    def record_conversion_start(self):
        pass
    
    def record_conversion_success(self, duration: float, metadata: Dict[str, Any]):
        self.conversion_counter.labels(status='success').inc()
        self.conversion_duration.observe(duration)
    
    def record_conversion_failure(self, error: str):
        self.conversion_counter.labels(status='failure').inc()
    
    def record_read_time(self, duration: float):
        self.read_duration.observe(duration)
    
    def record_write_time(self, duration: float):
        self.write_duration.observe(duration)
    
    def record_feature_count(self, count: int):
        self.feature_count_gauge.set(count)
    
    def record_file_sizes(self, input_mb: float, output_mb: float):
        self.input_size_gauge.set(input_mb)
        self.output_size_gauge.set(output_mb)

# JSON logging implementation
class JsonLogCollector(MetricsCollector):
    def __init__(self, output_file: Optional[str] = None):
        self.output_file = output_file
        self.current_record = {}
    
    def _write_record(self, record: Dict[str, Any]):
        json_str = json.dumps(record)
        if self.output_file:
            with open(self.output_file, 'a') as f:
                f.write(json_str + '\n')
        else:
            print(json_str)
    
    def record_conversion_start(self):
        self.current_record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'event': 'conversion_start'
        }
    
    def record_conversion_success(self, duration: float, metadata: Dict[str, Any]):
        self.current_record.update({
            'event': 'conversion_success',
            'duration_seconds': duration,
            **metadata
        })
        self._write_record(self.current_record)
    
    def record_conversion_failure(self, error: str):
        self.current_record.update({
            'event': 'conversion_failure',
            'error': error
        })
        self._write_record(self.current_record)
    
    def record_read_time(self, duration: float):
        self.current_record['read_duration_seconds'] = duration
    
    def record_write_time(self, duration: float):
        self.current_record['write_duration_seconds'] = duration
    
    def record_feature_count(self, count: int):
        self.current_record['feature_count'] = count
    
    def record_file_sizes(self, input_mb: float, output_mb: float):
        self.current_record['input_size_mb'] = input_mb
        self.current_record['output_size_mb'] = output_mb

# Null collector (no metrics)
class NullCollector(MetricsCollector):
    def record_conversion_start(self): pass
    def record_conversion_success(self, duration: float, metadata: Dict[str, Any]): pass
    def record_conversion_failure(self, error: str): pass
    def record_read_time(self, duration: float): pass
    def record_write_time(self, duration: float): pass
    def record_feature_count(self, count: int): pass
    def record_file_sizes(self, input_mb: float, output_mb: float): pass

# StatsD implementation
class StatsDCollector(MetricsCollector):
    def __init__(self, host: str = 'localhost', port: int = 8125, prefix: str = 'shapefile'):
        try:
            from statsd import StatsClient
            self.client = StatsClient(host, port, prefix=prefix)
            print(f"StatsD metrics sending to {host}:{port}")
        except ImportError:
            print("statsd module not installed. Install with: pip install statsd")
            raise
    
    def record_conversion_start(self):
        pass
    
    def record_conversion_success(self, duration: float, metadata: Dict[str, Any]):
        self.client.incr('conversion.success')
        self.client.timing('conversion.duration', duration * 1000)  # milliseconds
    
    def record_conversion_failure(self, error: str):
        self.client.incr('conversion.failure')
    
    def record_read_time(self, duration: float):
        self.client.timing('read.duration', duration * 1000)
    
    def record_write_time(self, duration: float):
        self.client.timing('write.duration', duration * 1000)
    
    def record_feature_count(self, count: int):
        self.client.gauge('feature.count', count)
    
    def record_file_sizes(self, input_mb: float, output_mb: float):
        self.client.gauge('input.size_mb', input_mb)
        self.client.gauge('output.size_mb', output_mb)

def convert_shapefile(input_path, output_path=None, metrics: MetricsCollector = None):
    """
    Convert a shapefile to GeoJSON with optional metrics collection.
    
    Args:
        input_path: Full path to the input .shp file
        output_path: Full path to output .geojson file (optional)
        metrics: MetricsCollector instance for recording metrics
    """
    if metrics is None:
        metrics = NullCollector()
    
    metrics.record_conversion_start()
    total_start = time.time()
    
    try:
        # Generate output path if not provided
        if output_path is None:
            input_file = Path(input_path)
            output_path = input_file.with_suffix('.geojson')
        
        # Record input file size
        input_size_mb = os.path.getsize(input_path) / 1024 / 1024
        
        # Read shapefile
        read_start = time.time()
        gdf = gpd.read_file(input_path)
        read_time = time.time() - read_start
        metrics.record_read_time(read_time)
        
        # Record feature count
        feature_count = len(gdf)
        metrics.record_feature_count(feature_count)
        
        print(f"Read {feature_count} features in {read_time:.2f}s")
        print(f"CRS: {gdf.crs}")
        print(f"Geometry types: {gdf.geometry.type.value_counts().to_dict()}")
        
        # Write GeoJSON
        write_start = time.time()
        gdf.to_file(output_path, driver='GeoJSON')
        write_time = time.time() - write_start
        metrics.record_write_time(write_time)
        
        # Record output file size
        output_size_mb = os.path.getsize(output_path) / 1024 / 1024
        metrics.record_file_sizes(input_size_mb, output_size_mb)
        
        # Record total duration
        total_time = time.time() - total_start
        
        metadata = {
            'input_file': str(input_path),
            'output_file': str(output_path),
            'feature_count': feature_count,
            'input_size_mb': input_size_mb,
            'output_size_mb': output_size_mb,
            'crs': str(gdf.crs)
        }
        metrics.record_conversion_success(total_time, metadata)
        
        print(f"Wrote GeoJSON in {write_time:.2f}s")
        print(f"Total conversion time: {total_time:.2f}s")
        print(f"Output file: {output_path} ({output_size_mb:.2f} MB)")
        
        return True
        
    except Exception as e:
        metrics.record_conversion_failure(str(e))
        print(f"Error during conversion: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(
        description='Convert shapefile to GeoJSON with optional metrics'
    )
    parser.add_argument(
        'input',
        help='Path to input shapefile (e.g., AZ649/spatial/soilmu_a_az649.shp)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Path to output GeoJSON file (optional)'
    )
    parser.add_argument(
        '--metrics',
        choices=['none', 'prometheus', 'json', 'statsd'],
        default='none',
        help='Metrics backend to use (default: none)'
    )
    parser.add_argument(
        '--metrics-port',
        type=int,
        default=8000,
        help='Port for Prometheus metrics server (default: 8000)'
    )
    parser.add_argument(
        '--metrics-file',
        help='Output file for JSON metrics'
    )
    parser.add_argument(
        '--statsd-host',
        default='localhost',
        help='StatsD host (default: localhost)'
    )
    parser.add_argument(
        '--statsd-port',
        type=int,
        default=8125,
        help='StatsD port (default: 8125)'
    )
    
    args = parser.parse_args()
    
    # Create appropriate metrics collector
    if args.metrics == 'prometheus':
        try:
            metrics = PrometheusCollector(port=args.metrics_port)
        except ImportError:
            print("prometheus-client not installed. Install with: pip install prometheus-client")
            return
    elif args.metrics == 'json':
        metrics = JsonLogCollector(output_file=args.metrics_file)
        print(f"JSON metrics will be {'written to ' + args.metrics_file if args.metrics_file else 'printed to console'}")
    elif args.metrics == 'statsd':
        try:
            metrics = StatsDCollector(host=args.statsd_host, port=args.statsd_port)
        except ImportError:
            return
    else:
        metrics = NullCollector()
    
    # Convert the file
    convert_shapefile(args.input, args.output, metrics)

if __name__ == "__main__":
    main()