import tkinter as tk
from ui import CaddyMateUI

if __name__ == "__main__":
    root = tk.Tk()

    # Start in fullscreen
    root.after(500, lambda: root.attributes('-fullscreen', True))

    def toggle_fullscreen(event=None):
        current = root.attributes('-fullscreen')
        root.attributes('-fullscreen', not current)

    # Bind 'f' key to toggle fullscreen
    root.bind('<f>', toggle_fullscreen)

    CaddyMateUI(root)
    root.mainloop()
