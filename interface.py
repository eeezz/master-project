import json
import socket
import amaze
from amaze.simu.maze import Maze
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox,
                             QCheckBox, QComboBox, QPushButton, QSpacerItem, QSizePolicy, QCheckBox, QComboBox,
                             QApplication, QMessageBox, QDialog, QLabel, QDialogButtonBox, QLineEdit)

'''sending survey is off'''
def send_to_server(maze_strings=None, survey_answers=None):#, survey_answers):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_address = ('127.0.0.1', 12345)
        client_socket.connect(server_address)

        # See "StartWindow(QDialog)" for why below functionality gives issues when running the server.
        # Eventually get maze image of first pretrained agent
        client_socket.sendall("request_image".encode())
        response = client_socket.recv(1024).decode()
        print("Received response:", response)  # Placeholder for first maze image

        # Convert maze_strings to JSON
        maze_data = json.dumps(maze_strings)
        # Send maze data to the server
        client_socket.sendall(maze_data.encode())

        # Convert survey_answers to JSON
        survey_data = json.dumps(survey_answers)
        # Send survey data to the server
        client_socket.sendall(survey_data.encode())

        # Receive response from the server
        response = client_socket.recv(1024).decode()
        print(response)

    except Exception as e:
        QMessageBox.warning(None, 'Error', str(e))

    finally:
        client_socket.close()

class StartWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Start")
        self.resize(450, 100)
        self.label = QLabel("Click to receive the pre-trained first agent")
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.accept)
        # Below line gives issues, so is currently commented out. Undo to see what it does.
        # It must get the placeholder for an agent image, but only shows that in console. Unable to continue in UI after this.
        #self.start_button.clicked.connect(send_to_server)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.start_button)
        self.setLayout(layout)

class ProgressDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Currently in Progress")
        self.resize(450, 100)
        layout = QVBoxLayout()
        self.label = QLabel("Currently in progress...Do not close")
        layout.addWidget(self.label)
        self.setLayout(layout)

    def set_message(self, message):
        self.label.setText(message)

class SurveyDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Survey")
        self.resize(1840, 980)

        layout = QVBoxLayout()

        # Question 1: Favorite number
        label1 = QLabel("How much do you like this study on a scale of 1-5?")
        layout.addWidget(label1)

        spin_box = QSpinBox()
        spin_box.setMinimum(1)
        spin_box.setMaximum(5)
        layout.addWidget(spin_box)

        # Question 2: Agreement level
        label2 = QLabel("How much do you agree?")
        layout.addWidget(label2)

        combo_box = QComboBox()
        combo_box.addItems(["Very", "Somewhat", "Neutral", "Not so much", "Never"])
        layout.addWidget(combo_box)

        # Question 3: Study
        label3 = QLabel("What is your participant ID?")
        layout.addWidget(label3)

        line_edit = QLineEdit()
        layout.addWidget(line_edit)

        # Submit button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)
        self.setLayout(layout)
        self.spin_box = spin_box
        self.combo_box = combo_box
        self.line_edit = line_edit

    def get_survey_responses(self):
        if self.exec_() == QDialog.Accepted:
            return {
                "number": self.spin_box.value(),
                "agreement_level": self.combo_box.currentText(),
                "ParticipantID": self.line_edit.text()
            }
        else:
            return None

