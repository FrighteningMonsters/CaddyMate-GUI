import tkinter as tk
import json
import math
import socket
import threading

# Constants for map dimensions in metres
MAP_WIDTH_METRES = 3.19
MAP_HEIGHT_METRES = 4.27

# Conversion factor: 1 metre = 100 pixels
METRES_TO_PIXELS = 100

# Calculate map dimensions in pixels
MAP_WIDTH_PIXELS = int(MAP_WIDTH_METRES * METRES_TO_PIXELS)
MAP_HEIGHT_PIXELS = int(MAP_HEIGHT_METRES * METRES_TO_PIXELS)

# Load polygons from polygons.txt
POLYGON_FILE = "polygons.txt"

def load_polygons(file_path):
    """Loads polygons from a JSON file."""
    with open(file_path, "r") as f:
        return json.load(f)

class MapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Outline")

        # Create a canvas to draw the map
        self.canvas = tk.Canvas(
            root,
            width=MAP_WIDTH_PIXELS,
            height=MAP_HEIGHT_PIXELS,
            bg="white"
        )
        self.canvas.pack()

        # Ensure PADDING_PIXELS is defined globally
        global PADDING_PIXELS
        PADDING_PIXELS = 20

        # Adjust canvas size to include padding
        self.canvas.config(
            width=MAP_WIDTH_PIXELS + 2 * PADDING_PIXELS,
            height=MAP_HEIGHT_PIXELS + 2 * PADDING_PIXELS
        )

        # Draw the outline of the map with padding
        self.canvas.create_rectangle(
            PADDING_PIXELS, PADDING_PIXELS,
            MAP_WIDTH_PIXELS + PADDING_PIXELS, MAP_HEIGHT_PIXELS + PADDING_PIXELS,
            outline="#000000",  # Black border color
            width=4  # Slightly thicker border
        )

        # Load custom polygons
        custom_polygons = load_polygons(POLYGON_FILE)

        # Draw custom polygons on the canvas
        for polygon in custom_polygons:
            pixel_points = [
                (x * METRES_TO_PIXELS + PADDING_PIXELS, y * METRES_TO_PIXELS + PADDING_PIXELS)
                for x, y in polygon["points"]
            ]
            self.canvas.create_polygon(
                *[coord for point in pixel_points for coord in point],
                fill="#808080",  # Gray color for polygons
                outline="black"
            )

        # Draw user position (circle) and flashlight beam
        self.user_circle = self.canvas.create_oval(
            0, 0, 0, 0,  # Initial position (hidden)
            fill="#FF5733",  # Orange color for the user
            outline="white",
            width=2
        )
        self.flashlight_beam = self.canvas.create_polygon(
            0, 0, 0, 0, 0, 0,  # Initial position (hidden)
            fill="#FFFF00",  # Yellow color for the beam
            outline="yellow"
        )

    def update_user_position(self, x, y, theta):
        """Updates the user's position and flashlight beam."""
        # Convert x, y from metres to pixels
        pixel_x = x * METRES_TO_PIXELS + PADDING_PIXELS
        pixel_y = y * METRES_TO_PIXELS + PADDING_PIXELS

        # Convert theta from degrees to radians
        theta = math.radians(theta)

        # Update user circle position
        radius = 10  # Radius of the circle in pixels
        self.canvas.coords(
            self.user_circle,
            pixel_x - radius, pixel_y - radius,
            pixel_x + radius, pixel_y + radius
        )

        # Update flashlight beam position
        beam_length = 50  # Length of the beam in pixels
        beam_angle = 0.5  # Beam spread in radians (~30 degrees)
        self.canvas.coords(
            self.flashlight_beam,
            pixel_x, pixel_y,
            pixel_x + beam_length * math.cos(theta - beam_angle),
            pixel_y + beam_length * math.sin(theta - beam_angle),
            pixel_x + beam_length * math.cos(theta + beam_angle),
            pixel_y + beam_length * math.sin(theta + beam_angle)
        )

    def start_udp_listener(self, host, port):
        """Starts a UDP listener to receive user position and orientation."""
        def listen():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                udp_socket.bind((host, port))
                print(f"Listening for UDP data on {host}:{port}...")

                while True:
                    data, _ = udp_socket.recvfrom(1024)  # Buffer size of 1024 bytes
                    try:
                        # Parse the received data (expected format: x,y,theta)
                        x, y, theta = map(float, data.decode().strip().split(","))
                        self.update_user_position(x, y, theta)
                    except ValueError:
                        print("Invalid data received:", data)

        # Run the listener in a separate thread
        threading.Thread(target=listen, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MapApp(root)

    # Start the UDP listener
    UDP_HOST = "0.0.0.0"
    UDP_PORT = 5005
    app.start_udp_listener(UDP_HOST, UDP_PORT)

    root.mainloop()