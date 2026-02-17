"""
Profiling module to measure function execution times and identify performance bottlenecks.
Logs per-call times and aggregated statistics for analysis.
"""

import time
import functools
import threading
from collections import defaultdict
from pathlib import Path

class Profiler:
    """Tracks function execution times with thread-safe logging."""
    
    def __init__(self, log_file="profiling_results.txt"):
        self.log_file = Path(log_file)
        self.stats = defaultdict(lambda: {"count": 0, "total": 0.0, "min": float('inf'), "max": 0.0})
        self.lock = threading.Lock()
        # Write header
        with open(self.log_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("CaddyMate Performance Profiling Results\n")
            f.write("=" * 80 + "\n\n")
    
    def profile_function(self, func):
        """Decorator to profile a function's execution time."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to milliseconds
            
            with self.lock:
                stats = self.stats[func.__name__]
                stats["count"] += 1
                stats["total"] += elapsed
                stats["min"] = min(stats["min"], elapsed)
                stats["max"] = max(stats["max"], elapsed)
                
                # Log individual call
                avg = stats["total"] / stats["count"]
                self._log_call(func.__name__, elapsed, stats["count"], avg, stats["min"], stats["max"])
            
            return result
        return wrapper
    
    def profile_context(self, name):
        """Context manager to profile a code block."""
        return _ProfileContext(self, name)
    
    def _log_call(self, func_name, elapsed_ms, call_count, avg_ms, min_ms, max_ms):
        """Write per-call and aggregated stats to log file."""
        with open(self.log_file, 'a') as f:
            f.write(f"[{func_name}] Call #{call_count}: {elapsed_ms:.3f}ms | "
                   f"Avg: {avg_ms:.3f}ms | Min: {min_ms:.3f}ms | Max: {max_ms:.3f}ms\n")
    
    def print_summary(self):
        """Print summary statistics to console and file."""
        summary = "\n" + "=" * 80 + "\nSUMMARY STATISTICS\n" + "=" * 80 + "\n"
        
        # Sort by total time (descending)
        sorted_stats = sorted(
            self.stats.items(),
            key=lambda x: x[1]["total"],
            reverse=True
        )
        
        summary += f"{'Function':<30} {'Calls':<8} {'Total (ms)':<12} {'Avg (ms)':<12} {'Min (ms)':<12} {'Max (ms)':<12}\n"
        summary += "-" * 80 + "\n"
        
        for func_name, stats in sorted_stats:
            avg = stats["total"] / stats["count"]
            summary += (f"{func_name:<30} {stats['count']:<8} {stats['total']:<12.3f} "
                       f"{avg:<12.3f} {stats['min']:<12.3f} {stats['max']:<12.3f}\n")
        
        print(summary)
        with open(self.log_file, 'a') as f:
            f.write(summary)
    
    def reset(self):
        """Clear all profiling data."""
        with self.lock:
            self.stats.clear()


class _ProfileContext:
    """Context manager for profiling code blocks."""
    
    def __init__(self, profiler, name):
        self.profiler = profiler
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        elapsed = (time.perf_counter() - self.start_time) * 1000
        with self.profiler.lock:
            stats = self.profiler.stats[self.name]
            stats["count"] += 1
            stats["total"] += elapsed
            stats["min"] = min(stats["min"], elapsed)
            stats["max"] = max(stats["max"], elapsed)
            self.profiler._log_call(self.name, elapsed, stats["count"], 
                                    stats["total"] / stats["count"], 
                                    stats["min"], stats["max"])


# Global profiler instance
_profiler = Profiler()

def profile(func):
    """Convenience decorator using global profiler."""
    return _profiler.profile_function(func)

@functools.lru_cache(maxsize=1)
def get_profiler():
    """Get the global profiler instance."""
    return _profiler
