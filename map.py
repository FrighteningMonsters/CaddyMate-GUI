import tkinter as tk
import heapq
import math
import json
import socket
import threading
import time
from styles import SECONDARY, TEXT
from profiler import profile

CELL_SIZE = 30 # pixels per grid cell

# UDP Pose Configuration
UDP_HOST = "0.0.0.0"
UDP_PORT = 5005
UDP_BUFFER_BYTES = 1024
THETA_IN_DEGREES = True
THETA_OFFSET_DEGREES = 90.0

# Performance Tuning
DRAW_INTERVAL_MS = 33
PATH_RECALC_INTERVAL_S = 1.0
CAMERA_SMOOTHING = 0.12
POSE_EPSILON = 0.02
THETA_EPSILON = 0.01

# Map Configuration
AISLE_ROWS = 2

def generate_map(num_aisles, num_rows):
    """
    Generates a grid representation of the store layout.
    """
    SHELF_WIDTH = 2
    SHELF_HEIGHT = 8
    SHELF_SPACING_X = 5  # Distance from start of one shelf to start of next (3 to 8)
    
    START_X = 3
    ROW_1_Y = 3
    ROW_2_Y = 16
    
    SHELVES_PER_ROW = 7
    
    # Calculate Grid Size
    # Width: Start + Shelves + End Margin
    # Last shelf ends at: START_X + (6 * 5) + 2 = 35
    # Add space for last aisle (approx 3 wide) + wall = 39
    grid_width = 39
    
    # Height: Row 2 Start + Height + Margin
    # 16 + 8 + 3 = 27 + wall = 28
    grid_height = 28
    
    grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]
    aisle_locs = {}
    
    # Walls
    for r in range(grid_height):
        grid[r][0] = 1
        grid[r][grid_width-1] = 1
    for c in range(grid_width):
        grid[0][c] = 1
        grid[grid_height-1][c] = 1

    # Place Shelves
    for row_start_y in [ROW_1_Y, ROW_2_Y]:
        for i in range(SHELVES_PER_ROW):
            sx = START_X + i * SHELF_SPACING_X
            for r in range(row_start_y, row_start_y + SHELF_HEIGHT):
                for c in range(sx, sx + SHELF_WIDTH):
                    if 0 <= r < grid_height and 0 <= c < grid_width:
                        grid[r][c] = 1

    # Define Aisles (8 per row)
    aisle_count = 1
    for row_start_y in [ROW_1_Y, ROW_2_Y]:
        for i in range(SHELVES_PER_ROW + 1):
            cx = 1.5 + i * SHELF_SPACING_X
            top_y = row_start_y
            bot_y = row_start_y + SHELF_HEIGHT - 1
            mid_y = (top_y + bot_y) / 2
            
            aisle_locs[str(aisle_count)] = {
                "top": (top_y, cx),
                "bottom": (bot_y, cx),
                "goal": (int(mid_y), int(cx))
            }
            aisle_count += 1
            
    return grid, aisle_locs, grid_width, grid_height

@profile
def astar(grid, start, goal):
    """
    Implements the A* pathfinding algorithm to find the shortest path.

    Args:
        grid (list): 2D list representing the map (0=walkable, 1=obstacle).
        start (tuple): (row, col) starting coordinates.
        goal (tuple): (row, col) goal coordinates.

    Returns:
        list: A list of (row, col) tuples representing the path, or None if no path found.
    """
    rows, cols = len(grid), len(grid[0])
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    def heuristic(a, b):
        """Euclidean distance heuristic."""
        return math.hypot(a[0] - b[0], a[1] - b[1])

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        # 8-way movement: (dx, dy, cost)
        sqrt2 = math.sqrt(2)
        neighbors = [
            (0, 1, 1), (0, -1, 1), (1, 0, 1), (-1, 0, 1),
            (1, 1, sqrt2), (1, -1, sqrt2), (-1, 1, sqrt2), (-1, -1, sqrt2)
        ]

        for dx, dy, cost in neighbors:
            neighbour = (current[0]+dx, current[1]+dy)

            if 0 <= neighbour[0] < rows and 0 <= neighbour[1] < cols:
                if grid[neighbour[0]][neighbour[1]] == 1:
                    continue

                tentative_g = g_score[current] + cost

                if neighbour not in g_score or tentative_g < g_score[neighbour]:
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative_g
                    f = tentative_g + heuristic(neighbour, goal)
                    heapq.heappush(open_set, (f, neighbour))

    return None


