import os
import tkinter as tk
from styles import *
from database import get_categories, get_items_for_category, get_all_items, get_max_aisle
from voice import VoiceToText
from ui_components import make_button, make_back_button

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
        self._scroll_canvases = set()
        self._drag_state = {"active": None, "last_y": None, "accum": 0.0}
        self._drag_bindings_ready = False

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

    def enable_canvas_drag_scroll(self, canvas):
        """
        Enables touch-drag scrolling on a canvas widget.
        
        Args:
            canvas: The canvas widget to enable scrolling on
        """
        self._scroll_canvases.add(canvas)
        if not self._drag_bindings_ready:
            self._install_drag_bindings()

    def _install_drag_bindings(self):
        """
        Installs global drag bindings once and routes events to the active canvas.
        """
        self._drag_bindings_ready = True
        pixels_per_unit = 8.0

        def _find_canvas(event):
            widget = self.root.winfo_containing(event.x_root, event.y_root)
            while widget is not None:
                if isinstance(widget, tk.Canvas) and widget in self._scroll_canvases:
                    return widget
                widget = widget.master
            return None

        def on_press(event):
            canvas = _find_canvas(event)
            if canvas is None or not canvas.winfo_exists():
                self._drag_state["active"] = None
                return
            self._drag_state["active"] = canvas
            self._drag_state["last_y"] = event.y_root
            self._drag_state["accum"] = 0.0

        def on_drag(event):
            canvas = self._drag_state["active"]
            if canvas is None or not canvas.winfo_exists():
                self._drag_state["active"] = None
                return
            if self._drag_state["last_y"] is None:
                self._drag_state["last_y"] = event.y_root
                return
            delta_y = event.y_root - self._drag_state["last_y"]
            self._drag_state["accum"] += delta_y
            self._drag_state["last_y"] = event.y_root

            steps = int(self._drag_state["accum"] / pixels_per_unit)
            if steps != 0:
                canvas.yview_scroll(-steps, "units")
                self._drag_state["accum"] -= steps * pixels_per_unit

        def on_release(event):
            self._drag_state["active"] = None
            self._drag_state["last_y"] = None
            self._drag_state["accum"] = 0.0

        self.root.bind_all("<ButtonPress-1>", on_press, add=True)
        self.root.bind_all("<B1-Motion>", on_drag, add=True)
        self.root.bind_all("<ButtonRelease-1>", on_release, add=True)

    def _make_back_button(self, parent=None, padx=0):
        """
        Wrapper for make_back_button that provides the go_back callback.
        """
        if parent is None:
            parent = self.root
        return make_back_button(parent, self.go_back, self.fonts, padx=padx)

    def _create_scrollable_canvas(self, container, bg_color):
        """
        Creates a scrollable canvas with a vertical scrollbar and drag support.

        Returns:
            tuple: (scrollable_frame, canvas)
        """
        canvas = tk.Canvas(container, bg=bg_color, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=bg_color)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.update_idletasks()
        window_id = canvas.create_window(0, 0, window=scrollable_frame, anchor="nw", width=canvas.winfo_width())

        def resize_frame(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", resize_frame)

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable_frame.bind("<Configure>", on_frame_configure)

        canvas.configure(yscrollcommand=scrollbar.set)

        # Enable drag scrolling on this canvas
        self.enable_canvas_drag_scroll(canvas)

        # Mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        return scrollable_frame, canvas

    def _create_card_scroll_area(self):
        """
        Creates a card container with a scrollable content area.

        Returns:
            tuple: (scrollable_frame, canvas)
        """
        card_container = tk.Frame(self.root, bg=BG_COLOR)
        card_container.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        card_frame = tk.Frame(
            card_container,
            bg=CARD_BG,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card_frame.pack(fill="both", expand=True)

        return self._create_scrollable_canvas(card_frame, CARD_BG)

    def _create_header(self, title, title_color=TEXT, subtitle=None):
        """
        Creates a standard header with a back button and optional subtitle.

        Returns:
            tuple: (header_frame, subtitle_frame or None)
        """
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", padx=20, pady=(15, 0))

        tk.Label(
            header_frame,
            text=title,
            font=self.fonts["title"],
            bg=BG_COLOR,
            fg=title_color
        ).pack(side="left")

        self._make_back_button(parent=header_frame)

        subtitle_frame = None
        if subtitle:
            subtitle_frame = tk.Frame(self.root, bg=BG_COLOR)
            subtitle_frame.pack(fill="x", padx=20, pady=(5, 15))
            tk.Label(
                subtitle_frame,
                text=subtitle,
                font=self.fonts["subtitle"],
                bg=BG_COLOR,
                fg=TEXT_LIGHT
            ).pack(side="left")

        return header_frame, subtitle_frame

    def _create_search_header(self, search_var):
        """
        Creates the search header with back button, entry, and mic button.

        Returns:
            tuple: (header_frame, search_entry, mic_btn)
        """
        header_frame = tk.Frame(self.root, bg=BG_COLOR)
        header_frame.pack(fill="x", pady=5)

        self._make_back_button(parent=header_frame, padx=10)

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

        return header_frame, search_entry, mic_btn

    def _create_keyboard_area(self, search_var):
        """
        Creates the on-screen keyboard container and show/hide button.

        Returns:
            tuple: (keyboard_container, keyboard_frame, show_keyboard_btn)
        """
        keyboard_container = tk.Frame(self.root, bg=BG_COLOR)
        keyboard_container.pack(fill="x", pady=5)

        keyboard_frame = tk.Frame(keyboard_container, bg=BG_COLOR)
        keyboard_frame.pack(fill="x")
        self.create_touch_keyboard(keyboard_frame, search_var)

        show_keyboard_btn = tk.Button(
            keyboard_container,
            text="Show Keyboard",
            font=("Arial", 12, "bold"),
            bg=SECONDARY,
            fg=TEXT,
            bd=1,
            relief="raised",
            command=self._show_keyboard
        )

        return keyboard_container, keyboard_frame, show_keyboard_btn
    
    def make_scrollable_frame(self):
        """
        Creates a scrollable frame container with touch-drag support.

        Returns:
            tuple: (scrollable_frame, canvas)
        """
        container = tk.Frame(self.root, bg=BG_COLOR)
        container.pack(fill="both", expand=True)
        return self._create_scrollable_canvas(container, BG_COLOR)


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
        browse_btn = make_button(
            button_container,
            "⌸ 📖 Browse Categories",
            lambda: self.navigate_to(self.show_categories),
            self.fonts,
            large=True,
            primary=True,
            width=22
        )
        browse_btn.pack(pady=10, ipady=4)

        search_btn = make_button(
            button_container,
            "🔍 Search Items",
            lambda: self.navigate_to(self.show_search),
            self.fonts,
            large=True,
            accent=True,
            width=22
        )
        search_btn.pack(pady=10, ipady=4)


    # Categories
    def show_categories(self):
        """Displays the list of item categories."""
        self.clear()

        self._create_header(
            "📂 Browse Categories",
            subtitle="Choose a category to explore items"
        )

        # Card container for category list
        scrollable_frame, canvas = self._create_card_scroll_area()

        # Add padding container
        padding_frame = tk.Frame(scrollable_frame, bg=CARD_BG)
        padding_frame.pack(fill="both", expand=True, padx=20, pady=15)

        for cat_id, name in get_categories():
            btn = make_button(
                padding_frame,
                name,
                lambda c=cat_id, n=name: self.navigate_to(self.show_items, c, n),
                self.fonts,
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

        self._create_search_header(search_var)

        (
            self.keyboard_container,
            self.keyboard_frame,
            self.show_keyboard_btn,
        ) = self._create_keyboard_area(search_var)

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
            btn = make_button(
                list_frame,
                item,
                lambda i=item, a=aisle: self.navigate_to(self.show_result, i, a),
                self.fonts,
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

        self._create_header(
            f"📦 {category_name}",
            subtitle="Select an item to find its location"
        )

        items = get_items_for_category(category_id)

        # Card container for items list
        scrollable_frame, canvas = self._create_card_scroll_area()

        # Add padding container
        padding_frame = tk.Frame(scrollable_frame, bg=CARD_BG)
        padding_frame.pack(fill="both", expand=True, padx=20, pady=15)

        for item, aisle in items:
            btn = make_button(
                padding_frame,
                item,
                lambda i=item, a=aisle: self.navigate_to(self.show_result, i, a),
                self.fonts,
                large=False,
                primary=True,
                width=28
            )
            btn.pack(pady=5, ipady=3)


    # Result
    def show_result(self, item, aisle):
        """Displays the result screen for a specific item."""
        self.clear()

        self._create_header("Item Found", title_color=PRIMARY)

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
        make_button(
            content_frame,
            "Begin Navigation",
            lambda: self.navigate_to(self.show_map, aisle),
            self.fonts,
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
            lambda: self.show_arrival_popup(f"Arrived at Aisle {aisle}"),
            fonts=self.fonts
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
