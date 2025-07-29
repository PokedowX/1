import kivy

kivy.require('2.3.0')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
import json
import os
from datetime import datetime, timedelta 
import random
from kivy.core.audio import SoundLoader
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.slider import Slider
import time
import math
from kivy.uix.checkbox import CheckBox
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.label import Label
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.recycleview.layout import LayoutSelectionBehavior

try:
    from kivy.utils import platform

    if platform == 'android':
        from android.permissions import request_permissions, Permission, check_permission
        from android.storage import app_storage_path, primary_external_storage_path
        from android import mActivity
        from jnius import autoclass, cast
        from android.storage import app_storage_path, primary_external_storage_path

        Environment = autoclass('android.os.Environment')
        Context = autoclass('android.content.Context')
        Intent = autoclass('android.content.Intent')
        Uri = autoclass('android.net.Uri')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
except ImportError:
    platform = 'desktop'


def get_data_path():
    if platform == 'android':
        try:
            storage_path = primary_external_storage_path()
            app_dir = os.path.join(storage_path, 'HabitBuilder')
            if not os.path.exists(app_dir):
                os.makedirs(app_dir)
            return os.path.join(app_dir, 'habit_builder_progress.json')
        except Exception:
            try:
                return os.path.join(app_storage_path(), 'habit_builder_progress.json')
            except Exception:
                return 'habit_builder_progress.json'
    else:
        return os.path.join(os.getcwd(), 'habit_builder_progress.json')


FILE = get_data_path()
MOTIVATIONAL_MESSAGES = [
    "Great job! Keep building those habits!",
    "You're making progress every day!",
    "Consistency is key. Keep it up!",
    "Small steps lead to big changes!",
    "You're one day closer to your goals!"
]


def get_default_data():
    return {
        "start_date": datetime.today().strftime("%Y-%m-%d"),
        "total_points": 0,
        "current_level": 1,
        "streak": 0,
        "last_log_date": "",
        "milestones": [],
        "day_logs": {},
        "habits": [
            {"name": "Wake up early", "points": 5},
            {"name": "Exercise (20–30 min)", "points": 5},
            {"name": "Meditation (10–15 min)", "points": 4},
            {"name": "Read (20 minutes)", "points": 4},
            {"name": "Deep Work block (1–2 hrs)", "points": 6},
            {"name": "No mindless scrolling", "points": 5}
        ],
        "audio_playback": {
            "categories": ["English", "Hindi", "Other"],
            "category_history": {},
            "file_history": {}
        },
        # New reminder settings
        "reminder_settings": {
            "enabled": False,
            "time": "20:00",  # Default time: 8 PM
            "habits_enabled": {},  # Will store per-habit toggle states
            "snooze_until": 0,  # Timestamp for snooze expiration
            "last_streak": 0,  # To detect streak changes
            "last_reminder": 0, # Timestamp of last reminder
            "notification_history": [],  # Store notification history

            "journal_questions": [  # Add this key
                {
                    "text": "How was your day?",
                    "type": "FreeText",
                    "options": []
                },
                {
                    "text": "What did you learn today?",
                    "type": "MultipleChoiceOrText",
                    "options": ["New skill", "Interesting fact", "Personal insight"]
                }
            ]
        }
    }



def load_data():
    try:
        if os.path.exists(FILE):
            with open(FILE, "r") as f:
                data = json.load(f)
                if "habits" in data and isinstance(data["habits"], list) and all(
                        isinstance(h, str) for h in data["habits"]):
                    data["habits"] = [{"name": h, "points": 5} for h in data["habits"]]
                default_data = get_default_data()
                for key in default_data:
                    if key not in data:
                        data[key] = default_data[key]
                # Ensure audio_playback structure exists
                if "audio_playback" not in data:
                    data["audio_playback"] = default_data["audio_playback"]
                if "categories" not in data["audio_playback"]:
                    data["audio_playback"]["categories"] = default_data["audio_playback"]["categories"]
                if "category_history" not in data["audio_playback"]:
                    data["audio_playback"]["category_history"] = {}
                if "file_history" not in data["audio_playback"]:
                    data["audio_playback"]["file_history"] = {}
                # Ensure journal_questions exists
                if "reminder_settings" in data and "journal_questions" not in data["reminder_settings"]:
                    data["reminder_settings"]["journal_questions"] = get_default_data()["reminder_settings"][
                        "journal_questions"]
                return data
        else:
            return get_default_data()
    except Exception as e:
        print(f"Error loading data: {e}")
        return get_default_data()


