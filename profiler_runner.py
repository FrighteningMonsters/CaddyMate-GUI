"""
Profiling runner script.
Run this to capture performance metrics and identify bottlenecks.

Usage:
    python profiler_runner.py

The script will:
1. Start the GUI with profiling enabled
2. Collect timing data for critical functions
3. Generate a profiling_results.txt file when the GUI closes
4. Display performance summary with function execution times
"""

import sys
import time
import tkinter as tk
from profiler import get_profiler

# Import after profiler is available
from ui import CaddyMateUI


def main():
    """Initialize and run the profiled GUI."""
    print("=" * 80)
    print("Performance Profiling Session")
    print("=" * 80)
    print("\nStarting GUI with profiling enabled...")
    print("Profiling data will be logged to: profiling_results.txt")
    print("\nKey functions being monitored:")
    print("  - theta_star() : Pathfinding algorithm")
    print("  - draw_robot() : Robot rendering")
    print("  - draw_path() : Path rendering")
    print("  - update_visuals() : Visual update loop")
    print("  - poll_position_update() : Position polling loop")
    print("  - draw_grid_shelves : Initial grid drawing")
    print("  - draw_aisle_labels : Aisle label rendering")
    print("\nClose the window when done to see the profiling summary.\n")

    root = tk.Tk()
    root.after(500, lambda: root.attributes('-fullscreen', True))

    def toggle_fullscreen(event=None):
        current = root.attributes('-fullscreen')
        root.attributes('-fullscreen', not current)

    root.bind('<f>', toggle_fullscreen)
    root.bind('<Escape>', lambda e: root.destroy())  # ESC to quit

    # Start the UI
    CaddyMateUI(root)

    # Schedule summary on window close
    def on_close():
        print("\n\nGenerating profiling summary...\n")
        profiler = get_profiler()
        profiler.print_summary()
        print("\nProfiling data saved to: profiling_results.txt")
        print("Check the file for detailed per-call timings.")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n\nProfiling interrupted.")
        profiler = get_profiler()
        profiler.print_summary()


if __name__ == "__main__":
    main()