def what_are_the_specifications(settings): # Long name, was first meant to fetch and print maze data
    specifications = []
    # Can add traps. Do not add clues, those are fixed.
    for setting in settings:
        seed = setting["Seed"]
        size = setting["Size"]
        lures = setting["Lures"] / 100
        unicursive = setting["Unicursive"]
        start = amaze.StartLocation[setting["Start"]]
        maze_data = Maze.BuildData(
            seed=seed,
            width=size, height=size,
            unicursive=unicursive,
            rotated=True,
            start=start,
            clue=[amaze.Sign(value=1)],
            p_lure=lures,
            lure=[amaze.Sign(value=.5)],
            p_trap=0,
            trap=[]
        )
        specifications.append(maze_data.to_string())
	# Gives one maze string per line.
        print("Training with maze:", maze_data.to_string())
    return specifications

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(1840, 980)
        self.round_count = 0  # Initialize count for experiment rounds. Is a necessary line.

        self.start_window = StartWindow()
        self.start_window.exec_()

        # The main vertical layout
        main_layout = QVBoxLayout()  # Changed from horizontal layout
        self.setLayout(main_layout)

        # The horizontal layer for the first two pairs
        layout1 = QHBoxLayout()
        main_layout.addLayout(layout1)

        # Widgets for the first two mazes/variables
        self.maze_widgets1 = []
        self.variable_widgets1 = []
        for i in range(2):  # Add two sets of widgets. Now have only two mazes in total.
            maze_widget, variable_layout, widgets = self._create_maze_and_variable_widgets()
            layout1.addWidget(maze_widget)
            layout1.addLayout(variable_layout)
            self.maze_widgets1.append(maze_widget)
            self.variable_widgets1.append(widgets)

        # The horizontal layer for the last two pairs
        layout2 = QHBoxLayout()
        main_layout.addLayout(layout2)

        # Widgets for the last two mazes/variables
        self.maze_widgets2 = []
        self.variable_widgets2 = []
        for i in range(2):  # Add two sets of widgets. Now already have four mazes in total.
            maze_widget, variable_layout, widgets = self._create_maze_and_variable_widgets()
            layout2.addWidget(maze_widget)
            layout2.addLayout(variable_layout)
            self.maze_widgets2.append(maze_widget)
            self.variable_widgets2.append(widgets)

        # The continue button
        self.save_button = QPushButton("Continue")
        self.save_button.setMinimumSize(100, 20)
        self.save_button.setMaximumSize(120, 30)
        self.save_button.clicked.connect(self.save_settings)
        #self.save_button.clicked.connect(self.show_progress_dialog) don't think it's needed
        save_layout = QHBoxLayout()
        save_layout.addStretch(1)
        save_layout.addWidget(self.save_button)
        main_layout.addLayout(save_layout)  # Add button to main layout with stretching for correct placement

        # Load previous settings to each maze, if they exist. Otherwise, the default values are used.
        self.load_settings()

    def _create_maze_and_variable_widgets(self):
        # Create maze widget. Used equally for all four.
        maze_widget = amaze.MazeWidget(self._maze_data(0, 5, 0, True, amaze.StartLocation.SOUTH_WEST))

        # Create variable widgets
        variable_layout = QFormLayout()
        widgets = {}

        def _add(cls, name, signal, func=None):
            _w = cls()
            variable_layout.addRow(name, _w)
            if func is not None:
                func(_w)
            getattr(_w, signal).connect(self.reset_maze)
            widgets[name] = _w

            # Set minimum and maximum sizes for input widgets, so they no longer overtake the window
            _w.setMinimumSize(100, 20)
            _w.setMaximumSize(120, 30)

	# Create all used inputs and the type they belong to
        _add(QSpinBox, "Seed", "valueChanged")
        _add(QSpinBox, "Size", "valueChanged", lambda w: w.setRange(5, 20))
        _add(QDoubleSpinBox, "Lures", "valueChanged", lambda w: (w.setRange(0, 100), w.setSuffix("%")))
        _add(QCheckBox, "Unicursive", "clicked", lambda w: w.setChecked(True))
        _add(QComboBox, "Start", "currentTextChanged", lambda w: w.addItems([s.name for s in amaze.StartLocation]))

        return maze_widget, variable_layout, widgets

    def reset_maze(self): # Reset values each time the window is closed
        sender = self.sender()
	# Go over first layer of mazes
        for i, widgets in enumerate(self.variable_widgets1):
            if sender in widgets.values():
                maze_widget = self.maze_widgets1[i]
                maze_widget.set_maze(self._maze_data(
                    widgets["Seed"].value(),
                    widgets["Size"].value(),
                    widgets["Lures"].value() / 100,
                    widgets["Unicursive"].isChecked(),
                    amaze.StartLocation[widgets["Start"].currentText()]
                ))
                return
	# Go over last layer of mazes
        for i, widgets in enumerate(self.variable_widgets2):
            if sender in widgets.values():
                maze_widget = self.maze_widgets2[i]
                maze_widget.set_maze(self._maze_data(
                    widgets["Seed"].value(),
                    widgets["Size"].value(),
                    widgets["Lures"].value() / 100,
                    widgets["Unicursive"].isChecked(),
                    amaze.StartLocation[widgets["Start"].currentText()]
                ))
                return

    # All data. If they do not show up in the interface, use default values.
    def _maze_data(self, seed, size, p_lure, easy, start):
        return amaze.Maze.BuildData(
            seed=seed,
            width=size, height=size,
            unicursive=easy,
            rotated=True,
            start=start,
            clue=[amaze.Sign(value=1)],
            p_lure=p_lure,
            lure=[amaze.Sign(value=.5)],
            p_trap=0,
            trap=[]
        )


    def initialize_survey(self):
        self.survey_answers = None
        self.survey_dialog = SurveyDialog()
        self.survey_answers = self.survey_dialog.get_survey_responses()
        if self.survey_answers is None:
            self.close()
        else:

            send_to_server(survey_answers=self.survey_answers)

    def save_settings(self): # Sends to server and saves mazes to file.
        # Added round incrementation
        self.round_count += 1

        settings = []
        for widgets in self.variable_widgets1:
            setting = {}
            for name, widget in widgets.items():
                if isinstance(widget, QSpinBox):
                    setting[name] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    setting[name] = widget.value()
                elif isinstance(widget, QCheckBox):
                    setting[name] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    setting[name] = widget.currentText()
            settings.append(setting)

        for widgets in self.variable_widgets2:
            setting = {}
            for name, widget in widgets.items():
                if isinstance(widget, QSpinBox):
                    setting[name] = widget.value()
                elif isinstance(widget, QDoubleSpinBox):
                    setting[name] = widget.value()
                elif isinstance(widget, QCheckBox):
                    setting[name] = widget.isChecked()
                elif isinstance(widget, QComboBox):
                    setting[name] = widget.currentText()
            settings.append(setting)

        # Get maze strings
        maze_strings = what_are_the_specifications(settings)
        # Send data to server
        send_to_server(maze_strings) #, self.survey_answers) '''sending survey is off'''
        # Show progress dialog after each round
        if self.round_count < 2:
            self.show_progress_dialog()
        else:
            self.show_progress_dialog_rounds()
            # Wait for 2 seconds before continuing
            QTimer.singleShot(4000, self.initialize_survey)
	    # File gets made for UI, not for socket interaction. Can be removed, since it's only handy for prototype.
        with open("settings.json", "w") as file:
            json.dump(settings, file)

    def load_settings(self): # Load the settings if they exist when the window is opened
        try:
            with open("settings.json", "r") as file:
                settings = json.load(file)
                for i, variables in enumerate(settings):
                    if i < len(self.variable_widgets1):
                        widgets = self.variable_widgets1[i]
                    else:
                        widgets = self.variable_widgets2[i - len(self.variable_widgets1)]
                    for name, value in variables.items():
                        if name in widgets:
                            widget = widgets[name]
                            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                                widget.setValue(value)
                            elif isinstance(widget, QCheckBox):
                                widget.setChecked(value)
                            elif isinstance(widget, QComboBox):
                                index = widget.findText(value)
                                if index != -1:
                                    widget.setCurrentIndex(index)
                # Reset maze using loaded settings # and create string representations
                #what_are_the_specifications(settings) #moved
                self.reset_maze()
        except FileNotFoundError:
            # Handle the case when the settings file is not found
            pass

    def show_progress_dialog(self):
        self.progress_dialog = ProgressDialog()
        self.progress_dialog.show()
        # Simulate server processing for 2 seconds, in absence of q learning functionality for server
        QTimer.singleShot(2000, self.process_finished)
    def process_finished(self):
        self.progress_dialog.set_message("Finished, select mazes for the next round")

    def show_progress_dialog_rounds(self):
        self.progress_dialog = ProgressDialog()
        self.progress_dialog.show()
        # Simulate server processing for 2 seconds, in absence of q learning functionality for server
        QTimer.singleShot(2000, self.rounds_finished)
    def rounds_finished(self):
        self.progress_dialog.set_message("Congrats, you are done. Next you will be shown a survey.")


def main(is_test=False):
    app = amaze.application()
    window = MainWindow()
    window.show()

    if is_test:
        QTimer.singleShot(1000, lambda: window.close())
    app.exec_()

if __name__ == "__main__":
    main()






