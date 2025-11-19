"""
Performance tests for Filter Presets functionality
Tests <300ms preset application time requirement
"""

import pytest
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, patch


class TestPresetPerformance:
    """Performance tests for filter preset operations"""

    def test_localstorage_performance_simulation(self):
        """Simulate localStorage performance for preset operations"""

        # Simulate localStorage operations with different data sizes
        test_data_sizes = [1, 5, 10, 20, 50]  # Number of presets
        preset_application_times = []

        for num_presets in test_data_sizes:
            # Create test data
            preset_data = {
                'tab_presets': {
                    'test_tab': []
                }
            }

            # Generate presets
            for i in range(num_presets):
                preset_data['tab_presets']['test_tab'].append({
                    'name': f'Preset {i}',
                    'filters': {
                        'search_term': f'search term {i} with some additional text to simulate realistic filter data',
                        'category': f'Category {i}',
                        'date_range': 'last_30_days',
                        'source': f'source_{i}'
                    },
                    'created_at': '2025-01-16T10:00:00Z',
                    'updated_at': '2025-01-16T10:00:00Z'
                })

            # Simulate JSON serialization/deserialization time
            start_time = time.perf_counter()

            # Simulate localStorage read
            serialized_data = __import__('json').dumps(preset_data)
            deserialized_data = __import__('json').loads(serialized_data)

            # Simulate finding and applying specific preset
            target_preset = deserialized_data['tab_presets']['test_tab'][0]
            filters_to_apply = target_preset['filters']

            # Simulate applying filters to UI components
            applied_filters = {}
            for key, value in filters_to_apply.items():
                applied_filters[key] = value

            end_time = time.perf_counter()

            operation_time = (end_time - start_time) * 1000  # Convert to milliseconds
            preset_application_times.append(operation_time)

            # Performance requirement: <300ms
            assert operation_time < 300, f"Preset application with {num_presets} presets took {operation_time:.2f}ms, expected <300ms"

        # Analyze performance across different data sizes
        avg_time = statistics.mean(preset_application_times)
        max_time = max(preset_application_times)

        print(f"Performance Summary:")
        print(f"Average preset application time: {avg_time:.2f}ms")
        print(f"Maximum preset application time: {max_time:.2f}ms")
        print(f"Time range: {min(preset_application_times):.2f}ms - {max(preset_application_times):.2f}ms")

        # Overall performance assertion
        assert avg_time < 200, f"Average preset application time {avg_time:.2f}ms exceeds 200ms target"
        assert max_time < 300, f"Maximum preset application time {max_time:.2f}ms exceeds 300ms requirement"

    def test_preset_storage_overhead(self):
        """Test storage overhead and memory usage"""

        # Calculate storage requirements for different numbers of presets
        test_cases = [1, 5, 10, 20, 50]  # Maximum is 10, but test higher for performance analysis

        for num_presets in test_cases:
            preset_data = []

            for i in range(num_presets):
                preset_data.append({
                    'name': f'Performance Test Preset {i}',
                    'filters': {
                        'search_term': f'Complex search term with multiple keywords term{i} term{i+1} term{i+2}',
                        'category': f'Advanced Category {i}',
                        'date_range': 'custom_date_range_with_start_and_end_dates',
                        'source': f'multiple_source_selection_{i}',
                        'additional_filter_1': f'extra_filter_data_{i}',
                        'additional_filter_2': f'more_filter_options_{i}'
                    },
                    'created_at': '2025-01-16T10:00:00Z',
                    'updated_at': '2025-01-16T10:00:00Z'
                })

            # Calculate storage size
            serialized_data = __import__('json').dumps(preset_data)
            storage_size_bytes = len(serialized_data.encode('utf-8'))
            storage_size_kb = storage_size_bytes / 1024

            print(f"Storage usage for {num_presets} presets: {storage_size_kb:.2f} KB")

            # Storage should be reasonable (even 50 presets should be <50KB)
            assert storage_size_kb < 50, f"Storage for {num_presets} presets ({storage_size_kb:.2f}KB) exceeds 50KB limit"

            # For the actual limit (10 presets), storage should be minimal
            if num_presets == 10:
                assert storage_size_kb < 10, f"Storage for 10 presets ({storage_size_kb:.2f}KB) exceeds 10KB expectation"

    def test_filter_preset_component_creation_performance(self):
        """Test performance of creating FilterPresetsComponent instances"""

        from src.web.dashboard.components.filter_presets import FilterPresetsComponent

        # Test component creation time
        creation_times = []

        for i in range(100):  # Test 100 iterations
            start_time = time.perf_counter()

            filter_inputs = {
                'search_term': f'test-search-input-{i}',
                'category': f'test-category-dropdown-{i}',
                'date_range': f'test-date-range-{i}'
            }

            component = FilterPresetsComponent(f'test_tab_{i}', filter_inputs)
            controls = component.create_preset_controls()

            end_time = time.perf_counter()
            creation_time = (end_time - start_time) * 1000
            creation_times.append(creation_time)

        avg_creation_time = statistics.mean(creation_times)
        max_creation_time = max(creation_times)

        print(f"Component Creation Performance:")
        print(f"Average creation time: {avg_creation_time:.2f}ms")
        print(f"Maximum creation time: {max_creation_time:.2f}ms")

        # Component creation should be fast (<10ms average)
        assert avg_creation_time < 10, f"Average component creation time {avg_creation_time:.2f}ms exceeds 10ms"
        assert max_creation_time < 50, f"Maximum component creation time {max_creation_time:.2f}ms exceeds 50ms"

    def test_callback_generation_performance(self):
        """Test performance of generating clientside callbacks"""

        from src.web.dashboard.components.filter_presets import FilterPresetsComponent

        callback_generation_times = []

        for i in range(50):  # Test 50 iterations
            start_time = time.perf_counter()

            filter_inputs = {
                'search_term': f'search-{i}',
                'category': f'category-{i}',
                'source': f'source-{i}'
            }

            component = FilterPresetsComponent(f'tab_{i}', filter_inputs)
            callbacks = component.get_clientside_callbacks()

            end_time = time.perf_counter()
            generation_time = (end_time - start_time) * 1000
            callback_generation_times.append(generation_time)

        avg_generation_time = statistics.mean(callback_generation_times)
        max_generation_time = max(callback_generation_times)

        print(f"Callback Generation Performance:")
        print(f"Average generation time: {avg_generation_time:.2f}ms")
        print(f"Maximum generation time: {max_generation_time:.2f}ms")

        # Callback generation should be very fast (<5ms average)
        assert avg_generation_time < 5, f"Average callback generation time {avg_generation_time:.2f}ms exceeds 5ms"
        assert max_generation_time < 20, f"Maximum callback generation time {max_generation_time:.2f}ms exceeds 20ms"

    def test_preset_application_with_large_filter_data(self):
        """Test preset application performance with large filter data"""

        # Create preset with large filter data
        large_filter_data = {
            'search_term': ' '.join([f'keyword{i}' for i in range(100)]),  # 100 keywords
            'category': 'Very Long Category Name with Multiple Words and Special Characters',
            'description': 'A' * 1000,  # 1000 character description
            'tags': ['tag' + str(i) for i in range(50)],  # 50 tags
            'metadata': {
                'custom_field_' + str(i): f'value_{i}' * 10 for i in range(20)  # 20 custom fields with long values
            }
        }

        # Test applying large preset data
        application_times = []

        for i in range(10):
            start_time = time.perf_counter()

            # Simulate preset application
            serialized_preset = __import__('json').dumps({
                'name': f'Large Preset {i}',
                'filters': large_filter_data,
                'created_at': '2025-01-16T10:00:00Z',
                'updated_at': '2025-01-16T10:00:00Z'
            })

            deserialized_preset = __import__('json').loads(serialized_preset)
            applied_filters = deserialized_preset['filters']

            # Simulate applying each filter to UI
            for key, value in applied_filters.items():
                # Simulate UI update operation
                processed_value = value if not isinstance(value, list) else value[:10]  # Limit list processing
                assert processed_value is not None

            end_time = time.perf_counter()
            application_time = (end_time - start_time) * 1000
            application_times.append(application_time)

        avg_time = statistics.mean(application_times)
        max_time = max(application_times)

        print(f"Large Filter Data Performance:")
        print(f"Average application time: {avg_time:.2f}ms")
        print(f"Maximum application time: {max_time:.2f}ms")

        # Even with large data, should be under 300ms
        assert avg_time < 200, f"Average large data preset application {avg_time:.2f}ms exceeds 200ms"
        assert max_time < 300, f"Maximum large data preset application {max_time:.2f}ms exceeds 300ms requirement"

    def test_concurrent_preset_operations(self):
        """Test performance of concurrent preset operations"""

        import threading
        import queue

        # Simulate concurrent preset operations
        results = queue.Queue()

        def simulate_preset_operation(operation_id: int):
            """Simulate a preset save/load operation"""
            start_time = time.perf_counter()

            # Simulate operation
            preset_data = {
                'name': f'Concurrent Preset {operation_id}',
                'filters': {
                    'search_term': f'search_{operation_id}',
                    'category': f'category_{operation_id}'
                },
                'created_at': '2025-01-16T10:00:00Z'
            }

            # Simulate localStorage operations
            serialized = __import__('json').dumps(preset_data)
            deserialized = __import__('json').loads(serialized)

            end_time = time.perf_counter()
            operation_time = (end_time - start_time) * 1000
            results.put(operation_time)

        # Run 20 concurrent operations
        threads = []
        start_time = time.perf_counter()

        for i in range(20):
            thread = threading.Thread(target=simulate_preset_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all operations to complete
        for thread in threads:
            thread.join()

        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000

        # Collect results
        operation_times = []
        while not results.empty():
            operation_times.append(results.get())

        avg_operation_time = statistics.mean(operation_times)
        max_operation_time = max(operation_times)

        print(f"Concurrent Operations Performance:")
        print(f"Total time for 20 concurrent operations: {total_time:.2f}ms")
        print(f"Average individual operation time: {avg_operation_time:.2f}ms")
        print(f"Maximum individual operation time: {max_operation_time:.2f}ms")

        # Concurrent operations should still be reasonably fast
        assert total_time < 1000, f"Total concurrent operation time {total_time:.2f}ms exceeds 1000ms"
        assert avg_operation_time < 100, f"Average concurrent operation time {avg_operation_time:.2f}ms exceeds 100ms"


if __name__ == '__main__':
    pytest.main([__file__])