def save_data(data):
    try:
        os.makedirs(os.path.dirname(FILE), exist_ok=True)
        with open(FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")


def get_day_number(start_date):
    try:
        today = datetime.today()
        return (today - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
    except ValueError:
        return 1


def calculate_points(log, habits):
    points = 0
    habit_points = {h["name"]: h["points"] for h in habits}
    for habit, value in log.get("Habits", {}).items():
        if habit in habit_points:
            points += habit_points[habit] if value else -habit_points[habit] // 2
    try:
        points += int(log.get("Energy", 5))
    except (ValueError, TypeError):
        points += 5
    return points


def update_streak(data):
    today = datetime.today().strftime("%Y-%m-%d")
    last_log = data.get("last_log_date", "")
    if last_log == today:
        return 0
    if last_log:
        try:
            last_date = datetime.strptime(last_log, "%Y-%m-%d")
            today_date = datetime.strptime(today, "%Y-%m-%d")
            delta = (today_date - last_date).days
            if delta == 1:
                data["streak"] += 1
            elif delta > 1:
                data["streak"] = 1
            else:
                return 0
        except ValueError:
            data["streak"] = 1
    else:
        data["streak"] = 1
    data["last_log_date"] = today
    return 5 if data["streak"] >= 3 else 0


def update_levels_and_milestones(data, app):
    try:
        new_level = data["total_points"] // 800 + 1
        if new_level > data["current_level"]:
            Clock.schedule_once(lambda dt: app.show_popup(f"🎉 You reached Level {new_level}!"), 0.1)
            data["current_level"] = new_level
        for milestone in [100, 250, 500, 1000, 2000]:
            if data["total_points"] >= milestone and milestone not in data["milestones"]:
                Clock.schedule_once(lambda dt, m=milestone: app.show_popup(f"🏆 You reached {m} points!"), 0.2)
                data["milestones"].append(milestone)
    except (KeyError, TypeError):
        data["current_level"] = 1
        data["milestones"] = []


class HabitsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.habit_states = {}
        Clock.schedule_once(self.build_ui, 0)

    def build_ui(self, dt=None):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        header_label = Label(text='Habit Builder', font_size=30, size_hint_y=0.1, color=(1, 1, 1, 1))
        layout.add_widget(header_label)
        self.stats_label = Label(text=self.get_stats_text(), font_size=16, size_hint_y=0.1, color=(1, 1, 1, 1))
        layout.add_widget(self.stats_label)
        scroll = ScrollView(size_hint_y=0.6)
        habits_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        habits_layout.bind(minimum_height=habits_layout.setter('height'))
        self.habit_states = {}
        for habit in self.app.data["habits"]:
            habit_name = habit["name"]
            habit_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
            label = Label(text=habit_name, font_size=14, text_size=(None, None), color=(1, 1, 1, 1))
            habit_row.add_widget(label)
            toggle = ToggleButton(text='Done', size_hint_x=0.3, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
            toggle.bind(state=self.update_button_color)
            self.habit_states[habit_name] = toggle
            habit_row.add_widget(toggle)
            habits_layout.add_widget(habit_row)
        scroll.add_widget(habits_layout)
        layout.add_widget(scroll)
        energy_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        energy_layout.add_widget(Label(text='Energy Level (1-10):', font_size=14, color=(1, 1, 1, 1)))
        self.energy_spinner = Spinner(text='5', values=[str(i) for i in range(1, 11)], size_hint_x=0.3,
                                      color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        energy_layout.add_widget(self.energy_spinner)
        submit_btn = Button(text='Submit Day', size_hint_y=0.1, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        submit_btn.bind(on_press=self.submit_log)
        layout.add_widget(energy_layout)
        layout.add_widget(submit_btn)
        self.add_widget(layout)

    def update_button_color(self, instance, value):
        if value == 'down':
            instance.background_color = (0, 0.5, 0, 1)  # Green
        else:
            instance.background_color = (0.3, 0.3, 0.3, 1)  # Dark gray

    def get_stats_text(self):
        return f'Day {self.app.day_num} | Level {self.app.data["current_level"]} | Points: {self.app.data["total_points"]} | Streak: {self.app.data["streak"]}'

    def on_pre_enter(self):
        if hasattr(self, 'stats_label'):
            self.stats_label.text = self.get_stats_text()

    def submit_log(self, instance):
        habits_done = sum(1 for btn in self.habit_states.values() if btn.state == 'down')
        total_habits = len(self.habit_states)
        completion_percentage = (habits_done / total_habits * 100) if total_habits > 0 else 0

        # Create confirmation popup
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(
            text=f'Completion: {int(completion_percentage)}%\nEnergy: {self.energy_spinner.text}\n\nSubmit this log?',
            color=(1, 1, 1, 1)))

        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        yes_btn = Button(text='Submit', color=(1, 1, 1, 1), background_color=(0, 0.5, 0, 1))
        no_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.8, 0, 0, 1))
        button_layout.add_widget(yes_btn)
        button_layout.add_widget(no_btn)
        content.add_widget(button_layout)

        popup = Popup(title='Confirm Submission', content=content, size_hint=(0.8, 0.4))

        def do_submit(instance):
            log = {
                "Habits": {habit: btn.state == 'down' for habit, btn in self.habit_states.items()},
                "Energy": self.energy_spinner.text,
                "Completion": str(int(completion_percentage))
            }
            self.app.submit_log(log)
            popup.dismiss()

        yes_btn.bind(on_press=do_submit)
        no_btn.bind(on_press=popup.dismiss)
        popup.open()


class JournalScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.current_question_idx = 0
        self.answer_widgets = {}
        Clock.schedule_once(self.build_ui, 0)

    def build_ui(self, dt=None):
        self.clear_widgets()
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Title
        title_label = Label(
            text='Journal',
            font_size=30,
            size_hint_y=0.08,
            color=(1, 1, 1, 1),
            bold=True
        )
        main_layout.add_widget(title_label)

        # Questions section - larger area
        questions_box = BoxLayout(orientation='vertical', size_hint_y=0.6, spacing=5)

        # Question text
        self.question_label = Label(
            text="",
            font_size=18,
            color=(0.8, 0.8, 1, 1),
            size_hint_y=0.15,
            halign='center',
            valign='middle'
        )
        questions_box.add_widget(self.question_label)

        # Answer area - increased height
        self.answer_container = BoxLayout(
            orientation='vertical',
            size_hint_y=0.7,
            padding=5
        )
        questions_box.add_widget(self.answer_container)

        # Navigation buttons
        nav_box = BoxLayout(size_hint_y=0.15, spacing=10)
        self.prev_btn = Button(
            text='Previous',
            disabled=True,
            background_color=(0.4, 0.4, 0.4, 1),
            color=(1, 1, 1, 1)
        )
        self.prev_btn.bind(on_press=self.prev_question)

        self.next_btn = Button(
            text='Next',
            background_color=(0.3, 0.3, 0.3, 1),
            color=(1, 1, 1, 1)
        )
        self.next_btn.bind(on_press=self.next_question)

        nav_box.add_widget(self.prev_btn)
        nav_box.add_widget(Label(text=f"1/1", size_hint_x=0.3))  # Placeholder for counter
        nav_box.add_widget(self.next_btn)
        questions_box.add_widget(nav_box)

        main_layout.add_widget(questions_box)

        # Journal entry section - reduced height
        journal_box = BoxLayout(orientation='vertical', size_hint_y=0.25, spacing=5)
        journal_box.add_widget(Label(
            text='Daily Reflection:',
            font_size=18,
            color=(0.8, 0.8, 1, 1),
            size_hint_y=0.2
        ))

        self.journal_input = TextInput(
            multiline=True,
            size_hint_y=0.8,
            foreground_color=(1, 1, 1, 1),
            background_color=(0.15, 0.15, 0.15, 1),
            hint_text='Write your thoughts here...',
            padding=10
        )
        journal_box.add_widget(self.journal_input)
        main_layout.add_widget(journal_box)

        # Save button
        save_btn = Button(
            text='Save Journal',
            size_hint_y=0.07,
            color=(1, 1, 1, 1),
            background_color=(0.2, 0.4, 0.8, 1),
            font_size=18
        )
        save_btn.bind(on_press=self.save_journal)
        main_layout.add_widget(save_btn)

        self.add_widget(main_layout)

    def create_question_widgets(self):
        self.answer_widgets = {}
        self.question_widgets = []
        questions = self.app.data["reminder_settings"].get("journal_questions", [])

        for i, question in enumerate(questions):
            if question['type'] == 'FreeText':
                text_input = TextInput(
                    multiline=True,
                    size_hint_y=0.9,
                    foreground_color=(1, 1, 1, 1),
                    background_color=(0.15, 0.15, 0.15, 1)
                )
                self.answer_widgets[i] = text_input
                self.question_widgets.append({
                    "widget": text_input,
                    "text": question['text']
                })

            elif question['type'] == 'MultipleChoice':
                options_layout = GridLayout(
                    cols=1,
                    spacing=5,
                    size_hint_y=0.9
                )
                option_widgets = []
                for option in question['options']:
                    option_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
                    checkbox = CheckBox(
                        group=f"group{id(question)}",
                        size_hint_x=0.1
                    )
                    option_row.add_widget(checkbox)
                    option_label = Label(
                        text=option,
                        size_hint_x=0.9,
                        color=(1, 1, 1, 1),
                        halign='left'
                    )
                    option_row.add_widget(option_label)
                    options_layout.add_widget(option_row)
                    option_widgets.append(checkbox)

                self.answer_widgets[i] = option_widgets
                self.question_widgets.append({
                    "widget": options_layout,
                    "text": question['text']
                })

            elif question['type'] == 'MultipleChoiceOrText':
                options_layout = GridLayout(
                    cols=1,
                    spacing=5,
                    size_hint_y=0.9
                )
                option_widgets = []
                for j, option in enumerate(question['options']):
                    option_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
                    checkbox = CheckBox(
                        group=f"group{id(question)}",
                        size_hint_x=0.1
                    )
                    option_row.add_widget(checkbox)
                    option_label = Label(
                        text=option,
                        size_hint_x=0.9,
                        color=(1, 1, 1, 1),
                        halign='left'
                    )
                    option_row.add_widget(option_label)
                    options_layout.add_widget(option_row)
                    option_widgets.append(checkbox)

            elif question['type'] == 'MultipleChoiceOrText':
                options_layout = GridLayout(
                    cols=1,
                    spacing=5,
                    size_hint_y=0.9
                )
                option_widgets = []

                # Add multiple choice options
                for option in question['options']:
                    option_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
                    checkbox = CheckBox(
                        group=f"group{id(question)}",
                        size_hint_x=0.1
                    )
                    option_row.add_widget(checkbox)
                    option_label = Label(
                        text=option,
                        size_hint_x=0.9,
                        color=(1, 1, 1, 1),
                        halign='left'
                    )
                    option_row.add_widget(option_label)
                    options_layout.add_widget(option_row)
                    option_widgets.append(checkbox)

                # Add free text input
                other_row = BoxLayout(orientation='vertical', size_hint_y=None, height=150)
                other_label = Label(text="Additional notes:", size_hint_y=0.2, color=(1, 1, 1, 1))
                other_input = TextInput(
                    size_hint_y=0.8,
                    multiline=True,
                    foreground_color=(1, 1, 1, 1),
                    background_color=(0.15, 0.15, 0.15, 1)
                )
                other_row.add_widget(other_label)
                other_row.add_widget(other_input)
                options_layout.add_widget(other_row)

                self.answer_widgets[i] = (option_widgets, other_input)
                self.question_widgets.append({
                    "widget": options_layout,
                    "text": question['text']
                })

                # Add "Other" option
                other_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
                other_checkbox = CheckBox(
                    group=f"group{id(question)}",
                    size_hint_x=0.1
                )
                other_label = Label(text="Other:", size_hint_x=0.2, color=(1, 1, 1, 1))
                other_input = TextInput(
                    size_hint_x=0.7,
                    multiline=False,
                    foreground_color=(1, 1, 1, 1),
                    background_color=(0.15, 0.15, 0.15, 1)
                )
                other_row.add_widget(other_checkbox)
                other_row.add_widget(other_label)
                other_row.add_widget(other_input)
                options_layout.add_widget(other_row)
                option_widgets.append(other_checkbox)

                self.answer_widgets[i] = (option_widgets, other_input)
                self.question_widgets.append({
                    "widget": options_layout,
                    "text": question['text']
                })

    def show_question(self, index):
        """Display the current question"""
        if not self.question_widgets or index < 0 or index >= len(self.question_widgets):
            return

        # Update navigation buttons
        self.prev_btn.disabled = (index == 0)
        self.next_btn.text = "Next" if index < len(self.question_widgets) - 1 else "Finish"

        # Update counter
        counter = self.prev_btn.parent.children[1]  # Get the counter label
        counter.text = f"{index + 1}/{len(self.question_widgets)}"

        # Update question text
        self.question_label.text = self.question_widgets[index]["text"]

        # Update answer container
        self.answer_container.clear_widgets()
        self.answer_container.add_widget(self.question_widgets[index]["widget"])

    def next_question(self, instance):
        if self.current_question_idx < len(self.question_widgets) - 1:
            self.current_question_idx += 1
            self.show_question(self.current_question_idx)
        else:
            # On last question, "Finish" button does nothing
            pass

    def prev_question(self, instance):
        if self.current_question_idx > 0:
            self.current_question_idx -= 1
            self.show_question(self.current_question_idx)

    def on_pre_enter(self):
        today_str = datetime.today().strftime("%Y-%m-%d")
        self.create_question_widgets()
        self.current_question_idx = 0
        self.show_question(0)

        # Check if journal data exists
        if today_str in self.app.data["day_logs"]:
            journal_data = self.app.data["day_logs"][today_str].get("Journal", {})

            # Handle both string and structured journal data
            if isinstance(journal_data, str):
                self.journal_input.text = journal_data
            else:
                self.journal_input.text = journal_data.get("free_text", "")

                # Load answers to questions if available
                if "answers" in journal_data:
                    answers = journal_data["answers"]
                    for answer in answers:
                        idx = answer["question_idx"]
                        if idx < len(self.answer_widgets):
                            q_type = self.app.data["reminder_settings"]["journal_questions"][idx]["type"]

                            if q_type == "FreeText":
                                self.answer_widgets[idx].text = answer.get("text", "")
                        elif q_type == "MultipleChoice":
                            selected_idx = answer.get("selected", -1)
                            if 0 <= selected_idx < len(self.answer_widgets[idx]):
                                self.answer_widgets[idx][selected_idx].active = True
                        elif q_type == "MultipleChoiceOrText":
                            selected_idx = answer.get("selected", -1)
                            if 0 <= selected_idx < len(self.answer_widgets[idx][0]):  # option_widgets
                                self.answer_widgets[idx][0][selected_idx].active = True
                                # If "Other" was selected, load the text
                                if selected_idx == len(self.answer_widgets[idx][0]) - 1:
                                    self.answer_widgets[idx][1].text = answer.get("text", "")

    def save_journal(self, instance):
        today_str = datetime.today().strftime("%Y-%m-%d")
        if today_str not in self.app.data["day_logs"]:
            self.app.show_popup("Please submit your habits first!")
            return

        questions = self.app.data["reminder_settings"]["journal_questions"]
        answers = []

        for i, question in enumerate(questions):
            if question['type'] == 'FreeText':
                answer_text = self.answer_widgets[i].text.strip()
                if not answer_text:
                    self.app.show_popup(f"Please answer: {question['text']}")
                    self.current_question_idx = i
                    self.show_question(i)
                    return
                answers.append({
                    "question_idx": i,
                    "text": answer_text
                })

            elif question['type'] == 'MultipleChoice':
                selected_idx = -1
                for j in range(len(question['options'])):
                    if self.answer_widgets[i][j].active:
                        selected_idx = j
                        break

                if selected_idx == -1:
                    self.app.show_popup(f"Please select an option for: {question['text']}")
                    self.current_question_idx = i
                    self.show_question(i)
                    return

                answers.append({
                    "question_idx": i,
                    "selected": selected_idx
                })

            elif question['type'] == 'MultipleChoiceOrText':
                option_widgets, other_input = self.answer_widgets[i]
                selected_idx = -1
                for j in range(len(option_widgets)):
                    if option_widgets[j].active:
                        selected_idx = j
                        break

                if selected_idx == -1:
                    self.app.show_popup(f"Please select an option for: {question['text']}")
                    self.current_question_idx = i
                    self.show_question(i)
                    return

                # Handle "Other" selection
                if selected_idx == len(option_widgets) - 1:  # "Other" option is selected
                    other_text = other_input.text.strip()
                    if not other_text:
                        self.app.show_popup(f"Please write your answer for 'Other' in: {question['text']}")
                        self.current_question_idx = i
                        self.show_question(i)
                        return
                    answers.append({
                        "question_idx": i,
                        "selected": selected_idx,
                        "text": other_text
                    })
                else:
                    answers.append({
                        "question_idx": i,
                        "selected": selected_idx
                    })

            elif question['type'] == 'MultipleChoiceOrText':
                option_widgets, other_input = self.answer_widgets[i]
                selected_indices = []

                # Get selected options
                for j, checkbox in enumerate(option_widgets):
                    if checkbox.active:
                        selected_indices.append(j)

                # Get free text
                other_text = other_input.text.strip()

                answers.append({
                    "question_idx": i,
                    "selected": selected_indices,
                    "text": other_text
                })

        # Build journal data
        journal_data = {
            "free_text": self.journal_input.text.strip(),
            "answers": answers
        }

        self.app.data["day_logs"][today_str]["Journal"] = journal_data
        save_data(self.app.data)
        self.app.show_popup("Journal saved!")
        self.app.sm.current = 'audio'
        Clock.schedule_once(lambda dt: self.app.play_random_audio(), 0.1)


class JournalQuestionManager(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        Clock.schedule_once(self.build_ui, 0)

    def build_ui(self, dt=None):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        title_label = Label(text='Journal Questions', font_size=30, size_hint_y=0.1, color=(1, 1, 1, 1))
        layout.add_widget(title_label)

        # Question list
        scroll = ScrollView()
        self.questions_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.questions_layout.bind(minimum_height=self.questions_layout.setter('height'))
        self.update_questions_display()
        scroll.add_widget(self.questions_layout)
        layout.add_widget(scroll)

        # Add question button
        add_btn = Button(text='Add Question', size_hint_y=0.1, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        add_btn.bind(on_press=self.add_question_dialog)
        layout.add_widget(add_btn)

        # Back button
        back_btn = Button(text='Back to Settings', size_hint_y=0.1, color=(1, 1, 1, 1),
                          background_color=(0.3, 0.3, 0.3, 1))
        back_btn.bind(on_press=lambda x: setattr(self.app.sm, 'current', 'settings'))
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def update_questions_display(self):
        self.questions_layout.clear_widgets()
        for i, question in enumerate(self.app.data["reminder_settings"]["journal_questions"]):
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)

            # Question text
            text_label = Label(text=question['text'], size_hint_x=0.5, color=(1, 1, 1, 1))
            row.add_widget(text_label)

            # Question type
            type_label = Label(text=question['type'], size_hint_x=0.2, color=(1, 1, 1, 1))
            row.add_widget(type_label)

            # Edit button
            edit_btn = Button(text='Edit', size_hint_x=0.15, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
            edit_btn.bind(on_press=lambda instance, idx=i: self.edit_question(idx))
            row.add_widget(edit_btn)

            # Delete button
            delete_btn = Button(text='Delete', size_hint_x=0.15, color=(1, 1, 1, 1), background_color=(0.8, 0, 0, 1))
            delete_btn.bind(on_press=lambda instance, idx=i: self.confirm_delete_question(idx))
            row.add_widget(delete_btn)

            self.questions_layout.add_widget(row)

    def add_question_dialog(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text='Add New Question', color=(1, 1, 1, 1)))

        # Question text input
        self.question_text = TextInput(hint_text='Question text', multiline=False,
                                       foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        content.add_widget(self.question_text)

        # Question type
        type_layout = BoxLayout(orientation='horizontal', spacing=10)
        type_layout.add_widget(Label(text='Type:', color=(1, 1, 1, 1)))
        self.question_type = Spinner(
            text='FreeText',
            values=['FreeText', 'MultipleChoice', 'MultipleChoiceOrText'],  # Add new type
            size_hint_x=0.7,
            color=(1, 1, 1, 1),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        type_layout.add_widget(self.question_type)
        content.add_widget(type_layout)

        # Options container
        self.options_container = BoxLayout(orientation='vertical', spacing=5)
        content.add_widget(self.options_container)
        self.question_type.bind(text=self.update_options_ui)

        # Buttons
        btn_layout = BoxLayout(spacing=10)
        save_btn = Button(text='Save', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        cancel_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Add Question', content=content, size_hint=(0.8, 0.6))

        save_btn.bind(on_press=lambda x: self.save_question(popup))
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def update_options_ui(self, spinner, value):
        self.options_container.clear_widgets()
        if value in ['MultipleChoice', 'MultipleChoiceOrText']:
            options_label = Label(text='Options (one per line):', color=(1, 1, 1, 1))
            self.options_container.add_widget(options_label)

            # Add hint for merged type
            if value == 'MultipleChoiceOrText':
                hint = Label(
                    text="(User can select multiple options AND add free text)",
                    font_size='12sp',
                    color=(0.8, 0.8, 0.8, 1)
                )
                self.options_container.add_widget(hint)

            self.options_input = TextInput(
                hint_text='Option 1\nOption 2\nOption 3',
                multiline=True,
                size_hint_y=0.7,
                foreground_color=(1, 1, 1, 1),
                background_color=(0.15, 0.15, 0.15, 1)
            )
            self.options_container.add_widget(self.options_input)

    def save_question(self, popup):
        text = self.question_text.text.strip()
        if not text:
            self.app.show_popup("Question text cannot be empty!")
            return

        question = {
            "text": text,
            "type": self.question_type.text,
            "options": []
        }

        if question["type"] in ['MultipleChoice', 'MultipleChoiceOrText']:
            options = self.options_input.text.split('\n')
            question["options"] = [opt.strip() for opt in options if opt.strip()]

            if not question["options"]:
                self.app.show_popup("Multiple choice questions must have options!")
                return

        self.app.data["reminder_settings"]["journal_questions"].append(question)
        save_data(self.app.data)
        self.update_questions_display()
        popup.dismiss()
        self.app.show_popup("Question added!")

    def edit_question(self, index):
        # Get the questions from the correct path in the data structure
        questions = self.app.data["reminder_settings"]["journal_questions"]
        if index < len(questions):
            question = questions[index]
            # Create edit dialog
            content = BoxLayout(orientation='vertical', spacing=10, padding=10)
            content.add_widget(Label(text='Edit Question:', color=(1, 1, 1, 1)))

            self.edit_text = TextInput(text=question['text'], multiline=False,
                                       foreground_color=(1, 1, 1, 1),
                                       background_color=(0.15, 0.15, 0.15, 1))
            content.add_widget(self.edit_text)

            button_layout = BoxLayout(size_hint_y=0.3, spacing=10)
            save_btn = Button(text='Save', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
            cancel_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
            button_layout.add_widget(save_btn)
            button_layout.add_widget(cancel_btn)
            content.add_widget(button_layout)

            popup = Popup(title='Edit Question', content=content, size_hint=(0.8, 0.4))

            def save_changes(instance):
                new_text = self.edit_text.text.strip()
                if new_text:
                    # Update the question text in the correct location
                    self.app.data["reminder_settings"]["journal_questions"][index]['text'] = new_text
                    save_data(self.app.data)
                    self.update_questions_display()
                    popup.dismiss()
                    self.app.show_popup("Question updated!")
                else:
                    self.app.show_popup("Question text cannot be empty!")

            save_btn.bind(on_press=save_changes)
            cancel_btn.bind(on_press=popup.dismiss)
            popup.open()
        else:
            self.app.show_popup("Invalid question index")

    def confirm_delete_question(self, index):
        question = self.app.data["reminder_settings"]["journal_questions"][index]
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f'Delete this question?\n\n"{question["text"]}"',
                                 color=(1, 1, 1, 1)))

        btn_layout = BoxLayout(spacing=10, size_hint_y=0.4)
        yes_btn = Button(text='Delete', color=(1, 1, 1, 1), background_color=(0.8, 0, 0, 1))
        no_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Confirm Deletion', content=content, size_hint=(0.8, 0.4))

        def delete_question(instance):
            # Remove the question
            del self.app.data["reminder_settings"]["journal_questions"][index]
            save_data(self.app.data)
            self.update_questions_display()
            popup.dismiss()
            self.app.show_popup("Question deleted!")

        yes_btn.bind(on_press=delete_question)
        no_btn.bind(on_press=popup.dismiss)
        popup.open()



class SelectableLabel(RecycleDataViewBehavior, Label):
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)
    entry_date = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

class SelectableRecycleBoxLayout(FocusBehavior, LayoutSelectionBehavior, RecycleBoxLayout):
    pass


class HistoryScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.filter_text = ""
        Clock.schedule_once(self.build_ui, 0)

    def build_ui(self, dt=None):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        title_label = Label(text='History', font_size=30, size_hint_y=0.1, color=(1, 1, 1, 1))
        layout.add_widget(title_label)

        # Search bar
        search_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        self.search_input = TextInput(hint_text='Search journal entries...', multiline=False,
                                      foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        self.search_input.bind(text=self.on_search_text)
        search_btn = Button(text='Search', size_hint_x=0.3, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        search_btn.bind(on_press=self.update_history)
        search_layout.add_widget(self.search_input)
        search_layout.add_widget(search_btn)
        layout.add_widget(search_layout)

        # History container with expandable entries
        scroll = ScrollView(size_hint_y=0.7)
        self.history_container = BoxLayout(
            orientation='vertical',
            spacing=10,
            size_hint_y=None,
            padding=5
        )
        self.history_container.bind(minimum_height=self.history_container.setter('height'))
        scroll.add_widget(self.history_container)
        layout.add_widget(scroll)

        # Buttons
        btn_layout = BoxLayout(size_hint_y=0.1, spacing=10)
        refresh_btn = Button(text='Refresh', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        refresh_btn.bind(on_press=self.refresh_history)
        back_btn = Button(text='Back', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        back_btn.bind(on_press=lambda x: setattr(self.app.sm, 'current', 'habits'))
        btn_layout.add_widget(refresh_btn)
        btn_layout.add_widget(back_btn)
        layout.add_widget(btn_layout)

        self.add_widget(layout)

    def on_search_text(self, instance, value):
        self.filter_text = value.lower()
        self.update_history()

    def on_pre_enter(self):
        self.update_history()

    def update_history(self, dt=None):
        self.history_container.clear_widgets()
        day_logs = self.app.data.get("day_logs", {})

        for date, log in sorted(day_logs.items(), reverse=True):
            if self.filter_text and not self.matches_search(log, self.filter_text):
                continue

            entry_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=100,  # Initial height
                padding=5
            )
            entry_box.entry_data = log  # Store log data
            entry_box.expanded = False  # Track expansion state

            # Header (always visible)
            header = BoxLayout(size_hint_y=None, height=40)
            date_label = Label(text=date, size_hint_x=0.6, color=(1, 1, 1, 1), halign='left')

            # Store reference to expand button directly
            expand_btn = Button(text='▼', size_hint_x=0.2, font_size=16)
            entry_box.expand_btn = expand_btn  # Store reference here

            header.add_widget(date_label)
            header.add_widget(Label(text=f"Day: {log.get('DayNumber', '')}", size_hint_x=0.2))
            header.add_widget(expand_btn)
            entry_box.add_widget(header)

            # Details (hidden by default)
            details_container = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=0  # Start collapsed
            )
            entry_box.details_container = details_container
            entry_box.add_widget(details_container)

            # Bind button here after creating it
            expand_btn.bind(on_press=lambda instance, box=entry_box: self.toggle_expand(box))

            self.history_container.add_widget(entry_box)

    def toggle_expand(self, entry_box):
        entry_box.expanded = not entry_box.expanded
        if entry_box.expanded:
            # Expand and load details
            entry_box.details_container.height = 300
            entry_box.height = 400
            entry_box.expand_btn.text = '▲'  # Use stored reference
            self.populate_details(entry_box.details_container, entry_box.entry_data)
        else:
            # Collapse
            entry_box.details_container.height = 0
            entry_box.height = 100
            entry_box.expand_btn.text = '▼'  # Use stored reference

    def populate_details(self, container, log):
        container.clear_widgets()

        # Create scrollable content area
        details_scroll = ScrollView()
        content_layout = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=10
        )
        content_layout.bind(minimum_height=content_layout.setter('height'))

        # Add log details
        details = [
            f"Completion: {log.get('Completion', '')}%",
            f"Energy: {log.get('Energy', '')}",
            "Habits:"
        ]

        # Add habits with status indicators
        habits = log.get("Habits", {})
        for habit, completed in habits.items():
            status = "✓" if completed else "✗"
            details.append(f"  {status} {habit}")

        # Add journal if exists
        journal = log.get("Journal", {})
        if journal:
            details.append("\nJournal:")
            if isinstance(journal, str):
                details.append(journal)
            else:
                # Free text
                if journal.get("free_text"):
                    details.append(f"  {journal['free_text']}")

                # Questions
                for i, answer in enumerate(journal.get("answers", [])):
                    question = self.app.data["reminder_settings"]["journal_questions"][answer["question_idx"]]
                    q_text = question["text"]

                    if question["type"] == "FreeText":
                        details.append(f"  Q: {q_text}")
                        details.append(f"    A: {answer.get('text', '')}")
                    elif question["type"] == "MultipleChoice":
                        details.append(f"  Q: {q_text}")
                        selected_idx = answer.get("selected", -1)
                        if 0 <= selected_idx < len(question["options"]):
                            details.append(f"    A: {question['options'][selected_idx]}")
                    elif question["type"] == "MultipleChoiceOrText":
                        details.append(f"  Q: {q_text}")
                        selected_idx = answer.get("selected", -1)
                        if 0 <= selected_idx < len(question["options"]):
                            if selected_idx == len(question["options"]) - 1:  # "Other" option
                                details.append(f"    A: {answer.get('text', '')}")
                            else:
                                details.append(f"    A: {question['options'][selected_idx]}")
                    elif question["type"] == "MultipleChoiceOrText":
                        details.append(f"  Q: {q_text}")

                        # Show selected options
                        if answer.get("selected"):
                            selected_text = ", ".join(question['options'][i] for i in answer["selected"])
                            details.append(f"    Selected: {selected_text}")

                        # Show additional text
                        if answer.get("text"):
                            details.append(f"    Notes: {answer['text']}")

        # Create content label
        content_label = Label(
            text="\n".join(details),
            size_hint_y=None,
            text_size=(Window.width * 0.95, None),
            halign='left',
            valign='top',
            color=(0.9, 0.9, 0.9, 1)
        )
        content_label.bind(texture_size=content_label.setter('size'))
        content_layout.add_widget(content_label)
        details_scroll.add_widget(content_layout)
        container.add_widget(details_scroll)

    def matches_search(self, log, search_text):
        search_text = search_text.lower()

        # Check basic fields
        basic_fields = ["Completion", "Energy", "DayNumber"]
        for field in basic_fields:
            if field in log and search_text in str(log[field]).lower():
                return True

        # Check habits
        habits = log.get("Habits", {})
        for habit, completed in habits.items():
            if search_text in habit.lower():
                return True

        # Check journal
        journal = log.get("Journal", {})
        if journal:
            if isinstance(journal, str):
                if search_text in journal.lower():
                    return True
            else:
                # Free text
                if "free_text" in journal and search_text in journal["free_text"].lower():
                    return True

                # Questions and answers
                for answer in journal.get("answers", []):
                    question_idx = answer.get("question_idx", -1)
                    if 0 <= question_idx < len(self.app.data["reminder_settings"]["journal_questions"]):
                        question = self.app.data["reminder_settings"]["journal_questions"][question_idx]
                        # Check question text
                        if search_text in question["text"].lower():
                            return True

                        # Check answer
                        if question["type"] == "FreeText":
                            if "text" in answer and search_text in answer["text"].lower():
                                return True
                        elif question["type"] == "MultipleChoice":
                            selected_idx = answer.get("selected", -1)
                            if 0 <= selected_idx < len(question["options"]):
                                if search_text in question["options"][selected_idx].lower():
                                    return True
                        elif question["type"] == "MultipleChoiceOrText":
                            selected_idx = answer.get("selected", -1)
                            if 0 <= selected_idx < len(question["options"]):
                                if selected_idx == len(question["options"]) - 1:  # "Other" option
                                    if "text" in answer and search_text in answer["text"].lower():
                                        return True
                                else:
                                    if search_text in question["options"][selected_idx].lower():
                                        return True

        return False

    def refresh_history(self, instance):
        self.update_history()


class SettingsScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        Clock.schedule_once(self.build_ui, 0)

    def build_ui(self, dt=None):
        scroll = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        title_label = Label(text='Settings', font_size=30, size_hint_y=None, height=60, color=(1, 1, 1, 1))
        layout.add_widget(title_label)

        # Habits Management Section
        habits_title = Label(text='Manage Habits', font_size=20, size_hint_y=None, height=50, color=(1, 1, 1, 1))
        layout.add_widget(habits_title)

        self.habits_layout = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None)
        self.habits_layout.bind(minimum_height=self.habits_layout.setter('height'))
        self.update_habits_display()
        layout.add_widget(self.habits_layout)

        add_habit_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.new_habit_input = TextInput(hint_text='New Habit', multiline=False, size_hint_x=0.5,
                                         foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        self.points_input = TextInput(hint_text='Points', input_filter='int', multiline=False, size_hint_x=0.2,
                                      foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        add_btn = Button(text='Add', size_hint_x=0.3, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        add_btn.bind(on_press=self.add_habit)
        add_habit_layout.add_widget(self.new_habit_input)
        add_habit_layout.add_widget(self.points_input)
        add_habit_layout.add_widget(add_btn)
        layout.add_widget(add_habit_layout)

        # Reminder Settings Section
        reminder_title = Label(text='Reminder Settings', font_size=20, size_hint_y=None, height=50, color=(1, 1, 1, 1))
        layout.add_widget(reminder_title)

        # Master toggle
        reminder_toggle_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        reminder_toggle_layout.add_widget(Label(text='Enable Reminders:', size_hint_x=0.5, color=(1, 1, 1, 1)))

        self.reminder_toggle = ToggleButton(
            text='Off',
            state='normal',
            size_hint_x=0.3,
            color=(1, 1, 1, 1),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        if self.app.data["reminder_settings"]["enabled"]:
            self.reminder_toggle.state = 'down'
            self.reminder_toggle.text = 'On'
        self.reminder_toggle.bind(state=self.toggle_reminders)
        reminder_toggle_layout.add_widget(self.reminder_toggle)
        layout.add_widget(reminder_toggle_layout)

        # Time picker
        time_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        time_layout.add_widget(Label(text='Reminder Time:', size_hint_x=0.5, color=(1, 1, 1, 1)))
        self.time_spinner = Spinner(
            text=self.app.data["reminder_settings"]["time"],
            values=[f"{h:02d}:{m:02d}" for h in range(0, 24) for m in [0, 15, 30, 45]],
            size_hint_x=0.5,
            color=(1, 1, 1, 1),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        self.time_spinner.bind(text=self.update_reminder_time)
        time_layout.add_widget(self.time_spinner)
        layout.add_widget(time_layout)

        # Per-habit toggles
        habit_reminder_title = Label(text='Habits to Remind:', font_size=16, size_hint_y=None, height=40,
                                     color=(1, 1, 1, 1))
        layout.add_widget(habit_reminder_title)

        scroll_habits = ScrollView(size_hint_y=0.3)
        self.habit_reminder_layout = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.habit_reminder_layout.bind(minimum_height=self.habit_reminder_layout.setter('height'))
        self.update_habit_reminders()
        scroll_habits.add_widget(self.habit_reminder_layout)
        layout.add_widget(scroll_habits)

        # Add Journal Questions section
        jq_title = Label(text='Journal Questions', font_size=20, size_hint_y=None, height=50, color=(1, 1, 1, 1))
        layout.add_widget(jq_title)

        jq_btn = Button(
            text='Manage Questions',
            size_hint_y=None,
            height=50,
            color=(1, 1, 1, 1),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        jq_btn.bind(on_press=lambda x: setattr(self.app.sm, 'current', 'journal_questions'))
        layout.add_widget(jq_btn)

        # Export/Import Section
        export_import_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        export_btn = Button(text='Export Data', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        export_btn.bind(on_press=self.export_data)
        import_btn = Button(text='Import Data', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        import_btn.bind(on_press=self.import_data)
        export_import_layout.add_widget(export_btn)
        export_import_layout.add_widget(import_btn)
        layout.add_widget(export_import_layout)

        # Reset Section
        reset_btn = Button(text='Reset All Data', size_hint_y=None, height=50, color=(1, 1, 1, 1),
                           background_color=(0.3, 0.3, 0.3, 1))
        reset_btn.bind(on_press=self.confirm_reset)
        layout.add_widget(reset_btn)

        # Add Notification History section
        history_title = Label(
            text='Notification History',
            font_size=20,
            size_hint_y=None,
            height=50,
            color=(1, 1, 1, 1)
        )
        layout.add_widget(history_title)

        # Clear history button
        clear_btn = Button(
            text='Clear History',
            size_hint_y=None,
            height=40,
            color=(1, 1, 1, 1),
            background_color=(0.8, 0, 0, 1)
        )
        clear_btn.bind(on_press=self.clear_notification_history)
        layout.add_widget(clear_btn)

        # Notification history scroll view
        history_scroll = ScrollView(size_hint_y=0.4)
        self.history_container = GridLayout(
            cols=1,
            spacing=5,
            size_hint_y=None,
            padding=5
        )
        self.history_container.bind(minimum_height=self.history_container.setter('height'))
        self.update_notification_history()
        history_scroll.add_widget(self.history_container)
        layout.add_widget(history_scroll)

        scroll.add_widget(layout)
        self.add_widget(scroll)

    def update_notification_history(self):
        """Populate notification history display"""
        self.history_container.clear_widgets()

        if not self.app.data.get("notification_history"):
            self.history_container.add_widget(
                Label(text="No notifications yet", color=(1, 1, 1, 1))
            )
            return

        for note in reversed(self.app.data["notification_history"]):
            timestamp = note.get("timestamp", "")
            ntype = note.get("type", "Notification")
            message = note.get("message", "")

            # Create formatted display
            box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=80,
                padding=5
            )

            # Header with timestamp and type
            header = BoxLayout(size_hint_y=0.4)
            header.add_widget(Label(
                text=timestamp,
                color=(0.8, 0.8, 0.8, 1),
                size_hint_x=0.7,
                halign='left'
            ))
            header.add_widget(Label(
                text=ntype,
                color=(0.5, 0.8, 1, 1),
                size_hint_x=0.3,
                halign='right'
            ))
            box.add_widget(header)

            # Notification message
            msg_label = Label(
                text=message,
                color=(1, 1, 1, 1),
                size_hint_y=0.6,
                halign='left',
                valign='top',
                text_size=(Window.width * 0.9, None)
            )
            box.add_widget(msg_label)

            self.history_container.add_widget(box)

    def clear_notification_history(self, instance):
        """Clear notification history"""
        self.app.data["notification_history"] = []
        save_data(self.app.data)
        self.update_notification_history()

    def is_habit_enabled(self, habit_name):
        habits_enabled = self.app.data["reminder_settings"]["habits_enabled"]
        # Enable by default if not explicitly set
        return habits_enabled.get(habit_name, True)

    def toggle_habit_reminder(self, habit_name, state):
        self.app.data["reminder_settings"]["habits_enabled"][habit_name] = (state == 'down')
        save_data(self.app.data)
        self.update_habit_reminders()

    def toggle_reminders(self, instance, state):
        enabled = (state == 'down')
        self.app.data["reminder_settings"]["enabled"] = enabled
        instance.text = 'On' if enabled else 'Off'
        save_data(self.app.data)

        if enabled:
            self.app.schedule_daily_reminder()

    def update_reminder_time(self, spinner, text):
        self.app.data["reminder_settings"]["time"] = text
        save_data(self.app.data)
        self.app.schedule_daily_reminder()

    def add_habit(self, instance):
        new_habit_name = self.new_habit_input.text.strip()
        points_text = self.points_input.text.strip()
        if new_habit_name and points_text:
            try:
                points = int(points_text)
                if points <= 0:
                    raise ValueError
                if any(h["name"] == new_habit_name for h in self.app.data["habits"]):
                    self.app.show_popup("Habit already exists!")
                else:
                    new_habit = {"name": new_habit_name, "points": points}
                    self.app.data["habits"].append(new_habit)
                    save_data(self.app.data)
                    self.update_habits_display()
                    self.app.habits_screen.build_ui()
                    self.app.show_popup(f"Habit '{new_habit_name}' added with {points} points!")
                    self.new_habit_input.text = ""
                    self.points_input.text = ""
            except ValueError:
                self.app.show_popup("Please enter a valid positive integer for points!")
        else:
            self.app.show_popup("Please enter both habit name and points!")

    def confirm_remove_habit(self, habit_name):
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text=f'Are you sure you want to remove "{habit_name}"?', color=(1, 1, 1, 1)))
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        yes_btn = Button(text='Yes', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        no_btn = Button(text='No', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        button_layout.add_widget(yes_btn)
        button_layout.add_widget(no_btn)
        content.add_widget(button_layout)
        popup = Popup(title='Confirm Removal', content=content, size_hint=(0.8, 0.4))
        yes_btn.bind(on_press=lambda x: self.do_remove_habit(habit_name, popup))
        no_btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def do_remove_habit(self, habit_name, popup):
        self.app.data["habits"] = [h for h in self.app.data["habits"] if h["name"] != habit_name]
        save_data(self.app.data)
        self.update_habits_display()
        self.app.habits_screen.build_ui()
        self.app.show_popup(f"Habit '{habit_name}' removed!")
        popup.dismiss()

    def update_habits_display(self):
        self.habits_layout.clear_widgets()
        for habit in self.app.data.get("habits", []):
            habit_name = habit["name"]
            habit_points = habit["points"]
            habit_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
            label = Label(text=f"{habit_name} ({habit_points} pts)", font_size=12, text_size=(None, None),
                          color=(1, 1, 1, 1))
            habit_row.add_widget(label)

            # Edit button
            edit_btn = Button(text='Edit', size_hint_x=0.2, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
            edit_btn.bind(on_press=lambda x, h=habit_name: self.edit_habit(h))
            habit_row.add_widget(edit_btn)

            # Remove button
            remove_btn = Button(text='Remove', size_hint_x=0.3, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
            remove_btn.bind(on_press=lambda x, h=habit_name: self.confirm_remove_habit(h))
            habit_row.add_widget(remove_btn)

            self.habits_layout.add_widget(habit_row)

    def export_data_to_file(self, filename):
        try:
            export_dir = os.path.dirname(FILE)
            os.makedirs(export_dir, exist_ok=True)
            export_file = os.path.join(export_dir, filename)
            with open(export_file, 'w') as f:
                json.dump(self.app.data, f, indent=2)
            return True
        except Exception as e:
            print(f"Export error: {str(e)}")
            return False

    def export_data(self, instance):
        if self.export_data_to_file('habit_builder_export.json'):
            self.app.show_popup("Data exported successfully!")
        else:
            self.app.show_popup("Export failed!")

    def import_data(self, instance):
        try:
            import_dir = os.path.dirname(FILE)
            import_file = os.path.join(import_dir, 'habit_builder_export.json')
            if os.path.exists(import_file):
                with open(import_file, 'r') as f:
                    imported_data = json.load(f)
                    default_data = get_default_data()
                    for key in default_data:
                        if key not in imported_data:
                            imported_data[key] = default_data[key]
                    self.app.data = imported_data
                    self.app.day_num = get_day_number(self.app.data["start_date"])
                save_data(self.app.data)
                self.app.show_popup("Data imported successfully!")
                self.update_habits_display()
                self.app.habits_screen.build_ui()
            else:
                self.app.show_popup("Export file not found!")
        except Exception as e:
            self.app.show_popup(f"Import error: {str(e)}")

    def confirm_reset(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(
            Label(text='Are you sure you want to reset all data?\nThis cannot be undone.', color=(1, 1, 1, 1)))
        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        yes_btn = Button(text='Yes, Reset', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        no_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        button_layout.add_widget(yes_btn)
        button_layout.add_widget(no_btn)
        content.add_widget(button_layout)
        popup = Popup(title='Confirm Reset', content=content, size_hint=(0.8, 0.4))

        def reset_data(btn):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f'habit_builder_backup_{timestamp}.json'
            if self.export_data_to_file(backup_file):
                print(f"Data backed up to {backup_file}")
            else:
                print("Failed to backup data")
            self.app.data = get_default_data()
            self.app.day_num = 1
            save_data(self.app.data)
            self.update_habits_display()
            popup.dismiss()
            self.app.show_popup("All data has been reset!")

        yes_btn.bind(on_press=reset_data)
        no_btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def edit_habit(self, habit_name, popup=None):
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text=f'Edit "{habit_name}"', color=(1, 1, 1, 1)))

        edit_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        self.edit_habit_input = TextInput(text=habit_name, multiline=False, size_hint_x=0.5,
                                          foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        current_points = next((h["points"] for h in self.app.data["habits"] if h["name"] == habit_name), 5)
        self.edit_points_input = TextInput(text=str(current_points), input_filter='int', multiline=False,
                                           size_hint_x=0.2, foreground_color=(1, 1, 1, 1),
                                           background_color=(0.15, 0.15, 0.15, 1))
        edit_layout.add_widget(self.edit_habit_input)
        edit_layout.add_widget(self.edit_points_input)
        content.add_widget(edit_layout)

        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        save_btn = Button(text='Save', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        cancel_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        button_layout.add_widget(save_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)

        edit_popup = Popup(title='Edit Habit', content=content, size_hint=(0.8, 0.4))

        def save_edit(instance):
            new_name = self.edit_habit_input.text.strip()
            points_text = self.edit_points_input.text.strip()
            if new_name and points_text:
                try:
                    points = int(points_text)
                    if points <= 0:
                        raise ValueError
                    for habit in self.app.data["habits"]:
                        if habit["name"] == habit_name:
                            habit["name"] = new_name
                            habit["points"] = points
                            break
                    save_data(self.app.data)
                    self.update_habits_display()
                    self.app.habits_screen.build_ui()
                    edit_popup.dismiss()
                    if popup:
                        popup.dismiss()
                    self.app.show_popup(f"Habit updated to '{new_name}' with {points} points!")
                except ValueError:
                    self.app.show_popup("Please enter a valid positive integer for points!")
            else:
                self.app.show_popup("Please enter both habit name and points!")

        save_btn.bind(on_press=save_edit)
        cancel_btn.bind(on_press=edit_popup.dismiss)
        edit_popup.open()

    def update_habit_reminders(self):
        self.habit_reminder_layout.clear_widgets()
        for habit in self.app.data["habits"]:
            habit_name = habit["name"]
            row = BoxLayout(size_hint_y=None, height=50, spacing=10)

            # Habit label
            row.add_widget(Label(text=habit_name, color=(1, 1, 1, 1), size_hint_x=0.7))

            # Toggle button
            toggle = ToggleButton(
                text='On' if self.is_habit_enabled(habit_name) else 'Off',
                state='down' if self.is_habit_enabled(habit_name) else 'normal',
                size_hint_x=0.3,
                color=(1, 1, 1, 1),
                background_color=(0.3, 0.3, 0.3, 1)
            )
            toggle.bind(state=lambda instance, state, h=habit_name: self.toggle_habit_reminder(h, state))
            row.add_widget(toggle)

            self.habit_reminder_layout.add_widget(row)


class AudioPlayerScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.current_sound = None
        self.audio_files = []
        self.current_category = "All"
        self.load_audio_list()
        self.volume = 0.7
        self.timer_event = None
        Clock.schedule_once(self.build_ui, 0)

    def build_ui(self, dt=None):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Title
        title_label = Label(text='Audio Player', font_size=30, size_hint_y=0.1, color=(1, 1, 1, 1))
        layout.add_widget(title_label)

        # Category filter
        category_layout = BoxLayout(size_hint_y=0.1, spacing=5)
        category_label = Label(text='Category:', size_hint_x=0.3, color=(1, 1, 1, 1))
        category_layout.add_widget(category_label)

        self.category_spinner = Spinner(
            text=self.current_category,
            values=["All"] + self.app.data["audio_playback"]["categories"],
            size_hint_x=0.7,
            color=(1, 1, 1, 1),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        self.category_spinner.bind(text=self.filter_by_category)
        category_layout.add_widget(self.category_spinner)
        layout.add_widget(category_layout)

        # Now playing info
        now_playing_box = BoxLayout(orientation='vertical', size_hint_y=0.3, spacing=5)
        self.now_playing_label = Label(text='Not playing', font_size=16, halign='center', color=(1, 1, 1, 1))
        now_playing_box.add_widget(self.now_playing_label)

        # Time display
        self.time_label = Label(text='00:00 / 00:00', font_size=14, halign='center', color=(1, 1, 1, 1))
        now_playing_box.add_widget(self.time_label)

        # Control buttons
        control_box = BoxLayout(size_hint_y=0.2, spacing=10)

        # Volume button
        self.volume_btn = Button(text='Volume', size_hint_x=0.2, color=(1, 1, 1, 1),
                                 background_color=(0.3, 0.3, 0.3, 1))
        self.volume_btn.bind(on_press=self.show_volume_popup)
        control_box.add_widget(self.volume_btn)

        # Previous button
        prev_btn = Button(text='Previous', size_hint_x=0.2, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        prev_btn.bind(on_press=self.prev_audio)
        control_box.add_widget(prev_btn)

        # Play/Pause button
        self.play_btn = Button(text='Play', size_hint_x=0.2, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        self.play_btn.bind(on_press=self.toggle_play)
        control_box.add_widget(self.play_btn)

        # Next button
        next_btn = Button(text='Next', size_hint_x=0.2, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        next_btn.bind(on_press=self.next_audio)
        control_box.add_widget(next_btn)

        # Manager button
        manager_btn = Button(text='Manage', size_hint_x=0.2, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        manager_btn.bind(on_press=lambda x: setattr(self.app.sm, 'current', 'audio_manager'))
        control_box.add_widget(manager_btn)

        now_playing_box.add_widget(control_box)
        layout.add_widget(now_playing_box)

        # Audio list
        scroll = ScrollView(size_hint_y=0.5)
        self.audio_list = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.audio_list.bind(minimum_height=self.audio_list.setter('height'))
        self.update_audio_list()
        scroll.add_widget(self.audio_list)
        layout.add_widget(scroll)

        # Navigation buttons
        nav_box = BoxLayout(size_hint_y=0.1, spacing=10)
        add_audio_btn = Button(text='Add Audio', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        add_audio_btn.bind(on_press=self.show_add_audio_dialog)
        nav_box.add_widget(add_audio_btn)

        back_btn = Button(text='Back to Habits', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        back_btn.bind(on_press=lambda x: setattr(self.app.sm, 'current', 'habits'))
        nav_box.add_widget(back_btn)

        layout.add_widget(nav_box)

        self.add_widget(layout)
        self.timer_event = Clock.schedule_interval(self.update_timer, 0.1)

    def on_leave(self, *args):
        if self.timer_event:
            self.timer_event.cancel()
        if self.current_sound:
            self.current_sound.stop()

    def update_timer(self, dt):
        if self.current_sound and self.current_sound.state == 'play':
            position = self.current_sound.get_pos()
            mins, secs = divmod(position, 60)
            total_mins, total_secs = divmod(self.current_sound.length, 60)
            self.time_label.text = f'{int(mins):02d}:{int(secs):02d} / {int(total_mins):02d}:{int(total_secs):02d}'

    def filter_by_category(self, spinner, text):
        self.current_category = text
        self.update_audio_list()

    def load_audio_list(self):
        audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio')
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)

        # Create category subdirectories
        for category in self.app.data["audio_playback"]["categories"]:
            os.makedirs(os.path.join(audio_dir, category), exist_ok=True)

        self.audio_files = []
        if self.current_category == "All":
            for category in self.app.data["audio_playback"]["categories"]:
                category_dir = os.path.join(audio_dir, category)
                if os.path.exists(category_dir):
                    files = [os.path.join(category, f) for f in os.listdir(category_dir)
                             if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
                    self.audio_files.extend(files)
        else:
            category_dir = os.path.join(audio_dir, self.current_category)
            if os.path.exists(category_dir):
                self.audio_files = [os.path.join(self.current_category, f) for f in os.listdir(category_dir)
                                    if f.lower().endswith(('.mp3', '.wav', '.ogg'))]

        self.audio_files.sort()

    def update_audio_list(self):
        self.audio_list.clear_widgets()
        for audio_file in self.audio_files:
            btn = Button(
                text=os.path.basename(audio_file),
                size_hint_y=None,
                height=50,
                color=(1, 1, 1, 1),
                background_color=(0.3, 0.3, 0.3, 1)
            )
            btn.bind(
                on_press=lambda x, f=audio_file: self.play_audio(f)
            )
            self.audio_list.add_widget(btn)

    def play_audio(self, filename):
        if self.current_sound:
            self.current_sound.stop()
            self.current_sound.unload()

        # Reset pause position if it exists
        if hasattr(self, 'paused_position'):
            del self.paused_position

        audio_path = os.path.join(os.path.dirname(FILE), 'motivation_audio', filename)
        self.current_sound = SoundLoader.load(audio_path)

        if self.current_sound:
            self.current_sound.volume = self.volume
            self.current_sound.play()
            self.play_btn.text = 'Pause'
            self.now_playing_label.text = f'Now playing: {os.path.basename(filename)}'

            # Add completion callback
            def on_complete(sound):
                # Save data after playback completes
                self.app.data["day_logs"][datetime.today().strftime("%Y-%m-%d")]["AudioPlayed"] = filename
                save_data(self.app.data)

            self.current_sound.bind(on_stop=on_complete)

            # Set initial time display
            if self.current_sound.length > 0:
                mins, secs = divmod(self.current_sound.length, 60)
                self.time_label.text = f'00:00 / {int(mins):02d}:{int(secs):02d}'
            else:
                self.time_label.text = '00:00 / --:--'

            # Store the filename for reference
            self.current_filename = filename

            # Update the timer immediately
            self.update_timer(0)
        else:
            self.now_playing_label.text = 'Error loading audio file'
            self.time_label.text = '00:00 / 00:00'

    def show_volume_popup(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)

        volume_label = Label(text=f'Volume: {int(self.volume * 100)}%', size_hint_y=0.2)
        content.add_widget(volume_label)

        volume_slider = Slider(min=0, max=1, value=self.volume, size_hint_y=0.4)

        def set_volume(instance, value):
            self.volume = value
            volume_label.text = f'Volume: {int(value * 100)}%'
            if self.current_sound:
                self.current_sound.volume = value

        volume_slider.bind(value=set_volume)
        content.add_widget(volume_slider)

        close_btn = Button(text='Close', size_hint_y=0.2)
        popup = Popup(title='Volume Control', content=content, size_hint=(0.7, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        content.add_widget(close_btn)

        popup.open()

    def toggle_play(self, instance):
        if self.current_sound:
            if self.current_sound.state == 'play':
                # Store position before pausing
                self.paused_position = self.current_sound.get_pos()
                self.current_sound.stop()
                self.play_btn.text = 'Play'
            else:
                # Resume from stored position
                if hasattr(self, 'paused_position'):
                    self.current_sound.seek(self.paused_position)
                self.current_sound.play()
                self.play_btn.text = 'Pause'

    def prev_audio(self, instance):
        if not self.audio_files:
            return

        current_index = -1
        if self.current_sound and self.current_sound.source:
            current_file = os.path.basename(self.current_sound.source)
            for i, f in enumerate(self.audio_files):
                if os.path.basename(f) == current_file:
                    current_index = i
                    break

        prev_index = (current_index - 1) % len(self.audio_files)
        self.play_audio(self.audio_files[prev_index])

    def next_audio(self, instance):
        if not self.audio_files:
            return

        current_index = -1
        if self.current_sound and self.current_sound.source:
            current_file = os.path.basename(self.current_sound.source)
            for i, f in enumerate(self.audio_files):
                if os.path.basename(f) == current_file:
                    current_index = i
                    break

        next_index = (current_index + 1) % len(self.audio_files)
        self.play_audio(self.audio_files[next_index])

    def get_downloads_path(self):
        if platform == 'android':
            try:
                Environment = autoclass('android.os.Environment')
                downloads_dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS)
                return downloads_dir.getAbsolutePath()
            except Exception:
                try:
                    return primary_external_storage_path()
                except Exception:
                    return os.path.expanduser("~")
        else:
            return os.path.join(os.path.expanduser("~"), "Downloads")

    def show_add_audio_dialog(self, instance):
        content = BoxLayout(orientation='vertical', spacing=10)

        # Category selection
        cat_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        cat_layout.add_widget(Label(text='Category:', size_hint_x=0.3, color=(1, 1, 1, 1)))
        self.add_category_spinner = Spinner(
            text=self.app.data["audio_playback"]["categories"][0],
            values=self.app.data["audio_playback"]["categories"],
            size_hint_x=0.7,
            color=(1, 1, 1, 1),
            background_color=(0.3, 0.3, 0.3, 1)
        )
        cat_layout.add_widget(self.add_category_spinner)
        content.add_widget(cat_layout)

        # File chooser with multiselect enabled
        file_chooser = FileChooserListView(filters=['*.mp3', '*.wav', '*.ogg'])
        file_chooser.path = self.get_downloads_path()
        file_chooser.multiselect = True  # Enable multiple file selection
        content.add_widget(file_chooser)

        # Status label
        self.add_status_label = Label(text='Select files to add', color=(1, 1, 1, 1))
        content.add_widget(self.add_status_label)

        button_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)
        add_btn = Button(text='Add Selected', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        cancel_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        button_layout.add_widget(add_btn)
        button_layout.add_widget(cancel_btn)
        content.add_widget(button_layout)

        popup = Popup(title='Select Audio Files', content=content, size_hint=(0.9, 0.9))

        def add_audio(instance):
            if file_chooser.selection:
                category = self.add_category_spinner.text
                dest_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio', category)
                os.makedirs(dest_dir, exist_ok=True)

                success_count = 0
                error_count = 0

                for src in file_chooser.selection:
                    try:
                        dest = os.path.join(dest_dir, os.path.basename(src))

                        # Check if file already exists
                        if os.path.exists(dest):
                            self.add_status_label.text = f'Skipped existing: {os.path.basename(src)}'
                            error_count += 1
                            continue

                        # Copy file
                        import shutil
                        shutil.copy2(src, dest)
                        success_count += 1
                        self.add_status_label.text = f'Added: {os.path.basename(src)}'

                    except Exception as e:
                        error_count += 1
                        self.add_status_label.text = f'Error adding {os.path.basename(src)}: {str(e)}'

                # Final status message
                self.add_status_label.text = (
                    f'Added {success_count} files, skipped {error_count} files. '
                    'Press "Add Selected" again to add more or "Close" to finish.'
                )

                # Refresh audio list if successful
                if success_count > 0:
                    self.load_audio_list()
                    self.update_audio_list()
            else:
                self.add_status_label.text = 'Please select at least one file!'

        add_btn.bind(on_press=add_audio)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()


class AudioManagerScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        Clock.schedule_once(self.build_ui, 0)

    def build_ui(self, dt=None):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Title
        title_label = Label(text='Audio Manager', font_size=30, size_hint_y=0.1, color=(1, 1, 1, 1))
        layout.add_widget(title_label)

        # Category management
        category_box = BoxLayout(orientation='vertical', size_hint_y=0.3, spacing=5)
        category_title = Label(text='Categories', font_size=20, size_hint_y=0.1, color=(1, 1, 1, 1))
        category_box.add_widget(category_title)

        # Category list
        scroll_cat = ScrollView(size_hint_y=0.7)
        self.category_list = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.category_list.bind(minimum_height=self.category_list.setter('height'))
        self.update_category_list()
        scroll_cat.add_widget(self.category_list)
        category_box.add_widget(scroll_cat)
        layout.add_widget(category_box)

        # Add category
        add_cat_box = BoxLayout(size_hint_y=0.1, spacing=10)
        self.new_cat_input = TextInput(hint_text='New category', multiline=False,
                                       foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        add_cat_box.add_widget(self.new_cat_input)

        add_cat_btn = Button(text='Add', size_hint_x=0.3, color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        add_cat_btn.bind(on_press=self.add_category)
        add_cat_box.add_widget(add_cat_btn)
        layout.add_widget(add_cat_box)

        # Audio files management
        audio_box = BoxLayout(orientation='vertical', size_hint_y=0.5, spacing=5)
        audio_title = Label(text='Audio Files', font_size=20, size_hint_y=0.1, color=(1, 1, 1, 1))
        audio_box.add_widget(audio_title)

        # Audio file list
        scroll_audio = ScrollView(size_hint_y=0.9)
        self.audio_list = GridLayout(cols=1, spacing=5, size_hint_y=None)
        self.audio_list.bind(minimum_height=self.audio_list.setter('height'))
        self.update_audio_list()
        scroll_audio.add_widget(self.audio_list)
        audio_box.add_widget(scroll_audio)
        layout.add_widget(audio_box)

        # Back button
        back_btn = Button(text='Back to Player', size_hint_y=0.1, color=(1, 1, 1, 1),
                          background_color=(0.3, 0.3, 0.3, 1))
        back_btn.bind(on_press=lambda x: setattr(self.app.sm, 'current', 'audio'))
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def update_category_list(self):
        self.category_list.clear_widgets()
        for category in self.app.data["audio_playback"]["categories"]:
            row = BoxLayout(size_hint_y=None, height=50)

            # Category name
            cat_label = Button(
                text=category,
                color=(1, 1, 1, 1),
                background_color=(0.3, 0.3, 0.3, 1),
                size_hint_x=0.7
            )
            cat_label.bind(on_press=lambda x, c=category: self.rename_category(c))
            row.add_widget(cat_label)

            # Delete button
            del_btn = Button(
                text='Delete',
                color=(1, 1, 1, 1),
                background_color=(0.8, 0, 0, 1),
                size_hint_x=0.3
            )
            del_btn.bind(on_press=lambda x, c=category: self.confirm_delete_category(c))
            row.add_widget(del_btn)

            self.category_list.add_widget(row)

    def update_audio_list(self):
        self.audio_list.clear_widgets()
        audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio')

        for category in self.app.data["audio_playback"]["categories"]:
            cat_dir = os.path.join(audio_dir, category)
            if not os.path.exists(cat_dir):
                continue

            for file in os.listdir(cat_dir):
                if file.lower().endswith(('.mp3', '.wav', '.ogg')):
                    row = BoxLayout(size_hint_y=None, height=50)

                    # File name
                    file_label = Button(
                        text=f"{category}/{file}",
                        color=(1, 1, 1, 1),
                        background_color=(0.3, 0.3, 0.3, 1),
                        size_hint_x=0.7
                    )
                    file_label.bind(on_press=lambda x, f=file, c=category: self.rename_audio(c, f))
                    row.add_widget(file_label)

                    # Delete button
                    del_btn = Button(
                        text='Delete',
                        color=(1, 1, 1, 1),
                        background_color=(0.8, 0, 0, 1),
                        size_hint_x=0.3
                    )
                    del_btn.bind(on_press=lambda x, f=file, c=category: self.confirm_delete_audio(c, f))
                    row.add_widget(del_btn)

                    self.audio_list.add_widget(row)

    def add_category(self, instance):
        new_cat = self.new_cat_input.text.strip()
        if new_cat:
            if new_cat in self.app.data["audio_playback"]["categories"]:
                self.app.show_popup("Category already exists!")
            else:
                # Create directory for new category
                audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio')
                os.makedirs(os.path.join(audio_dir, new_cat), exist_ok=True)

                # Update data
                self.app.data["audio_playback"]["categories"].append(new_cat)
                save_data(self.app.data)

                # Update UI
                self.update_category_list()
                self.new_cat_input.text = ""
                self.app.show_popup(f"Category '{new_cat}' added!")
        else:
            self.app.show_popup("Please enter a category name!")

    def rename_category(self, old_name):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f'Rename "{old_name}" to:', color=(1, 1, 1, 1)))

        new_name_input = TextInput(text=old_name, multiline=False,
                                   foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        content.add_widget(new_name_input)

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        save_btn = Button(text='Save', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        cancel_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Rename Category', content=content, size_hint=(0.8, 0.4))

        def save_changes(instance):
            new_name = new_name_input.text.strip()
            if new_name and new_name != old_name:
                if new_name in self.app.data["audio_playback"]["categories"]:
                    self.app.show_popup("Category name already exists!")
                else:
                    # Update directory name
                    audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio')
                    os.rename(
                        os.path.join(audio_dir, old_name),
                        os.path.join(audio_dir, new_name)
                    )

                    # Update data
                    index = self.app.data["audio_playback"]["categories"].index(old_name)
                    self.app.data["audio_playback"]["categories"][index] = new_name
                    save_data(self.app.data)

                    # Update UI
                    self.update_category_list()
                    self.update_audio_list()
                    popup.dismiss()
                    self.app.show_popup(f"Category renamed to '{new_name}'!")
            else:
                self.app.show_popup("Please enter a valid new name!")

        save_btn.bind(on_press=save_changes)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def confirm_delete_category(self, category):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f'Delete "{category}" and all its contents?', color=(1, 1, 1, 1)))

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        yes_btn = Button(text='Delete', color=(1, 1, 1, 1), background_color=(0.8, 0, 0, 1))
        no_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Confirm Delete', content=content, size_hint=(0.8, 0.4))

        def delete_category(instance):
            # Delete directory and contents
            audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio')
            cat_dir = os.path.join(audio_dir, category)

            import shutil
            if os.path.exists(cat_dir):
                shutil.rmtree(cat_dir)

            # Update data
            self.app.data["audio_playback"]["categories"].remove(category)
            save_data(self.app.data)

            # Update UI
            self.update_category_list()
            self.update_audio_list()
            popup.dismiss()
            self.app.show_popup(f"Category '{category}' deleted!")

        yes_btn.bind(on_press=delete_category)
        no_btn.bind(on_press=popup.dismiss)
        popup.open()

    def rename_audio(self, category, filename):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f'Rename "{filename}" to:', color=(1, 1, 1, 1)))

        new_name_input = TextInput(text=os.path.splitext(filename)[0], multiline=False,
                                   foreground_color=(1, 1, 1, 1), background_color=(0.15, 0.15, 0.15, 1))
        content.add_widget(new_name_input)

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        save_btn = Button(text='Save', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        cancel_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        btn_layout.add_widget(save_btn)
        btn_layout.add_widget(cancel_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Rename Audio', content=content, size_hint=(0.8, 0.4))

        def save_changes(instance):
            new_name = new_name_input.text.strip()
            if new_name:
                audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio')
                old_path = os.path.join(audio_dir, category, filename)
                ext = os.path.splitext(filename)[1]
                new_path = os.path.join(audio_dir, category, f"{new_name}{ext}")

                try:
                    os.rename(old_path, new_path)
                    self.update_audio_list()
                    popup.dismiss()
                    self.app.show_popup("Audio file renamed!")
                except Exception as e:
                    self.app.show_popup(f"Error: {str(e)}")
            else:
                self.app.show_popup("Please enter a valid name!")

        save_btn.bind(on_press=save_changes)
        cancel_btn.bind(on_press=popup.dismiss)
        popup.open()

    def confirm_delete_audio(self, category, filename):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        content.add_widget(Label(text=f'Delete "{filename}"?', color=(1, 1, 1, 1)))

        btn_layout = BoxLayout(size_hint_y=0.3, spacing=10)
        yes_btn = Button(text='Delete', color=(1, 1, 1, 1), background_color=(0.8, 0, 0, 1))
        no_btn = Button(text='Cancel', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        btn_layout.add_widget(yes_btn)
        btn_layout.add_widget(no_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Confirm Delete', content=content, size_hint=(0.8, 0.4))

        def delete_audio(instance):
            audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio')
            file_path = os.path.join(audio_dir, category, filename)

            if os.path.exists(file_path):
                os.remove(file_path)
                self.update_audio_list()
                popup.dismiss()
                self.app.show_popup("Audio file deleted!")
            else:
                self.app.show_popup("File not found!")

        yes_btn.bind(on_press=delete_audio)
        no_btn.bind(on_press=popup.dismiss)
        popup.open()


class HabitBuilderApp(App):
    def build(self):
        Window.clearcolor = (0.2, 0.2, 0.2, 1)
        if platform == 'android':
            try:
                permissions = [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
                if not all(check_permission(p) for p in permissions):
                    request_permissions(permissions)
            except Exception as e:
                print(f"Permission error: {e}")

        self.title = "Habit Builder"
        self.data = load_data()
        self.day_num = get_day_number(self.data["start_date"])
        self.sm = ScreenManager()

        # Create screens
        self.habits_screen = HabitsScreen(self, name='habits')
        self.journal_screen = JournalScreen(self, name='journal')
        self.history_screen = HistoryScreen(self, name='history')
        self.settings_screen = SettingsScreen(self, name='settings')
        self.audio_screen = AudioPlayerScreen(self, name='audio')
        self.audio_manager_screen = AudioManagerScreen(self, name='audio_manager')

        # Add screens to manager
        self.sm.add_widget(self.habits_screen)
        self.sm.add_widget(self.journal_screen)
        self.sm.add_widget(self.history_screen)
        self.sm.add_widget(self.settings_screen)
        self.sm.add_widget(self.audio_screen)
        self.sm.add_widget(self.audio_manager_screen)

        # Navigation bar
        nav_layout = BoxLayout(size_hint_y=0.12, padding=2, spacing=2)

        habits_btn = Button(text='Habits', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        habits_btn.bind(on_press=lambda x: setattr(self.sm, 'current', 'habits'))
        nav_layout.add_widget(habits_btn)

        journal_btn = Button(text='Journal', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        journal_btn.bind(on_press=lambda x: setattr(self.sm, 'current', 'journal'))
        nav_layout.add_widget(journal_btn)

        history_btn = Button(text='History', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        history_btn.bind(on_press=lambda x: setattr(self.sm, 'current', 'history'))
        nav_layout.add_widget(history_btn)

        settings_btn = Button(text='Settings', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        settings_btn.bind(on_press=lambda x: setattr(self.sm, 'current', 'settings'))
        nav_layout.add_widget(settings_btn)

        audio_btn = Button(text='Audio', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.3, 1))
        audio_btn.bind(on_press=lambda x: setattr(self.sm, 'current', 'audio'))
        nav_layout.add_widget(audio_btn)

        # Main layout
        main_layout = BoxLayout(orientation='vertical')
        main_layout.add_widget(self.sm)
        main_layout.add_widget(nav_layout)

        # Initialize this after loading data
        self.journal_questions_screen = JournalQuestionManager(self, name='journal_questions')
        self.sm.add_widget(self.journal_questions_screen)

        # Schedule reminders on app start
        Clock.schedule_once(lambda dt: self.schedule_daily_reminder(), 1)
        return main_layout

    def schedule_daily_reminder(self):
        # Cancel any existing scheduled reminders
        if hasattr(self, 'reminder_event'):
            self.reminder_event.cancel()

        # Only schedule if reminders are enabled
        if not self.data["reminder_settings"]["enabled"]:
            return

        # Parse reminder time
        try:
            reminder_time = self.data["reminder_settings"]["time"]
            hour, minute = map(int, reminder_time.split(':'))
        except:
            hour, minute = 20, 0  # Default to 8 PM

        # Calculate next reminder time
        now = datetime.now()
        next_reminder = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # If time already passed today, schedule for tomorrow
        if now > next_reminder:
            next_reminder += timedelta(days=1)

        # Calculate seconds until reminder
        seconds_until = (next_reminder - now).total_seconds()

        # Schedule the reminder
        self.reminder_event = Clock.schedule_once(
            lambda dt: self.show_reminder(),
            seconds_until
        )

    def show_reminder(self):
        # Skip if snooze is active
        if time.time() < self.data["reminder_settings"]["snooze_until"]:
            self.schedule_daily_reminder()
            return

        # Skip if already logged today
        today_str = datetime.today().strftime("%Y-%m-%d")
        if today_str in self.data.get("day_logs", {}):
            self.schedule_daily_reminder()
            return

        # Prepare motivational message based on streak status
        streak = self.data.get("streak", 0)
        last_streak = self.data["reminder_settings"]["last_streak"]
        message = "Time to log your habits!"

        if streak == 0 and last_streak > 0:
            message = "Your streak was broken! Start a new one today!"
        elif streak == 0 and self.data.get("last_log_date", ""):
            last_log = datetime.strptime(self.data["last_log_date"], "%Y-%m-%d")
            days_missed = (datetime.today() - last_log).days
            if days_missed > 1:
                message = f"You've missed {days_missed} days. It's never too late to restart!"

        # Update streak tracking
        self.data["reminder_settings"]["last_streak"] = streak
        self.data["reminder_settings"]["last_reminder"] = time.time()
        save_data(self.data)

        # Show reminder popup
        self.show_reminder_popup(message)

        # Check for weekly reflection
        if self.should_show_weekly_reflection():
            Clock.schedule_once(lambda dt: self.show_weekly_reflection(), 2)

        # Reschedule for next day
        self.schedule_daily_reminder()

    def show_reminder_popup(self, message):
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text=message, color=(1, 1, 1, 1)))

        btn_layout = BoxLayout(spacing=10, size_hint_y=0.4)
        log_btn = Button(text='Log Now', color=(1, 1, 1, 1), background_color=(0, 0.5, 0, 1))
        snooze_btn = Button(text='Snooze (1 hr)', color=(1, 1, 1, 1), background_color=(0.5, 0.5, 0, 1))
        dismiss_btn = Button(text='Dismiss', color=(1, 1, 1, 1), background_color=(0.8, 0, 0, 1))

        btn_layout.add_widget(log_btn)
        btn_layout.add_widget(snooze_btn)
        btn_layout.add_widget(dismiss_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Reminder', content=content, size_hint=(0.8, 0.4), auto_dismiss=False)

        def log_notification(self, ntype, message):
            """Record notification in history"""
            if "notification_history" not in self.data:
                self.data["notification_history"] = []

            # Limit history to 50 entries
            if len(self.data["notification_history"]) >= 50:
                self.data["notification_history"].pop(0)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.data["notification_history"].append({
                "timestamp": timestamp,
                "type": ntype,
                "message": message
            })
            save_data(self.data)

            # Refresh history display if we're on settings screen
            if hasattr(self.settings_screen, 'update_notification_history'):
                self.settings_screen.update_notification_history()

        def show_reminder_popup(self, message):
            # Log the notification
            self.log_notification("Daily Reminder", message)
            # ... rest of existing implementation ...

        def show_weekly_reflection(self):
            # Log the notification
            self.log_notification("Weekly Reflection", "Time for weekly reflection!")

        def log_now(instance):
            popup.dismiss()
            self.sm.current = 'habits'

        def snooze(instance):
            self.data["reminder_settings"]["snooze_until"] = time.time() + 3600  # 1 hour
            save_data(self.data)
            popup.dismiss()
            self.schedule_daily_reminder()

        def dismiss(instance):
            popup.dismiss()

        log_btn.bind(on_press=log_now)
        snooze_btn.bind(on_press=snooze)
        dismiss_btn.bind(on_press=dismiss)

        popup.open()

    def should_show_weekly_reflection(self):
        # Show weekly reflection on Sundays
        return datetime.today().weekday() == 6  # Sunday is 6

    def show_weekly_reflection(self):
        content = BoxLayout(orientation='vertical', spacing=10)
        content.add_widget(Label(text="It's the end of the week! Review your progress?",
                                 color=(1, 1, 1, 1)))

        btn_layout = BoxLayout(spacing=10, size_hint_y=0.4)
        history_btn = Button(text='View History', color=(1, 1, 1, 1), background_color=(0, 0.5, 0, 1))
        journal_btn = Button(text='Write Journal', color=(1, 1, 1, 1), background_color=(0.3, 0.3, 0.8, 1))
        later_btn = Button(text='Later', color=(1, 1, 1, 1), background_color=(0.8, 0, 0, 1))

        btn_layout.add_widget(history_btn)
        btn_layout.add_widget(journal_btn)
        btn_layout.add_widget(later_btn)
        content.add_widget(btn_layout)

        popup = Popup(title='Weekly Reflection', content=content, size_hint=(0.8, 0.4), auto_dismiss=False)

        def go_to_history(instance):
            popup.dismiss()
            self.sm.current = 'history'

        def go_to_journal(instance):
            popup.dismiss()
            self.sm.current = 'journal'

        def dismiss(instance):
            popup.dismiss()

        history_btn.bind(on_press=go_to_history)
        journal_btn.bind(on_press=go_to_journal)
        later_btn.bind(on_press=dismiss)

        popup.open()

    def submit_log(self, log):
        today_str = datetime.today().strftime("%Y-%m-%d")
        if today_str in self.data.get("day_logs", {}):
            self.show_popup("You've already logged today!")
            return

        earned = calculate_points(log, self.data["habits"])
        streak_bonus = update_streak(self.data)
        total = earned + streak_bonus

        self.data["total_points"] = self.data.get("total_points", 0) + total
        update_levels_and_milestones(self.data, self)

        if "day_logs" not in self.data:
            self.data["day_logs"] = {}

        self.data["day_logs"][today_str] = {
            "DayNumber": self.day_num,
            "Completion": log.get("Completion", "100"),
            "Habits": log.get("Habits", {}),
            "Energy": log.get("Energy", "5"),
            "Journal": "",
            "Points": total,
            "StreakBonus": streak_bonus
        }

        save_data(self.data)
        self.day_num = get_day_number(self.data["start_date"])
        message = random.choice(MOTIVATIONAL_MESSAGES)
        self.show_popup(message)
        Clock.schedule_once(lambda dt: setattr(self.sm, 'current', 'journal'), 1)

    def play_random_audio(self):
        today = datetime.today().strftime("%Y-%m-%d")

        # Skip if audio already played today
        if today in self.data["day_logs"] and "AudioPlayed" in self.data["day_logs"][today]:
            return

        # Get available categories
        categories = self.data["audio_playback"]["categories"]
        if not categories:
            return

        # Select a category that hasn't been played recently
        cat_history = self.data["audio_playback"].setdefault("category_history", {})
        file_history = self.data["audio_playback"].setdefault("file_history", {})

        # Reset history if all categories have been played
        if len(cat_history) >= len(categories):
            cat_history.clear()
            file_history.clear()

        # Select category with least recent playback
        available_cats = [c for c in categories if c not in cat_history]
        category = random.choice(available_cats) if available_cats else random.choice(categories)

        # Get audio files in selected category
        audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio', category)
        if not os.path.exists(audio_dir):
            return

        audio_files = [f for f in os.listdir(audio_dir)
                       if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        if not audio_files:
            return

        # Get unplayed files in category
        played_in_cat = file_history.get(category, [])
        available_files = [f for f in audio_files if f not in played_in_cat]

        if not available_files:
            # Reset category history if all played
            available_files = audio_files
            played_in_cat = []

        # Select random file
        audio_file = random.choice(available_files)

        # Update history
        cat_history[category] = today
        played_in_cat.append(audio_file)
        file_history[category] = played_in_cat

        # Update day log (will be saved after playback completes)
        self.data["day_logs"][today]["AudioPlayed"] = f"{category}/{audio_file}"

        # Play audio
        full_path = os.path.join(category, audio_file)
        self.audio_screen.play_audio(full_path)

    def show_popup(self, message):
        content = Label(text=message, color=(1, 1, 1, 1))
        popup = Popup(title='Notification', content=content, size_hint=(0.8, 0.4), auto_dismiss=True)
        popup.open()

    def play_random_audio(self):
        today = datetime.today().strftime("%Y-%m-%d")

        # Skip if already played today
        if today in self.data["day_logs"] and "AudioPlayed" in self.data["day_logs"][today]:
            return

        # Get available categories
        categories = self.data["audio_playback"]["categories"]
        if not categories:
            return

        # Select a random category
        category = random.choice(categories)

        # Get files in category
        audio_dir = os.path.join(os.path.dirname(FILE), 'motivation_audio', category)
        if not os.path.exists(audio_dir):
            return

        audio_files = [f for f in os.listdir(audio_dir)
                       if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
        if not audio_files:
            return

        # Get playback history for category
        history = self.data["audio_playback"].setdefault("category_history", {})
        played_files = history.setdefault(category, [])

        # Get unplayed files
        unplayed = [f for f in audio_files if f not in played_files]

        if not unplayed:
            # Reset if all played
            played_files.clear()
            unplayed = audio_files

        # Select random unplayed file
        audio_file = random.choice(unplayed)
        played_files.append(audio_file)

        # Save to history
        self.data["day_logs"][today]["AudioPlayed"] = f"{category}/{audio_file}"
        save_data(self.data)

        # Play the audio
        full_path = os.path.join(category, audio_file)
        self.sm.current = 'audio'
        self.audio_screen.play_audio(full_path)

    def on_audio_completed(self, instance):
        today = datetime.today().strftime("%Y-%m-%d")
        save_data(self.data)

if __name__ == '__main__':
    HabitBuilderApp().run()