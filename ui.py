import tkinter as tk
from styles import *
from database import get_categories, get_items_for_category, get_all_items

class CaddyMateUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CaddyMate")
        self.root.geometry("800x480")
        self.root.configure(bg=BG_COLOR)

        self.fonts = load_fonts(root)

        self.show_main_menu()

    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

    def make_button(self, text, command, parent=None, large=True, primary=True, width=None):
        if parent is None:
            parent = self.root

        if width is None:
            width = 18 if large else 16

        return tk.Button(
            parent,
            text=text,
            font=self.fonts["button"] if large else self.fonts["small"],
            width=width,
            height=2 if large else 1,
            bg=PRIMARY if primary else SECONDARY,
            fg="white" if primary else TEXT,
            activebackground=PRIMARY_DARK if primary else "#d1d5db",
            bd=0,
            relief="flat",
            command=command
        )
    
    def make_scrollable_frame(self):
        container = tk.Frame(self.root, bg=BG_COLOR)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, bg=BG_COLOR, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=BG_COLOR)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Force geometry update BEFORE creating window
        canvas.update_idletasks()
        
        window_id = canvas.create_window(0, 0, window=scrollable_frame, anchor="n", width=canvas.winfo_width())
        
        def resize_frame(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", resize_frame)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
        # Click and drag
        def on_press(event):
            canvas.scan_mark(event.x, event.y)
        
        def on_drag(event):
            canvas.scan_dragto(event.x, event.y, gain=1)
        
        # Bind to canvas
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        
        # RECURSIVELY bind to all child widgets
        def bind_to_widget(widget):
            widget.bind("<ButtonPress-1>", on_press)
            widget.bind("<B1-Motion>", on_drag)
            for child in widget.winfo_children():
                bind_to_widget(child)
        
        bind_to_widget(scrollable_frame)
        
        # Re-bind when new widgets are added
        def update_bindings(event):
            bind_to_widget(scrollable_frame)
        
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            update_bindings(event)

        scrollable_frame.bind("<Configure>", on_frame_configure)

        return scrollable_frame, canvas


    # Main Menu
    def show_main_menu(self):
        self.clear()

        tk.Label(
            self.root,
            text="CaddyMate",
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=TEXT
        ).pack(pady=40)

        self.make_button("Locate Item", self.show_categories).pack(pady=15)
        self.make_button("Search Items", self.show_search).pack(pady=15)


    # Categories
    def show_categories(self):
        self.clear()

        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=10)

        self.make_button("Return", self.show_main_menu, parent=header_frame, large=False, primary=False, width=8).pack(side="right", padx=10)

        tk.Label(
            header_frame,
            text="Select Category",
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=TEXT
        ).pack(side="left", padx=10)

        list_frame, _ = self.make_scrollable_frame()

        for cat_id, name in get_categories():
            self.make_button(name, lambda c=cat_id, n=name: self.show_items(c, n), parent=list_frame, large=False, width=22).pack(pady=6)


    # Search
    def show_search(self):
        self.clear()

        search_var = tk.StringVar()

        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=5)

        self.make_button("Return", self.show_main_menu, parent=header_frame, large=False, primary=False, width=8).pack(side="right", padx=10)

        search_entry = tk.Entry(
            header_frame,
            textvariable=search_var,
            font=self.fonts["small"],
            bg="white",
            fg=TEXT,
            bd=2,
            relief="solid",
            width=30
        )
        search_entry.place(relx=0.5, rely=0.5, anchor="center")

        keyboard_frame = tk.Frame(self.root, bg=BG_COLOR)
        keyboard_frame.pack(fill="x", pady=5)
        self.create_touch_keyboard(keyboard_frame, search_var)

        list_frame, canvas = self.make_scrollable_frame()

        all_items = get_all_items()

        for item, aisle in all_items:
            btn = self.make_button(item, lambda i=item, a=aisle: self.show_result(i, a), parent=list_frame, large=False, width=22)
            btn.pack(pady=3)
            btn.item_name = item

        search_var.trace("w", lambda *_: self.filter_search_results(search_var.get(), list_frame, canvas))

    def create_touch_keyboard(self, parent, text_var):
        keys = [
            ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
            ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
            ['z', 'x', 'c', 'v', 'b', 'n', 'm']
        ]

        for row in keys:
            row_frame = tk.Frame(parent, bg=BG_COLOR)
            row_frame.pack()
            for key in row:
                btn = tk.Button(
                    row_frame,
                    text=key.upper(),
                    font=("Arial", 14, "bold"),
                    width=4,
                    height=2,
                    bg="#e5e7eb",
                    fg=TEXT,
                    bd=1,
                    relief="raised",
                    command=lambda k=key: text_var.set(text_var.get() + k)
                )
                btn.pack(side="left", padx=2, pady=2)

        bottom_frame = tk.Frame(parent, bg=BG_COLOR)
        bottom_frame.pack()

        tk.Button(
            bottom_frame,
            text="SPACE",
            font=("Arial", 14, "bold"),
            width=20,
            height=2,
            bg="#e5e7eb",
            fg=TEXT,
            bd=1,
            relief="raised",
            command=lambda: text_var.set(text_var.get() + ' ')
        ).pack(side="left", padx=2, pady=2)

        tk.Button(
            bottom_frame,
            text="⌫",
            font=("Arial", 14, "bold"),
            width=8,
            height=2,
            bg="#fca5a5",
            fg=TEXT,
            bd=1,
            relief="raised",
            command=lambda: text_var.set(text_var.get()[:-1])
        ).pack(side="left", padx=2, pady=2)

        tk.Button(
            bottom_frame,
            text="CLEAR",
            font=("Arial", 14, "bold"),
            width=8,
            height=2,
            bg="#fca5a5",
            fg=TEXT,
            bd=1,
            relief="raised",
            command=lambda: text_var.set('')
        ).pack(side="left", padx=2, pady=2)

    def filter_search_results(self, query, list_frame, canvas):
        query_lower = query.lower()

        for widget in list_frame.winfo_children():
            if hasattr(widget, 'item_name'):
                if query_lower in widget.item_name.lower():
                    widget.pack(pady=6)
                else:
                    widget.pack_forget()

        # Scroll to the top after filtering
        canvas.yview_moveto(0)


    # Items
    def show_items(self, category_id, category_name):
        self.clear()

        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=10)

        self.make_button("Return", self.show_categories, parent=header_frame, large=False, primary=False, width=8).pack(side="right", padx=10)

        tk.Label(
            header_frame,
            text=category_name,
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=TEXT
        ).pack(side="left", padx=10)

        items = get_items_for_category(category_id)

        list_frame, _ = self.make_scrollable_frame()

        for item, aisle in items:
            self.make_button(item, lambda i=item, a=aisle: self.show_result(i, a), parent=list_frame, large=False, width=22).pack(pady=6)


    # Result
    def show_result(self, item, aisle):
        self.clear()

        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=10)

        self.make_button("Return", self.show_categories, parent=header_frame, large=False, primary=False, width=8).pack(side="right", padx=10)

        tk.Label(
            self.root,
            text=item,
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=TEXT
        ).pack(pady=20)

        tk.Label(
            self.root,
            text=aisle,
            font=self.fonts["result"],
            bg=BG_COLOR,
            fg=PRIMARY
        ).pack(pady=50)