class StoreMap(tk.Frame):
    """
    A Tkinter widget that renders the store map, robot position, and navigation path.
    """
    def __init__(self, parent, target_aisle, max_aisles, on_back, on_arrival=None):
        """Initializes the map view and starts the position polling loop."""
        super().__init__(parent)
        self.configure(bg="#f0f0f0")
        self.pack(fill="both", expand=True)
        
        self.on_back = on_back
        self.on_arrival = on_arrival
        self.target_aisle = str(target_aisle)
        
        # Generate Map
        self.grid, self.aisle_locations, self.GRID_WIDTH, self.GRID_HEIGHT = generate_map(max_aisles, AISLE_ROWS)
        
        # UI Setup
        self.setup_ui()
        
        # Robot state (Placeholder starting position)
        self.robot_x = 2.0
        self.robot_y = 2.0
        self.robot_theta = 0.0

        self.target_x = self.robot_x
        self.target_y = self.robot_y
        self.sensor_x = self.robot_x
        self.sensor_y = self.robot_y
        self.sensor_theta = self.robot_theta
        self.current_goal = None
        self.remaining_path = []
        self._last_path_time = 0.0
        self._last_path_cell = None
        self._camera_x = None
        self._camera_y = None
        self._last_draw_pose = (self.robot_x, self.robot_y, self.robot_theta)

        self._udp_stop = threading.Event()
        self._udp_lock = threading.Lock()
        
        self.robot_ids = []
        self.path_drawn = []
        self.target_drawn = []
        
        self.draw_robot(self.robot_x, self.robot_y, self.robot_theta)
        self.update_visuals()
        
        # Auto-start navigation
        self.start_navigation()
        self.start_udp_listener()
        self.poll_position_update()
        self.bind("<Destroy>", self._on_destroy)

    def _on_destroy(self, _event):
        """Stops background UDP listener when the widget is destroyed."""
        self._udp_stop.set()

    def start_udp_listener(self):
        """Starts a background UDP listener for (x, z, theta) pose updates."""
        thread = threading.Thread(target=self._udp_listener, daemon=True)
        thread.start()

    def _udp_listener(self):
        """Receives pose updates over UDP and updates the sensor position."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind((UDP_HOST, UDP_PORT))
            sock.settimeout(0.5)
            while not self._udp_stop.is_set():
                try:
                    data, _ = sock.recvfrom(UDP_BUFFER_BYTES)
                except socket.timeout:
                    continue

                message = data.decode("utf-8", errors="ignore").strip()
                if not message:
                    continue

                pose = self._parse_pose_message(message)
                if pose:
                    print(f"Received pose: {pose}")
                    x, z, theta = pose
                    if THETA_IN_DEGREES:
                        theta = math.radians(theta + THETA_OFFSET_DEGREES)
                    with self._udp_lock:
                        self.sensor_x = x
                        self.sensor_y = z
                        self.sensor_theta = theta
        finally:
            sock.close()

    def _parse_pose_message(self, message):
        """Parses JSON or CSV pose messages into (x, z, theta)."""
        try:
            payload = json.loads(message)
            x = float(payload.get("x"))
            z = float(payload.get("z"))
            theta = float(payload.get("theta"))
            return x, z, theta
        except Exception:
            pass

        try:
            parts = [p.strip() for p in message.split(",")]
            if len(parts) >= 3:
                return float(parts[0]), float(parts[1]), float(parts[2])
        except Exception:
            pass

        return None

    def setup_ui(self):
        """Sets up the canvas and draws the static map elements (shelves, labels)."""
        # Header
        header = tk.Frame(self, bg="#f0f0f0")
        header.pack(fill="x", padx=10, pady=5)
        
        tk.Button(
            header,
            text="Return",
            font=("Arial", 20),
            width=8,
            height=1,
            bg=SECONDARY,
            fg=TEXT,
            activebackground="#d1d5db",
            bd=0,
            relief="flat",
            command=self.on_back
        ).pack(side="right")
        tk.Label(header, text=f"Navigating to Aisle {self.target_aisle}", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(side="left")

        FULL_W = self.GRID_WIDTH * CELL_SIZE
        FULL_H = self.GRID_HEIGHT * CELL_SIZE
        VIEW_W = 800
        VIEW_H = 440 # Slightly less to account for header

        self.canvas = tk.Canvas(
            self,
            width=VIEW_W,
            height=VIEW_H,
            bg="white",
            scrollregion=(0, 0, FULL_W, FULL_H),
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Draw grid and shelves
        for r in range(self.GRID_HEIGHT):
            for c in range(self.GRID_WIDTH):
                x1 = c * CELL_SIZE
                y1 = r * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE

                if self.grid[r][c] == 1:
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill="#404040", outline="", tags="shelf")

        # Draw Aisle Labels
        for aisle, locs in self.aisle_locations.items():
            # Top Label
            r, c = locs["top"]
            x = c * CELL_SIZE + CELL_SIZE / 2
            y = (r - 2) * CELL_SIZE + CELL_SIZE / 2
            self.canvas.create_text(x, y, text=f"Aisle {aisle}", font=("Arial", 14, "bold"), fill="#666")

            # Bottom Label
            r, c = locs["bottom"]
            y = (r + 2) * CELL_SIZE + CELL_SIZE / 2
            self.canvas.create_text(x, y, text=f"Aisle {aisle}", font=("Arial", 14, "bold"), fill="#666")

    @profile
    def draw_robot(self, x, y, theta):
        """Draws the robot icon and direction beam on the canvas."""
        for item in self.robot_ids:
            self.canvas.delete(item)
        self.robot_ids.clear()

        px = x * CELL_SIZE + CELL_SIZE/2
        py = y * CELL_SIZE + CELL_SIZE/2
        r = CELL_SIZE / 2.5

        beam_len = CELL_SIZE * 3
        beam_angle = 0.5 # radians (~30 degrees)
        
        beam_points = [
            px, py,
            px + beam_len * math.cos(theta - beam_angle),
            py + beam_len * math.sin(theta - beam_angle),
            px + beam_len * math.cos(theta + beam_angle),
            py + beam_len * math.sin(theta + beam_angle)
        ]
        beam = self.canvas.create_polygon(*beam_points, fill="#fef08a", outline="#fde047")
        self.canvas.tag_lower(beam, "shelf")
        self.robot_ids.append(beam)

        circle = self.canvas.create_oval(px-r, py-r, px+r, py+r, fill="#f97316", outline="white", width=2)
        self.robot_ids.append(circle)

    @profile
    def draw_path(self, path, goal_cell):
        """Draws the navigation line and goal marker on the canvas."""
        for item in self.path_drawn:
            self.canvas.delete(item)
        self.path_drawn = []
        
        for item in self.target_drawn:
            self.canvas.delete(item)
        self.target_drawn = []

        line_points = []
        for (r, c) in path:
            cx = c * CELL_SIZE + CELL_SIZE/2
            cy = r * CELL_SIZE + CELL_SIZE/2
            line_points.extend([cx, cy])

        if len(line_points) >= 4:
            line = self.canvas.create_line(*line_points, fill="#3b82f6", width=8, capstyle=tk.ROUND, joinstyle=tk.ROUND)
            self.path_drawn.append(line)

        tr, tc = goal_cell
        tx = tc * CELL_SIZE + CELL_SIZE/2
        ty = tr * CELL_SIZE + CELL_SIZE/2
        tr_size = CELL_SIZE / 1.5
        
        t_circle = self.canvas.create_oval(tx-tr_size, ty-tr_size, tx+tr_size, ty+tr_size, fill="#dc2626", outline="white", width=2)
        self.target_drawn.append(t_circle)
        
        t_text = self.canvas.create_text(tx, ty, text="GOAL", fill="white", font=("Arial", 10, "bold"))
        self.target_drawn.append(t_text)

    @profile
    def update_visuals(self):
        """Periodically updates the robot's visual position (smoothing) and camera view."""
        if not self.winfo_exists():
            return

        with self._udp_lock:
            sx = self.sensor_x
            sy = self.sensor_y
            stheta = self.sensor_theta

        dx = sx - self.robot_x
        dy = sy - self.robot_y
        
        if abs(dx) > 0.001 or abs(dy) > 0.001:
            self.robot_x += dx * 0.2
            self.robot_y += dy * 0.2
            
        # Angle smoothing
        diff = stheta - self.robot_theta
        # Normalize to [-pi, pi]
        diff = (diff + math.pi) % (2 * math.pi) - math.pi
        
        if abs(diff) > 0.001:
            self.robot_theta += diff * 0.2

        # Skip redraws if pose is effectively unchanged
        lx, ly, ltheta = self._last_draw_pose
        pose_changed = (
            abs(self.robot_x - lx) > POSE_EPSILON
            or abs(self.robot_y - ly) > POSE_EPSILON
            or abs(self.robot_theta - ltheta) > THETA_EPSILON
        )

        # Camera follow (800x440 viewport), smoothed each frame
        FULL_W = self.GRID_WIDTH * CELL_SIZE
        FULL_H = self.GRID_HEIGHT * CELL_SIZE
        view_w = 800
        view_h = 440
        target_cam_x = (self.robot_x * CELL_SIZE) - (view_w / 2)
        target_cam_y = (self.robot_y * CELL_SIZE) - (view_h / 2)

        max_cam_x = max(0.0, FULL_W - view_w)
        max_cam_y = max(0.0, FULL_H - view_h)
        target_cam_x = max(0.0, min(target_cam_x, max_cam_x))
        target_cam_y = max(0.0, min(target_cam_y, max_cam_y))

        if self._camera_x is None or self._camera_y is None:
            self._camera_x = target_cam_x
            self._camera_y = target_cam_y
        else:
            self._camera_x += (target_cam_x - self._camera_x) * CAMERA_SMOOTHING
            self._camera_y += (target_cam_y - self._camera_y) * CAMERA_SMOOTHING

        if FULL_W > 0 and FULL_H > 0:
            self.canvas.xview_moveto(self._camera_x / FULL_W)
            self.canvas.yview_moveto(self._camera_y / FULL_H)

        if pose_changed:
            if self.current_goal:
                vis_path = [(self.robot_y, self.robot_x)] + self.remaining_path
                self.draw_path(vis_path, self.current_goal)

            self.draw_robot(self.robot_x, self.robot_y, self.robot_theta)
            self._last_draw_pose = (self.robot_x, self.robot_y, self.robot_theta)

        self.after(DRAW_INTERVAL_MS, self.update_visuals)

    def start_navigation(self):
        """Calculates the initial path to the target aisle."""
        if self.target_aisle in self.aisle_locations:
            goal = self.aisle_locations[self.target_aisle]["goal"]
            start = (int(self.robot_y), int(self.robot_x))
            path = astar(self.grid, start, goal)
            if path:
                self.current_goal = goal
                self.remaining_path = path[1:]

    @profile
    def poll_position_update(self):
        """Updates the robot's logical position using the latest UDP data."""
        if not self.winfo_exists():
            return

        if self.current_goal:
            # Check if we have arrived at the goal (within 1.5 units)
            gy, gx = self.current_goal
            with self._udp_lock:
                sx = self.sensor_x
                sy = self.sensor_y
            dist = math.hypot(sx - gx, sy - gy)
            if dist < 1.5:
                if self.on_arrival:
                    self.on_arrival()
                return

            now = time.monotonic()
            current_cell = (int(sy), int(sx))
            if now - self._last_path_time >= PATH_RECALC_INTERVAL_S:
                if current_cell != self._last_path_cell:
                    path = astar(self.grid, current_cell, self.current_goal)
                    if path:
                        self.remaining_path = path[1:]
                    self._last_path_cell = current_cell
                self._last_path_time = now

        self.after(100, self.poll_position_update)