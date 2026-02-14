import tkinter as tk
import heapq
import math
from styles import SECONDARY, TEXT

CELL_SIZE = 30 # pixels per grid cell

# Map Configuration
AISLE_ROWS = 2

def generate_map(num_aisles, num_rows):
    aisles_per_row = math.ceil(num_aisles / num_rows)
    
    # Layout Constants (in cells)
    AISLE_WIDTH = 4
    SHELF_WIDTH = 2
    SHELF_HEIGHT = 10
    V_MARGIN = 6
    
    # Calculate Grid Size
    # Width: Wall + (Aisles * Width) + (Shelves * Width) + Wall
    grid_width = 1 + (aisles_per_row * AISLE_WIDTH) + ((aisles_per_row - 1) * SHELF_WIDTH) + 1
    
    # Height: Wall + Margins + Shelves + Wall
    grid_height = 2 + (num_rows * SHELF_HEIGHT) + ((num_rows + 1) * V_MARGIN)
    
    grid = [[0 for _ in range(grid_width)] for _ in range(grid_height)]
    aisle_locs = {}
    
    # Walls
    for r in range(grid_height):
        grid[r][0] = 1
        grid[r][grid_width-1] = 1
    for c in range(grid_width):
        grid[0][c] = 1
        grid[grid_height-1][c] = 1
        
    aisle_count = 1
    
    for r_idx in range(num_rows):
        row_top_y = 1 + V_MARGIN + r_idx * (SHELF_HEIGHT + V_MARGIN)
        row_bot_y = row_top_y + SHELF_HEIGHT
        
        for c_idx in range(aisles_per_row):
            if aisle_count > num_aisles:
                break
                
            start_x = 1 + c_idx * (AISLE_WIDTH + SHELF_WIDTH)
            center_x = start_x + (AISLE_WIDTH // 2)
            
            aisle_locs[str(aisle_count)] = {
                "top": (row_top_y, center_x),
                "bottom": (row_bot_y - 1, center_x),
                "goal": ((row_top_y + row_bot_y) // 2, center_x)
            }
            
            # Create Shelf to the right (if not last aisle in row)
            if c_idx < aisles_per_row - 1:
                shelf_start_x = start_x + AISLE_WIDTH
                for r in range(row_top_y, row_bot_y):
                    for w in range(SHELF_WIDTH):
                        grid[r][shelf_start_x + w] = 1
                        # Add tag logic in setup_ui or here? 
                        # The grid is just 0/1, setup_ui draws rectangles.
                        
            aisle_count += 1
            
    return grid, aisle_locs, grid_width, grid_height

def astar(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]

        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            neighbour = (current[0]+dx, current[1]+dy)

            if 0 <= neighbour[0] < rows and 0 <= neighbour[1] < cols:
                if grid[neighbour[0]][neighbour[1]] == 1:
                    continue

                tentative_g = g_score[current] + 1

                if neighbour not in g_score or tentative_g < g_score[neighbour]:
                    came_from[neighbour] = current
                    g_score[neighbour] = tentative_g
                    f = tentative_g + heuristic(neighbour, goal)
                    heapq.heappush(open_set, (f, neighbour))

    return None


class StoreMap(tk.Frame):
    def __init__(self, parent, target_aisle, max_aisles, on_back):
        super().__init__(parent)
        self.configure(bg="#f0f0f0")
        self.pack(fill="both", expand=True)
        
        self.on_back = on_back
        self.target_aisle = str(target_aisle)
        
        # Generate Map
        self.grid, self.aisle_locations, self.GRID_WIDTH, self.GRID_HEIGHT = generate_map(max_aisles, AISLE_ROWS)
        
        # UI Setup
        self.setup_ui()
        
        # Robot state (Placeholder starting position)
        # TODO use real current position
        self.robot_x = 2.0
        self.robot_y = 2.0
        self.robot_theta = 0.0

        self.target_x = 2.0
        self.target_y = 2.0
        self.current_goal = None
        self.remaining_path = []

        self.robot_ids = []
        self.path_drawn = []
        self.target_drawn = []
        self.anim_job = None
        
        self.draw_robot(self.robot_x, self.robot_y, self.robot_theta)
        self.update_visuals()
        
        # Auto-start navigation
        self.start_navigation()

    def setup_ui(self):
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
            command=self.cleanup_and_back
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
        
        # Bind click
        self.canvas.bind("<Button-1>", self.on_canvas_click)

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

    def draw_robot(self, x, y, theta):
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

    def draw_path(self, path, goal_cell):
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

    def update_visuals(self):
        if not self.winfo_exists():
            return

        dx = self.target_x - self.robot_x
        dy = self.target_y - self.robot_y
        
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            self.robot_x += dx * 0.1
            self.robot_y += dy * 0.1
            self.robot_theta = math.atan2(dy, dx)
            
        # Camera follow (800x480 viewport)
        FULL_W = self.GRID_WIDTH * CELL_SIZE
        FULL_H = self.GRID_HEIGHT * CELL_SIZE
        cam_x = (self.robot_x * CELL_SIZE) - (800 / 2)
        cam_y = (self.robot_y * CELL_SIZE) - (440 / 2)
        self.canvas.xview_moveto(cam_x / FULL_W)
        self.canvas.yview_moveto(cam_y / FULL_H)

        if self.current_goal:
            vis_path = [(self.robot_y, self.robot_x), (self.target_y, self.target_x)] + self.remaining_path
            self.draw_path(vis_path, self.current_goal)

        self.draw_robot(self.robot_x, self.robot_y, self.robot_theta)

        self.after(20, self.update_visuals)

    def simulate_walking(self, path_queue):
        if not path_queue:
            return

        next_r, next_c = path_queue[0]
        self.target_y = float(next_r)
        self.target_x = float(next_c)
        
        self.remaining_path = path_queue[1:]
        
        self.anim_job = self.after(400, lambda: self.simulate_walking(self.remaining_path))

    def start_navigation(self):
        if self.target_aisle in self.aisle_locations:
            goal = self.aisle_locations[self.target_aisle]["goal"]
            start = (int(self.robot_y), int(self.robot_x))
            path = astar(self.grid, start, goal)
            if path:
                self.current_goal = goal
                self.remaining_path = path[1:]

    def on_canvas_click(self, event):
        if self.anim_job:
            self.after_cancel(self.anim_job)
            self.anim_job = None

        c = int(self.canvas.canvasx(event.x) / CELL_SIZE)
        r = int(self.canvas.canvasy(event.y) / CELL_SIZE)

        if 0 <= r < self.GRID_HEIGHT and 0 <= c < self.GRID_WIDTH and self.grid[r][c] == 0:
            self.target_x = float(c)
            self.target_y = float(r)
            self.robot_x = float(c)
            self.robot_y = float(r)
            
            if self.current_goal:
                path = astar(self.grid, (r, c), self.current_goal)
                if path:
                    self.remaining_path = path[1:]

    def cleanup_and_back(self):
        if self.anim_job:
            self.after_cancel(self.anim_job)
            self.anim_job = None
        self.on_back()