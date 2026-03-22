from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.clock import mainthread
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.utils import platform
from kivy.core.window import Window
import requests
import threading
import os

# --- 1. DYNAMIC ANDROID PERMISSIONS ---
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([
        Permission.READ_EXTERNAL_STORAGE,
        Permission.WRITE_EXTERNAL_STORAGE,
        Permission.INTERNET
    ])
    # Explicitly start in the Download folder where PDFs are usually saved
    PRIMARY_STORAGE = '/storage/emulated/0/Download' 
else:
    PRIMARY_STORAGE = os.path.expanduser('~')

SERVER_URL = "https://offline-demo-mode.hf.space/process_pdf"

# --- ANDROID 11+ FULL STORAGE REDIRECT ---
def request_full_storage_permission():
    if platform == 'android':
        try:
            from jnius import autoclass, cast
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Environment = autoclass('android.os.Environment')
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            Uri = autoclass('android.net.Uri')

            # If permission isn't granted, redirect to settings
            if not Environment.isExternalStorageManager():
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                uri = Uri.parse("package:" + PythonActivity.mActivity.getPackageName())
                intent.setData(uri)
                currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
                currentActivity.startActivity(intent)
        except Exception as e:
            print(f"Failed to request full storage: {e}")


class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_file = None
        
        # Root Layout
        self.layout = BoxLayout(orientation='vertical', padding=15, spacing=15)

        # --- TOP BAR ---
        top_bar = BoxLayout(size_hint_y=0.1)
        self.status_label = Label(text="", font_size='14sp', halign='left')
        self.status_label.bind(size=self.status_label.setter('text_size'))
        
        # 3-Bar Menu Icon (Hamburger Menu)
        menu_btn = Button(text="≡", font_size='35sp', size_hint_x=0.15, background_color=(0.3, 0.3, 0.3, 1))
        menu_btn.bind(on_press=self.go_to_settings)
        
        top_bar.add_widget(self.status_label)
        top_bar.add_widget(menu_btn)
        self.layout.add_widget(top_bar)

        # --- THE 2 LINES OF TEXT ---
        text_box = BoxLayout(orientation='vertical', size_hint_y=0.5)
        self.desc1 = Label(
            text="This application extracts voter information from pdf file and saves to excel file", 
            halign='center', valign='middle', font_size='18sp'
        )
        self.desc1.bind(size=self.desc1.setter('text_size'))
        
        self.desc2 = Label(text="Select the file to begin", bold=True, font_size='20sp', size_hint_y=0.4)
        
        text_box.add_widget(self.desc1)
        text_box.add_widget(self.desc2)
        self.layout.add_widget(text_box)

        # --- BOTTOM BUTTONS ---
        self.btn_box = BoxLayout(orientation='vertical', size_hint_y=0.4, spacing=15)
        
        # Always Red Select Button
        self.select_btn = Button(text="Select", font_size='18sp', background_color=(0.8, 0.2, 0.2, 1)) 
        self.select_btn.bind(on_press=self.show_file_popup)
        self.btn_box.add_widget(self.select_btn)

        # The Start button is created, but NOT added to the screen yet
        self.start_btn = Button(text="Start", font_size='18sp', background_color=(0.1, 0.7, 0.3, 1)) 
        self.start_btn.bind(on_press=self.start_upload)

        self.layout.add_widget(self.btn_box)
        self.add_widget(self.layout)

    def go_to_settings(self, instance):
        self.manager.current = 'settings'

    def show_file_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10)
        file_chooser = FileChooserListView(path=PRIMARY_STORAGE, filters=['*.pdf'])
        content.add_widget(file_chooser)

        btn_box = BoxLayout(size_hint_y=0.15, spacing=10)
        cancel_btn = Button(text="Cancel", background_color=(0.5, 0.5, 0.5, 1))
        select_popup_btn = Button(text="Select", background_color=(0.8, 0.2, 0.2, 1))
        
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(select_popup_btn)
        content.add_widget(btn_box)

        popup = Popup(title="Browse for PDF", content=content, size_hint=(0.95, 0.95))

        def on_select(btn):
            if file_chooser.selection:
                self.selected_file = file_chooser.selection[0]
                self.status_label.text = f"Selected:\n{os.path.basename(self.selected_file)}"
                
                # Magically make the Green Start button appear below Select!
                if self.start_btn not in self.btn_box.children:
                    self.btn_box.add_widget(self.start_btn)
            popup.dismiss()

        cancel_btn.bind(on_press=popup.dismiss)
        select_popup_btn.bind(on_press=on_select)
        popup.open()

    def start_upload(self, instance):
        if not self.selected_file:
            return

        self.status_label.text = "Uploading and Processing...\n(Please wait)"
        self.start_btn.disabled = True
        self.select_btn.disabled = True

        threading.Thread(target=self.send_to_server, args=(self.selected_file,), daemon=True).start()

    def send_to_server(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                files = {'file': f}
                response = requests.post(SERVER_URL, files=files)

            if response.status_code == 200:
                app = App.get_running_app()
                output_dir = app.output_dir if app.output_dir != PRIMARY_STORAGE else os.path.dirname(filepath)
                save_path = os.path.join(output_dir, os.path.basename(filepath).replace('.pdf', '_Completed.xlsx'))

                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                self.update_status(f"SUCCESS! Excel saved to:\n{output_dir}")
            else:
                self.update_status(f"Server Error: {response.text}")

        except Exception as e:
            self.update_status("Connection Failed! Check Server/Wi-Fi.")

    @mainthread
    def update_status(self, message):
        self.status_label.text = message
        self.start_btn.disabled = False
        self.select_btn.disabled = False
        
        # Hide the start button again after completion
        if self.start_btn in self.btn_box.children:
            self.btn_box.remove_widget(self.start_btn)
            self.selected_file = None

    def update_theme(self, is_dark):
        font_color = (1, 1, 1, 1) if is_dark else (0.1, 0.1, 0.1, 1)
        self.desc1.color = font_color
        self.desc2.color = font_color
        self.status_label.color = font_color


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=15)

        # --- TOP BAR WITH ARROW ---
        top_bar = BoxLayout(size_hint_y=0.1)
        back_btn = Button(text="←", font_size='35sp', size_hint_x=0.15, background_color=(0.3, 0.3, 0.3, 1))
        back_btn.bind(on_press=self.go_back)
        
        self.title_label = Label(text="Options Menu", font_size='22sp', bold=True)
        
        top_bar.add_widget(back_btn)
        top_bar.add_widget(self.title_label)
        top_bar.add_widget(Label(size_hint_x=0.15)) # Spacer
        self.layout.add_widget(top_bar)

        # --- ANDROID 11+ PDF PERMISSION BUTTON ---
        perm_btn = Button(text="Grant Full Folder Access\n(Fix missing PDFs)", size_hint_y=0.15, background_color=(0.8, 0.5, 0.1, 1), halign='center')
        perm_btn.bind(on_press=lambda x: request_full_storage_permission())
        self.layout.add_widget(perm_btn)

        # --- THEME TOGGLE ---
        self.theme_btn = Button(text="Switch to Light Theme", size_hint_y=0.15, background_color=(0.5, 0.5, 0.5, 1))
        self.theme_btn.bind(on_press=self.toggle_theme)
        self.layout.add_widget(self.theme_btn)

        # --- FOLDER CHOOSER ---
        self.folder_label = Label(text="Current Output Folder:\nDefault (Same as PDF)", size_hint_y=0.2, halign='center')
        self.layout.add_widget(self.folder_label)

        change_folder_btn = Button(text="Change output folder", size_hint_y=0.15, background_color=(0.2, 0.5, 0.8, 1))
        change_folder_btn.bind(on_press=self.show_folder_popup)
        self.layout.add_widget(change_folder_btn)

        self.layout.add_widget(Label(size_hint_y=0.25)) # Spacer to push elements up
        self.add_widget(self.layout)

    def go_back(self, instance):
        self.manager.current = 'main'

    def toggle_theme(self, instance):
        app = App.get_running_app()
        app.is_dark_theme = not app.is_dark_theme
        
        if app.is_dark_theme:
            Window.clearcolor = (0.1, 0.1, 0.1, 1)
            self.theme_btn.text = "Switch to Light Theme"
            self.title_label.color = (1, 1, 1, 1)
            self.folder_label.color = (1, 1, 1, 1)
        else:
            Window.clearcolor = (0.95, 0.95, 0.95, 1)
            self.theme_btn.text = "Switch to Dark Theme"
            self.title_label.color = (0.1, 0.1, 0.1, 1)
            self.folder_label.color = (0.1, 0.1, 0.1, 1)
            
        self.manager.get_screen('main').update_theme(app.is_dark_theme)

    def show_folder_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10)
        # dirselect=True restricts picking to Folders instead of Files
        folder_chooser = FileChooserListView(path=PRIMARY_STORAGE, dirselect=True)
        content.add_widget(folder_chooser)

        btn_box = BoxLayout(size_hint_y=0.15, spacing=10)
        cancel_btn = Button(text="Cancel", background_color=(0.5, 0.5, 0.5, 1))
        set_folder_btn = Button(text="Set Folder", background_color=(0.2, 0.5, 0.8, 1))
        
        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(set_folder_btn)
        content.add_widget(btn_box)

        popup = Popup(title="Select Output Folder", content=content, size_hint=(0.95, 0.95))

        def on_set(btn):
            app = App.get_running_app()
            if folder_chooser.selection:
                app.output_dir = folder_chooser.selection[0]
            else:
                app.output_dir = folder_chooser.path
            self.folder_label.text = f"Current Output Folder:\n{app.output_dir}"
            popup.dismiss()

        cancel_btn.bind(on_press=popup.dismiss)
        set_folder_btn.bind(on_press=on_set)
        popup.open()


class VoterApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_dark_theme = True
        self.output_dir = PRIMARY_STORAGE

    def build(self):
        Window.clearcolor = (0.1, 0.1, 0.1, 1) # Start in Dark Mode
        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        return sm

if __name__ == '__main__':
    VoterApp().run()