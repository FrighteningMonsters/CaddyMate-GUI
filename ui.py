import os
import tkinter as tk
from styles import *
from database import get_categories, get_items_for_category, get_all_items, get_max_aisle
from voice import VoiceToText

class CaddyMateUI:
    """
    The main controller for the CaddyMate User Interface.
    Manages screen navigation, input handling, and view rendering.
    """
    def __init__(self, root):
        """
        Initializes the UI, loads resources (fonts, images), and displays the main menu.
        """
        self.root = root
        self.root.title("CaddyMate")
        self.root.geometry("800x480")
        self.root.configure(bg=BG_COLOR)

        self.fonts = load_fonts(root)
        self.history = []

        self.vtt = VoiceToText()
        self.voice_active = False
        self._arrival_popup = None

        base_dir = os.path.dirname(os.path.abspath(__file__))
        mic_full = tk.PhotoImage(file=os.path.join(base_dir, "resources", "microphone.png"))
        self.mic_icon = mic_full.subsample(50, 50)

        logo_full = tk.PhotoImage(file=os.path.join(base_dir, "resources", "logo.png"))
        self.logo_icon = logo_full.subsample(3, 3)

        # Create a solid red square stop icon the same size as the mic icon
        stop_size = 24
        self.stop_icon = tk.PhotoImage(width=stop_size, height=stop_size)
        self.stop_icon.put("#dc2626", to=(0, 0, stop_size, stop_size))

        self.show_main_menu()

    def navigate_to(self, screen_func, *args):
        """
        Navigates to a new screen function, saving the current state to history.
        """
        self.history.append((screen_func, args))
        screen_func(*args)

    def go_back(self):
        """
        Returns to the previous screen in the history stack.
        """
        if len(self.history) > 1:
            self.history.pop()  # Remove current screen
            screen_func, args = self.history.pop()  # Get previous screen
            self.navigate_to(screen_func, *args)

    def clear(self):
        """
        Clears all widgets from the root window and stops any active voice recording.
        """
        self.stop_voice()
        for w in self.root.winfo_children():
            w.destroy()

    def make_button(self, text, command, parent=None, large=True, primary=True, width=None, accent=False):
        """
        Helper method to create a standardized button widget.

        Returns:
            tk.Button: The configured button widget.
        """
        if parent is None:
            parent = self.root

        if width is None:
            width = 18 if large else 16

        # Determine colors based on button type
        if accent:
            bg_color = ACCENT
            active_bg = ACCENT_HOVER
        elif primary:
            bg_color = PRIMARY
            active_bg = PRIMARY_HOVER
        else:
            bg_color = SECONDARY
            active_bg = "#d1d5db"

        btn = tk.Button(
            parent,
            text=text,
            font=self.fonts["button"] if large else self.fonts["small"],
            width=width,
            height=2 if large else 1,
            bg=bg_color,
            fg="white" if (primary or accent) else TEXT,
            activebackground=active_bg,
            activeforeground="white" if (primary or accent) else TEXT,
            bd=0,
            relief="flat",
            command=command,
            cursor="hand2"
        )
        
        # Add hover effects
        def on_enter(e):
            btn.config(bg=active_bg)
        
        def on_leave(e):
            btn.config(bg=bg_color)
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def make_back_button(self, parent=None, padx=0):
        """
        Helper method to create a standardized back button widget.
        
        Args:
            parent: The parent frame for the button. Defaults to root.
            padx: Horizontal padding for the button pack call. Defaults to 0.
        
        Returns:
            tk.Button: The configured back button widget.
        """
        if parent is None:
            parent = self.root
        
        btn = self.make_button(
            "← Back",
            self.go_back,
            parent=parent,
            large=False,
            primary=False,
            width=8
        )
        btn.pack(side="right", padx=padx)
        return btn
    
    def make_scrollable_frame(self):
        """
        Creates a scrollable frame container with touch-drag support.

        Returns:
            tuple: (scrollable_frame, canvas)
        """
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
        """Displays the main menu screen."""
        self.clear()
        self.history = [(self.show_main_menu, ())]

        # Main container with compact padding for small screen
        main_container = tk.Frame(self.root, bg=BG_COLOR)
        main_container.pack(fill="both", expand=True, padx=20, pady=15)

        # Header with logo and title
        header_frame = tk.Frame(main_container, bg=BG_COLOR)
        header_frame.pack(pady=(0, 20))

        tk.Label(
            header_frame,
            image=self.logo_icon,
            bg=BG_COLOR
        ).pack(side="left", padx=(0, 12))

        title_frame = tk.Frame(header_frame, bg=BG_COLOR)
        title_frame.pack(side="left")

        tk.Label(
            title_frame,
            text="CaddyMate",
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=TEXT
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="Your Smart Shopping Assistant",
            font=self.fonts["subtitle"],
            bg=BG_COLOR,
            fg=TEXT_LIGHT
        ).pack(anchor="w")

        # Card container for buttons
        card_frame = tk.Frame(
            main_container,
            bg=CARD_BG,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card_frame.pack(fill="both", expand=True)

        # Add padding inside card
        inner_frame = tk.Frame(card_frame, bg=CARD_BG)
        inner_frame.pack(fill="both", expand=True, padx=25, pady=25)

        # Button container for proper spacing
        button_container = tk.Frame(inner_frame, bg=CARD_BG)
        button_container.pack(expand=True)

        # Modern styled buttons with icons
        browse_btn = self.make_button(
            "📂 Browse Categories",
            lambda: self.navigate_to(self.show_categories),
            parent=button_container,
            large=True,
            primary=True,
            width=22
        )
        browse_btn.pack(pady=10, ipady=4)

        search_btn = self.make_button(
            "🔍 Search Items",
            lambda: self.navigate_to(self.show_search),
            parent=button_container,
            large=True,
            accent=True,
            width=22
        )
        search_btn.pack(pady=10, ipady=4)


    # Categories
    def show_categories(self):
        """Displays the list of item categories."""
        self.clear()

        # Top header with back button
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=20, pady=(15, 0))

        tk.Label(
            header_frame,
            text="📂 Browse Categories",
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=TEXT
        ).pack(side="left")

        self.make_back_button(parent=header_frame)

        # Subtitle
        subtitle_frame = tk.Frame(self.root, bg=BG_COLOR)
        subtitle_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        tk.Label(
            subtitle_frame,
            text="Choose a category to explore items",
            font=self.fonts["subtitle"],
            bg=BG_COLOR,
            fg=TEXT_LIGHT
        ).pack(side="left")

        # Card container for category list
        card_container = tk.Frame(self.root, bg=BG_COLOR)
        card_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        card_frame = tk.Frame(
            card_container,
            bg=CARD_BG,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card_frame.pack(fill="both", expand=True)

        # Create scrollable area inside card
        canvas = tk.Canvas(card_frame, bg=CARD_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(card_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CARD_BG)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

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

        # Add padding container
        padding_frame = tk.Frame(scrollable_frame, bg=CARD_BG)
        padding_frame.pack(fill="both", expand=True, padx=20, pady=15)

        for cat_id, name in get_categories():
            btn = self.make_button(
                name,
                lambda c=cat_id, n=name: self.navigate_to(self.show_items, c, n),
                parent=padding_frame,
                large=False,
                primary=True,
                width=28
            )
            btn.pack(pady=5, ipady=3)


    # Search
    def show_search(self):
        """Displays the search screen with keyboard and voice input options."""
        self.clear()

        search_var = tk.StringVar()

        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=5)

        self.make_back_button(parent=header_frame, padx=10)

        search_bar = tk.Frame(header_frame, bg=BG_COLOR)
        search_bar.place(relx=0.5, rely=0.5, anchor="center")

        search_entry = tk.Entry(
            search_bar,
            textvariable=search_var,
            font=self.fonts["small"],
            bg="white",
            fg=TEXT,
            bd=2,
            relief="solid",
            width=26
        )
        search_entry.pack(side="left")

        mic_btn = tk.Button(
            search_bar,
            image=self.mic_icon,
            width=40,
            height=40,
            bg=SECONDARY,
            bd=1,
            relief="raised",
            command=lambda: self.toggle_voice(search_var, mic_btn)
        )
        mic_btn.pack(side="left", padx=(4, 0))

        self.keyboard_container = tk.Frame(self.root, bg=BG_COLOR)
        self.keyboard_container.pack(fill="x", pady=5)

        self.keyboard_frame = tk.Frame(self.keyboard_container, bg=BG_COLOR)
        self.keyboard_frame.pack(fill="x")
        self.create_touch_keyboard(self.keyboard_frame, search_var)

        self.show_keyboard_btn = tk.Button(
            self.keyboard_container,
            text="Show Keyboard",
            font=("Arial", 12, "bold"),
            bg=SECONDARY,
            fg=TEXT,
            bd=1,
            relief="raised",
            command=self._show_keyboard
        )

        list_frame, canvas = self.make_scrollable_frame()
        list_container = canvas.master
        list_container.configure(bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
        list_container.pack_configure(padx=20, pady=(0, 15))
        canvas.configure(bg=CARD_BG)
        list_frame.configure(bg=CARD_BG)

        padding_frame = tk.Frame(list_frame, bg=CARD_BG)
        padding_frame.pack(fill="both", expand=True, padx=20, pady=15)

        all_items = get_all_items()
        search_var.trace("w", lambda *_: self.filter_search_results(search_var.get(), all_items, padding_frame, canvas))

    def create_touch_keyboard(self, parent, text_var):
        """Creates an on-screen touch keyboard inside the specified parent frame."""
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
            bg="#f76868",
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
            bg="#f76868",
            fg=TEXT,
            bd=1,
            relief="raised",
            command=lambda: text_var.set('')
        ).pack(side="left", padx=2, pady=2)

    def _hide_keyboard(self):
        """Hides the on-screen keyboard to save space."""
        self.keyboard_frame.pack_forget()
        self.show_keyboard_btn.pack(fill="x", padx=10, pady=2)

    def _show_keyboard(self):
        """Shows the on-screen keyboard."""
        self.show_keyboard_btn.pack_forget()
        self.keyboard_frame.pack(fill="x")

    def toggle_voice(self, search_var, mic_btn):
        """Toggles voice recognition on or off."""
        if self.voice_active:
            self.stop_voice(mic_btn)
        else:
            self.voice_active = True
            mic_btn.configure(bg="#fca5a5", image=self.stop_icon)
            self._hide_keyboard()

            def on_result(text, final):
                if final:
                    search_var.set(text)
                    self.stop_voice(mic_btn)

            started = self.vtt.start(on_result)
            if not started:
                self.voice_active = False
                mic_btn.configure(bg=SECONDARY, image=self.mic_icon)

    def stop_voice(self, mic_btn=None):
        """Stops the voice recognition stream."""
        if self.voice_active:
            self.vtt.stop()
            self.voice_active = False
            if mic_btn:
                mic_btn.configure(bg=SECONDARY, image=self.mic_icon)

    def filter_search_results(self, query, items, list_frame, canvas):
        """Filters the list of items based on the search query."""
        query_lower = query.lower()

        for widget in list_frame.winfo_children():
            widget.destroy()

        if not query_lower:
            canvas.yview_moveto(0)
            return

        starts_with = []
        whole_word = []
        contains = []

        for item, aisle in items:
            name_lower = item.lower()
            words = name_lower.split()
            if name_lower.startswith(query_lower):
                starts_with.append((item, aisle))
            elif query_lower in words:
                whole_word.append((item, aisle))
            elif query_lower in name_lower:
                contains.append((item, aisle))

        for item, aisle in starts_with + whole_word + contains:
            btn = self.make_button(
                item,
                lambda i=item, a=aisle: self.navigate_to(self.show_result, i, a),
                parent=list_frame,
                large=False,
                width=22
            )
            btn.pack(pady=4)

        # Scroll to the top after filtering
        canvas.yview_moveto(0)


    # Items
    def show_items(self, category_id, category_name):
        """Displays items within a selected category."""
        self.clear()

        # Top header with back button
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=20, pady=(15, 0))

        tk.Label(
            header_frame,
            text=f"📦 {category_name}",
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=TEXT
        ).pack(side="left")

        self.make_back_button(parent=header_frame)

        # Subtitle
        subtitle_frame = tk.Frame(self.root, bg=BG_COLOR)
        subtitle_frame.pack(fill="x", padx=20, pady=(5, 15))
        
        tk.Label(
            subtitle_frame,
            text="Select an item to find its location",
            font=self.fonts["subtitle"],
            bg=BG_COLOR,
            fg=TEXT_LIGHT
        ).pack(side="left")

        items = get_items_for_category(category_id)

        # Card container for items list
        card_container = tk.Frame(self.root, bg=BG_COLOR)
        card_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        card_frame = tk.Frame(
            card_container,
            bg=CARD_BG,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card_frame.pack(fill="both", expand=True)

        # Create scrollable area inside card
        canvas = tk.Canvas(card_frame, bg=CARD_BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(card_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CARD_BG)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

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

        # Add padding container
        padding_frame = tk.Frame(scrollable_frame, bg=CARD_BG)
        padding_frame.pack(fill="both", expand=True, padx=20, pady=15)

        for item, aisle in items:
            btn = self.make_button(
                item,
                lambda i=item, a=aisle: self.navigate_to(self.show_result, i, a),
                parent=padding_frame,
                large=False,
                primary=True,
                width=28
            )
            btn.pack(pady=5, ipady=3)


    # Result
    def show_result(self, item, aisle):
        """Displays the result screen for a specific item."""
        self.clear()

        # Top header with back button
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=20, pady=(15, 0))

        tk.Label(
            header_frame,
            text="Item Found",
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=PRIMARY
        ).pack(side="left")

        self.make_back_button(parent=header_frame)

        # Main content card
        card_container = tk.Frame(self.root, bg=BG_COLOR)
        card_container.pack(fill="both", expand=True, padx=20, pady=(15, 15))

        card_frame = tk.Frame(
            card_container,
            bg=CARD_BG,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card_frame.pack(fill="both", expand=True)

        # Content inside card
        content_frame = tk.Frame(card_frame, bg=CARD_BG)
        content_frame.pack(fill="both", expand=True, padx=30, pady=40)

        # Item name
        tk.Label(
            content_frame,
            text=item,
            font=self.fonts["title"],
            bg=CARD_BG,
            fg=TEXT,
            wraplength=400
        ).pack(pady=(0, 30))

        # Aisle display with icon
        aisle_label_frame = tk.Frame(content_frame, bg=CARD_BG)
        aisle_label_frame.pack(pady=(0, 40))

        tk.Label(
            aisle_label_frame,
            text="Aisle",
            font=self.fonts["small"],
            bg=CARD_BG,
            fg=TEXT_LIGHT
        ).pack()

        tk.Label(
            aisle_label_frame,
            text=aisle,
            font=self.fonts["result"],
            bg=CARD_BG,
            fg=PRIMARY
        ).pack()

        # Navigation button
        self.make_button(
            "Begin Navigation",
            lambda: self.navigate_to(self.show_map, aisle),
            parent=content_frame,
            large=True,
            primary=True
        ).pack(pady=0, ipady=6)

    # Map
    def show_map(self, aisle):
        """Initializes and displays the navigation map."""
        self.clear()
        from map import StoreMap
        
        max_aisles = get_max_aisle()
        StoreMap(
            self.root,
            aisle,
            max_aisles,
            self.go_back,
            lambda: self.show_arrival_popup(f"Arrived at Aisle {aisle}")
        )

    def show_arrival_popup(self, message):
        """Shows a short-lived popup, then returns to the main menu."""
        if self._arrival_popup and self._arrival_popup.winfo_exists():
            return

        popup = tk.Toplevel(self.root)
        self._arrival_popup = popup
        popup.overrideredirect(True)
        popup.configure(bg=BG_COLOR)

        popup.update_idletasks()
        self.root.update_idletasks()
        win_w = self.root.winfo_width()
        win_h = self.root.winfo_height()
        win_x = self.root.winfo_rootx()
        win_y = self.root.winfo_rooty()
        popup.geometry(f"{win_w}x{win_h}+{win_x}+{win_y}")

        frame = tk.Frame(popup, bg=BG_COLOR, bd=2, relief="ridge")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        tk.Label(
            frame,
            text=message,
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=PRIMARY
        ).pack(expand=True)

        def close_and_home():
            if popup.winfo_exists():
                popup.destroy()
            self.show_main_menu()

        popup.after(2000, close_and_home)
