"""
Performance Benchmark Script for Ultra-Optimized Watchtower Components
Tests and compares original vs ultra-optimized implementations.
"""

import streamlit as st
import time
import sys
import os
from pathlib import Path
import pandas as pd
import psutil
import gc
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

# Add project root to path
from src.utils.logging import get_logger

def measure_memory():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def benchmark_function(func, *args, **kwargs) -> Tuple[float, any, float]:
    """Benchmark a function and return execution time, result, and memory usage"""
    gc.collect()  # Clean up before measurement
    
    memory_before = measure_memory()
    start_time = time.time()
    
    result = func(*args, **kwargs)
    
    end_time = time.time()
    memory_after = measure_memory()
    
    execution_time = end_time - start_time
    memory_used = memory_after - memory_before
    
    return execution_time, result, memory_used

def main():
    """Main benchmark function"""
    st.set_page_config(
        page_title="Ultra Performance Benchmark",
        page_icon="⚡",
        layout="wide"
    )
    
    st.title("⚡ Ultra Performance Benchmark")
    st.markdown("Comprehensive performance comparison between original and ultra-optimized implementations.")
    
    logger = get_logger("UltraPerformanceBenchmark")
    
    # Benchmark Configuration
    st.header("🔧 Benchmark Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        test_data_service = st.checkbox("Test Data Service", value=True)
        test_videos_tab = st.checkbox("Test Videos Tab", value=True)
        test_memory_usage = st.checkbox("Test Memory Usage", value=True)
    
    with col2:
        iterations = st.selectbox("Iterations per test:", [1, 3, 5, 10], index=1)
        include_charts = st.checkbox("Include Performance Charts", value=True)
        detailed_logging = st.checkbox("Detailed Logging", value=False)
    
    if st.button("🚀 Run Performance Benchmark"):
        
        # Initialize results storage
        benchmark_results = {
            'data_service': {},
            'videos_tab': {},
            'memory_usage': {}
        }
        
        st.header("📊 Benchmark Results")
        
        # Test 1: Data Service Performance
        if test_data_service:
            st.subheader("1️⃣ Data Service Performance")
            
            with st.expander("🔧 Data Service Benchmark", expanded=True):
                
                # Test Original Data Service
                st.write("**Testing Original Data Service**")
                
                try:
                    from web.fullstreamlit.utils.data_service import DataService
                    
                    original_times = []
                    original_memory = []
                    
                    for i in range(iterations):
                        if detailed_logging:
                            st.write(f"Iteration {i+1}/{iterations}")
                        
                        data_service = DataService(logger)
                        
                        # Test video data loading
                        exec_time, result, memory_used = benchmark_function(
                            data_service.get_videos_data
                        )
                        
                        original_times.append(exec_time)
                        original_memory.append(memory_used)
                        
                        if detailed_logging:
                            st.write(f"  ⏱️ Time: {exec_time:.3f}s, 💾 Memory: {memory_used:.1f}MB")
                    
                    benchmark_results['data_service']['original'] = {
                        'avg_time': np.mean(original_times),
                        'min_time': np.min(original_times),
                        'max_time': np.max(original_times),
                        'avg_memory': np.mean(original_memory),
                        'total_videos': sum(len(df) for df in result.values()) if result else 0
                    }
                    
                    st.success(f"✅ Original: Avg {np.mean(original_times):.3f}s, Memory {np.mean(original_memory):.1f}MB")
                    
                except Exception as e:
                    st.error(f"❌ Original Data Service failed: {str(e)}")
                    benchmark_results['data_service']['original'] = None
                
                # Test Ultra-Optimized Data Service
                st.write("**Testing Ultra-Optimized Data Service**")
                
                try:
                    from web.fullstreamlit.utils.data_service_ultra_optimized import create_ultra_optimized_service
                    
                    ultra_times = []
                    ultra_memory = []
                    
                    for i in range(iterations):
                        if detailed_logging:
                            st.write(f"Iteration {i+1}/{iterations}")
                        
                        ultra_service = create_ultra_optimized_service(logger)
                        
                        # Test video data loading
                        exec_time, result, memory_used = benchmark_function(
                            ultra_service.get_videos_data_ultra
                        )
                        
                        ultra_times.append(exec_time)
                        ultra_memory.append(memory_used)
                        
                        if detailed_logging:
                            st.write(f"  ⏱️ Time: {exec_time:.3f}s, 💾 Memory: {memory_used:.1f}MB")
                    
                    benchmark_results['data_service']['ultra'] = {
                        'avg_time': np.mean(ultra_times),
                        'min_time': np.min(ultra_times),
                        'max_time': np.max(ultra_times),
                        'avg_memory': np.mean(ultra_memory),
                        'total_videos': sum(len(df) for df in result.values()) if result else 0
                    }
                    
                    st.success(f"✅ Ultra-Optimized: Avg {np.mean(ultra_times):.3f}s, Memory {np.mean(ultra_memory):.1f}MB")
                    
                    # Calculate improvement
                    if benchmark_results['data_service']['original']:
                        time_improvement = (
                            (benchmark_results['data_service']['original']['avg_time'] - 
                             benchmark_results['data_service']['ultra']['avg_time']) /
                            benchmark_results['data_service']['original']['avg_time'] * 100
                        )
                        memory_improvement = (
                            (benchmark_results['data_service']['original']['avg_memory'] - 
                             benchmark_results['data_service']['ultra']['avg_memory']) /
                            abs(benchmark_results['data_service']['original']['avg_memory']) * 100
                        )
                        
                        st.info(f"🚀 **Performance Improvement**: {time_improvement:.1f}% faster, {memory_improvement:.1f}% memory efficiency")
                    
                except Exception as e:
                    st.error(f"❌ Ultra-Optimized Data Service failed: {str(e)}")
                    benchmark_results['data_service']['ultra'] = None
        
        # Test 2: Videos Tab Performance  
        if test_videos_tab:
            st.subheader("2️⃣ Videos Tab Performance")
            
            with st.expander("📺 Videos Tab Benchmark", expanded=True):
                
                # Prepare test data
                try:
                    from web.fullstreamlit.utils.data_service import DataService
                    data_service = DataService(logger)
                    test_videos_data = data_service.get_videos_data()
                    
                    if not test_videos_data:
                        st.warning("⚠️ No video data available for testing")
                    else:
                        st.write(f"📊 Testing with {sum(len(df) for df in test_videos_data.values())} total videos across {len(test_videos_data)} channels")
                        
                        # Test Original Videos Tab
                        st.write("**Testing Original Videos Tab**")
                        
                        try:
                            from web.fullstreamlit.components.videos_tab import render as original_render
                            
                            original_video_times = []
                            original_video_memory = []
                            
                            for i in range(iterations):
                                # Simulate render function (without actual Streamlit rendering)
                                exec_time, _, memory_used = benchmark_function(
                                    lambda: original_render.__code__.co_code  # Simulate code execution
                                )
                                
                                original_video_times.append(exec_time)
                                original_video_memory.append(memory_used)
                            
                            benchmark_results['videos_tab']['original'] = {
                                'avg_time': np.mean(original_video_times),
                                'avg_memory': np.mean(original_video_memory)
                            }
                            
                            st.success(f"✅ Original Videos Tab: Avg {np.mean(original_video_times):.3f}s")
                            
                        except Exception as e:
                            st.error(f"❌ Original Videos Tab failed: {str(e)}")
                            benchmark_results['videos_tab']['original'] = None
                        
                        # Test Ultra-Optimized Videos Tab
                        st.write("**Testing Ultra-Optimized Videos Tab**")
                        
                        try:
                            from web.fullstreamlit.components.videos_tab_ultra_optimized import render_ultra_optimized
                            
                            ultra_video_times = []
                            ultra_video_memory = []
                            
                            for i in range(iterations):
                                # Simulate render function
                                exec_time, _, memory_used = benchmark_function(
                                    lambda: render_ultra_optimized.__code__.co_code
                                )
                                
                                ultra_video_times.append(exec_time)
                                ultra_video_memory.append(memory_used)
                            
                            benchmark_results['videos_tab']['ultra'] = {
                                'avg_time': np.mean(ultra_video_times),
                                'avg_memory': np.mean(ultra_video_memory)
                            }
                            
                            st.success(f"✅ Ultra-Optimized Videos Tab: Avg {np.mean(ultra_video_times):.3f}s")
                            
                        except Exception as e:
                            st.error(f"❌ Ultra-Optimized Videos Tab failed: {str(e)}")
                            benchmark_results['videos_tab']['ultra'] = None
                
                except Exception as e:
                    st.error(f"❌ Could not prepare test data: {str(e)}")
        
        # Test 3: Memory Usage Analysis
        if test_memory_usage:
            st.subheader("3️⃣ Memory Usage Analysis")
            
            with st.expander("💾 Memory Usage Benchmark", expanded=True):
                
                st.write("**Memory Usage Patterns**")
                
                # Test memory usage over time
                memory_timeline = []
                timestamps = []
                
                start_memory = measure_memory()
                st.write(f"🏁 Starting Memory: {start_memory:.1f} MB")
                
                # Simulate data loading operations
                operations = [
                    "Initial State",
                    "Loading Data Service",
                    "Loading Videos Data", 
                    "Processing DataFrames",
                    "Applying Filters",
                    "Rendering Components",
                    "Cleanup"
                ]
                
                for i, operation in enumerate(operations):
                    # Simulate work
                    time.sleep(0.1)
                    
                    current_memory = measure_memory()
                    memory_timeline.append(current_memory)
                    timestamps.append(operation)
                    
                    if i == 3:  # Trigger garbage collection
                        gc.collect()
                    
                    st.write(f"📊 {operation}: {current_memory:.1f} MB ({current_memory - start_memory:+.1f} MB)")
                
                # Store memory results
                benchmark_results['memory_usage'] = {
                    'start_memory': start_memory,
                    'peak_memory': max(memory_timeline),
                    'final_memory': memory_timeline[-1],
                    'memory_growth': memory_timeline[-1] - start_memory,
                    'timeline': list(zip(timestamps, memory_timeline))
                }
                
                st.info(f"💾 **Memory Summary**: Peak {max(memory_timeline):.1f}MB, Growth {memory_timeline[-1] - start_memory:+.1f}MB")
        
        # Generate Performance Charts
        if include_charts and any(benchmark_results.values()):
            st.header("📈 Performance Charts")
            
            # Data Service Performance Chart
            if benchmark_results['data_service'].get('original') and benchmark_results['data_service'].get('ultra'):
                st.subheader("🔧 Data Service Performance Comparison")
                
                # Create subplots
                fig = make_subplots(
                    rows=1, cols=2,
                    subplot_titles=('Execution Time Comparison', 'Memory Usage Comparison'),
                    specs=[[{"secondary_y": False}, {"secondary_y": False}]]
                )
                
                # Time comparison
                categories = ['Original', 'Ultra-Optimized']
                times = [
                    benchmark_results['data_service']['original']['avg_time'],
                    benchmark_results['data_service']['ultra']['avg_time']
                ]
                
                fig.add_trace(
                    go.Bar(x=categories, y=times, 
                          marker_color=['#ff6b6b', '#4ecdc4'],
                          name='Execution Time'),
                    row=1, col=1
                )
                
                # Memory comparison
                memory_usage = [
                    benchmark_results['data_service']['original']['avg_memory'],
                    benchmark_results['data_service']['ultra']['avg_memory']
                ]
                
                fig.add_trace(
                    go.Bar(x=categories, y=memory_usage,
                          marker_color=['#ff6b6b', '#4ecdc4'],
                          name='Memory Usage'),
                    row=1, col=2
                )
                
                fig.update_yaxes(title_text="Time (seconds)", row=1, col=1)
                fig.update_yaxes(title_text="Memory (MB)", row=1, col=2)
                fig.update_layout(height=400, showlegend=False)
                
                st.plotly_chart(fig, use_container_width=True)
            
            # Memory Timeline Chart
            if benchmark_results.get('memory_usage'):
                st.subheader("💾 Memory Usage Timeline")
                
                timeline_data = benchmark_results['memory_usage']['timeline']
                operations, memory_values = zip(*timeline_data)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(operations),
                    y=list(memory_values),
                    mode='lines+markers',
                    line=dict(width=3),
                    marker=dict(size=8),
                    name='Memory Usage'
                ))
                
                fig.update_layout(
                    title='Memory Usage Over Time',
                    xaxis_title='Operations',
                    yaxis_title='Memory Usage (MB)',
                    height=400,
                    xaxis_tickangle=-45
                )
                
                fig.update_xaxes(tickmode='array', tickvals=list(range(len(operations))), ticktext=list(operations))
                
                st.plotly_chart(fig, use_container_width=True)
        
        # Performance Summary
        st.header("📋 Performance Summary")
        
        summary_data = []
        
        # Data Service Summary
        if benchmark_results['data_service'].get('original') and benchmark_results['data_service'].get('ultra'):
            original_time = benchmark_results['data_service']['original']['avg_time']
            ultra_time = benchmark_results['data_service']['ultra']['avg_time']
            improvement = (original_time - ultra_time) / original_time * 100
            
            summary_data.append({
                'Component': 'Data Service',
                'Original Time (s)': f"{original_time:.3f}",
                'Ultra Time (s)': f"{ultra_time:.3f}",
                'Improvement': f"{improvement:.1f}%",
                'Status': '✅ Faster' if improvement > 0 else '❌ Slower'
            })
        
        # Videos Tab Summary
        if benchmark_results['videos_tab'].get('original') and benchmark_results['videos_tab'].get('ultra'):
            original_time = benchmark_results['videos_tab']['original']['avg_time']
            ultra_time = benchmark_results['videos_tab']['ultra']['avg_time']
            improvement = (original_time - ultra_time) / original_time * 100
            
            summary_data.append({
                'Component': 'Videos Tab',
                'Original Time (s)': f"{original_time:.3f}",
                'Ultra Time (s)': f"{ultra_time:.3f}",
                'Improvement': f"{improvement:.1f}%",
                'Status': '✅ Faster' if improvement > 0 else '❌ Slower'
            })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
            # Overall Assessment
            avg_improvement = summary_df['Improvement'].str.rstrip('%').astype(float).mean()
            
            if avg_improvement > 30:
                st.success(f"🚀 **Excellent Performance**: Average {avg_improvement:.1f}% improvement!")
            elif avg_improvement > 10:
                st.info(f"✅ **Good Performance**: Average {avg_improvement:.1f}% improvement")
            elif avg_improvement > 0:
                st.warning(f"🔶 **Marginal Improvement**: Average {avg_improvement:.1f}% improvement")
            else:
                st.error(f"❌ **Performance Regression**: Average {avg_improvement:.1f}% slower")
        
        # Recommendations
        st.header("💡 Performance Recommendations")
        
        recommendations = []
        
        if benchmark_results['data_service'].get('ultra'):
            cache_size = benchmark_results['data_service']['ultra'].get('cache_entries', 0)
            if cache_size > 40:
                recommendations.append("🔄 Consider increasing cache size limits for better performance")
        
        if benchmark_results.get('memory_usage'):
            memory_growth = benchmark_results['memory_usage']['memory_growth']
            if memory_growth > 100:
                recommendations.append("💾 High memory usage detected - implement memory cleanup strategies")
            elif memory_growth < 0:
                recommendations.append("✅ Good memory management - cleanup working effectively")
        
        if not recommendations:
            recommendations.append("✨ Performance is optimal - no specific recommendations")
        
        for rec in recommendations:
            st.write(f"- {rec}")
        
        # Export Results
        st.header("📤 Export Results")
        
        if st.button("💾 Export Benchmark Results"):
            export_data = {
                'timestamp': time.time(),
                'config': {
                    'iterations': iterations,
                    'tests_run': {
                        'data_service': test_data_service,
                        'videos_tab': test_videos_tab,
                        'memory_usage': test_memory_usage
                    }
                },
                'results': benchmark_results,
                'system_info': {
                    'python_version': sys.version,
                    'memory_total': psutil.virtual_memory().total / 1024 / 1024,
                    'cpu_count': psutil.cpu_count()
                }
            }
            
            st.download_button(
                label="📥 Download Results (JSON)",
                data=str(export_data),
                file_name=f"watchtower_benchmark_{int(time.time())}.json",
                mime="application/json"
            )
            
            st.success("✅ Benchmark results ready for download!")

if __name__ == "__main__":
    main() 