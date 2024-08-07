import json
import socket
import amaze
import base64
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QSpinBox, QDoubleSpinBox,
                             QPushButton, QCheckBox, QComboBox,
                             QMessageBox, QDialog, QLabel, QGridLayout, QScrollArea, QLineEdit)

BUFFER_SIZE = 4096
HOST = 'localhost'# Change to ip of where server is located
PORT = 50000

def send_to_server(participant_id=None, maze_strings=None):
    try:
        server_address = (HOST, PORT)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect(server_address)

            # Combine participant ID and maze_strings into one JSON object
            data = {
                "participant_id": participant_id,
                "maze_data": maze_strings
            }
            data_json = json.dumps(data)
            client_socket.sendall(data_json.encode())

        # Receive response from the server in chunks
            response = b""
            while True:
                chunk = client_socket.recv(BUFFER_SIZE)
                if not chunk:
                    break
                response += chunk
            response = response.decode()
            return response

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        client_socket.close()


class ImageWindow(QDialog):
    def __init__(self, images, maze_strings, update_callback):
        super().__init__()
        self.setWindowTitle("Result trajectories")
        self.resize(1000, 800)
        self.update_callback = update_callback

        self.images = images
        self.maze_strings = maze_strings

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        layout = QGridLayout(content_widget)
        max_image_size = 320  # Adjust this value if need be

        # Use the images in the layout
        for index, image_data in enumerate(images):
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(image_data))
            scaled_pixmap = pixmap.scaled(max_image_size, max_image_size, Qt.KeepAspectRatio)

            label = QLabel()
            label.setPixmap(scaled_pixmap)
            layout.addWidget(label, index // 2, index % 2)  # Arrange images in a grid

            # Set the layout for the content widget
        content_widget.setLayout(layout)

        # Get user input
        instruction_label = QLabel("Enter the maze number with which you would like to continue (1-4)")
        layout.addWidget(instruction_label, len(images) // 2 + 1, 0, 1, 2)

        self.input_field = QComboBox()
        self.input_field.addItems([str(i + 1) for i in range(len(images))])
        layout.addWidget(self.input_field, len(images) // 2 + 2, 0, 1, 2)

        self.confirm_button = QPushButton("Select this maze")
        self.confirm_button.clicked.connect(self.on_confirm)
        layout.addWidget(self.confirm_button, len(images) // 2 + 3, 0, 1, 2)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

    def on_confirm(self):
        try:
            selected_index = int(self.input_field.currentText()) - 1
            if 0 <= selected_index < len(self.images):
                new_maze_string = self.maze_strings[selected_index]
                #print("Selected Maze String:", new_maze_string)
                self.update_callback(new_maze_string)
                self.accept()
            else:
                print("Invalid index")

        except ValueError:
            print("Please enter a valid number")

    def closeEvent(self, event):
        if not hasattr(self, 'participant_id') or not self.participant_id:
            QMessageBox.warning(self, "Cannot close", "Please select a maze number.")
            event.ignore()  # Ignore a user closing the window before entering their id
        else:
            event.accept()  # Closing the window with an id in the input box is also not possible

class ImageWindowRounds(QDialog): # Similar to the above, but specific to the last round
    def __init__(self, images):
        super().__init__()
        self.setWindowTitle("Final results!")
        self.resize(1000, 800)
        #(1840, 980)
        self.images = images

        # Again scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        layout = QGridLayout(content_widget)
        max_image_size = 320  # Adjust this value if need be

        for index, image_data in enumerate(images):
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(image_data))
            scaled_pixmap = pixmap.scaled(max_image_size, max_image_size, Qt.KeepAspectRatio)

            label = QLabel()
            label.setPixmap(scaled_pixmap)
            layout.addWidget(label, index // 2, index % 2)  # Arrange images in a grid
        content_widget.setLayout(layout)

        self.confirm_button = QPushButton("I'm finished, take me to the end screen")
        self.confirm_button.clicked.connect(self.accept)
        layout.addWidget(self.confirm_button)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

class StartWindow(QDialog): # Has the instructions on it
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Start")
        self.resize(450, 300)
        layout = QVBoxLayout()
        self.label = QLabel("Welcome to the experiment and thank you for your participation.\n\nPlease make sure you have an internet connection and plenty of battery. Your goal is to teach a virtual agent to become\nthe best at navigating mazes. You will do this by iteratively creating mazes for 10 rounds on which the agent can train first.\n\nIn the next screen, you will be shown an example of a poorly trained agent. The route it took is shown as dotted lines.\nPlease enter your participant ID once you have looked at the example. \n\n\n\nDuring the experiment, you will be shown 4 mazes per round. Each of these has adjustable variables, you are completely free in\nwhat and how you decide to change/leave unchanged. White arrows within a maze are clues, they can't be changed.\nGrey arrows are traps, their prevalence can be increased/decreased.\n\nWhen you feel you are done with the 4 mazes, you may click the 'Submit' button in that screen.\nA pop up is then shown to indicate the training has begun, during which you won’t need to do anything.\n\nThis training process may take a few minutes (2-10 min., depending on your submitted mazes) and you are not obligated to\nstay in front of your screen during that time. Once the popup disappears, the results of your training are shown.\nEach result shows 1 maze you created and 3 rotated versions.\n\nYou may select 1 result from the drop-down menu to take to the next round. All mazes will be updated to the one you picked.\nThen the cycle begins again for the next round. For the last round you don't need to pick a result.\nYour final test results may hold your agent's best performance yet!\n\n\n\nThe end screen will link you to a survey. Please fill this in (it's anonymous), after which you may claim your compensation.\n\nTo begin, please click 'start' to see the poorly trained example agent.\n")
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        font = self.label.font()
        font.setPointSize(11)  # Adjust the font size as needed
        self.label.setFont(font)

        layout.addWidget(self.label)
        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.accept)
        layout.addWidget(self.start_button)
        self.setLayout(layout)

class PreImageWindow(QDialog):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Trajectory of the first agent")
        layout = QVBoxLayout()

        # Create a label to display the image
        self.image_label = QLabel()
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(700, 700)  # Resize to 700x700 pixels
        self.image_label.setPixmap(scaled_pixmap)
        layout.addWidget(self.image_label)

        # Create an input field for participant ID
        self.participant_id_input = QLineEdit(self)
        self.participant_id_input.setPlaceholderText("Enter your participant ID")
        layout.addWidget(self.participant_id_input)

        # Create a button to start
        self.start_button = QPushButton("Let's start with this ID", self)
        self.start_button.clicked.connect(self.on_start)
        layout.addWidget(self.start_button)

        self.setLayout(layout)

    def on_start(self):
        self.participant_id = self.participant_id_input.text().strip()
        if not self.participant_id:
            QMessageBox.warning(self, "No Input", "Please enter your participant ID first.")
            return
        self.accept()

    def get_participant_id(self):
        return self.participant_id

    def closeEvent(self, event):
        if not hasattr(self, 'participant_id') or not self.participant_id:
            QMessageBox.warning(self, "Cannot close", "Please enter your participant ID and start.")
            event.ignore()  # Ignore a user closing the window before entering their id
        else:
            event.accept()  # Closing the window with an id in the input box is also not possible

class EndWindow(QDialog): #Has redirections to a survey
    def __init__(self, main_window):
        super().__init__()
        self.setWindowTitle("End")
        self.resize(450, 300)
        layout = QVBoxLayout()
        self.label = QLabel(
            "Thank you for participating.\n\n Please copy the following link to complete the survey. \n https://forms.gle/rest/of/a/link You may now close the program.")
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Set font size
        font = self.label.font()
        font.setPointSize(10)
        self.label.setFont(font)
        layout.addWidget(self.label)

        self.end_button = QPushButton("Close", self)
        self.end_button.clicked.connect(self.on_close)
        layout.addWidget(self.end_button)
        self.setLayout(layout)

    def on_close(self):
        self.accept()  # Closes EndWindow
        self.main_window.close()  # Closes main window. Does give error, but since it closes anyway i think it's fine. "AttributeError: 'EndWindow' object has no attribute 'main_window'"

class ProgressDialog(QDialog): # The pop up
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Training is currently in progress... Do not close")
        self.resize(700, 80)
        layout = QVBoxLayout()
        self.label = QLabel("Training is currently in progress... Do not close")
        layout.addWidget(self.label)
        self.setLayout(layout)

    def set_message(self, message):
        self.label.setText(message)

class MainWindow(QWidget): # Most important window
    def __init__(self):
        super().__init__()
        self.resize(1840, 980)
        self.round_count = 0  # Initialize count for experiment rounds.

        self.start_window = StartWindow() # Initialize the start up window
        self.start_window.exec_()

        # Show the PreImageWindow to get participant ID
        self.pre_image_window = PreImageWindow("pretrained agent image.png")  # Specify the correct image path
        if self.pre_image_window.exec_() == QDialog.Accepted:
            self.participant_id = self.pre_image_window.get_participant_id()

        main_layout = QVBoxLayout()
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

        # The continue button adjusted for width
        self.save_button = QPushButton("Submit")
        self.save_button.setMinimumSize(100, 20)
        self.save_button.setMaximumSize(120, 30)
        self.save_button.clicked.connect(self.save_settings)
        save_layout = QHBoxLayout()
        save_layout.addStretch(1)
        save_layout.addWidget(self.save_button)
        main_layout.addLayout(save_layout)

    def _create_maze_and_variable_widgets(self):
        # Create maze widget. Used equally for all four.
        maze_widget = amaze.MazeWidget(self._maze_data(0, 5, 0, True,
                            amaze.StartLocation.SOUTH_WEST))
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
        _add(QDoubleSpinBox, "Traps", "valueChanged", lambda w: (w.setRange(0, 100), w.setSuffix("%")))
        _add(QCheckBox, "Without intersections", "clicked", lambda w: w.setChecked(True))
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
                    widgets["Traps"].value() / 100,
                    widgets["Without intersections"].isChecked(),
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
                    widgets["Traps"].value() / 100,
                    widgets["Without intersections"].isChecked(),
                    amaze.StartLocation[widgets["Start"].currentText()]
                ))
                return

    # All data. If they do not show up in the interface, use default values.
    def _maze_data(self, seed, size, p_trap, easy, start):
        return amaze.Maze.BuildData(
            seed=seed,
            width=size, height=size,
            unicursive=easy,
            rotated=True,
            start=start,
            clue=[amaze.Sign(value=1)],
            p_lure=0,
            lure=[],
            p_trap=p_trap,
            trap=[amaze.Sign(value=.5)]
        )

    def save_settings(self): # Sends to server used to save mazes to file.
        # Add round incrementation
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
        maze_strings = settings

        # Show progress dialog after each round. This is where everything happens from after user submission
        if self.round_count < 10: # Adjust as needed. Currently 10 rounds have to pass.
            self.show_progress_dialog(maze_strings)
        else:
            self.show_progress_dialog_rounds(maze_strings)

    def show_progress_dialog(self, maze_strings):
        self.setEnabled(False)  # Disable the MainWindow
        self.progress_dialog = ProgressDialog()
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        response = send_to_server(self.participant_id, maze_strings)
        if response:
            try:
                images = json.loads(response)
                # Continue with the processing of images
                self.process_finished(images, maze_strings)
            except json.JSONDecodeError as e:
                print("JSON decoding error:", e)
                QMessageBox.warning(None, 'Error', "Failed to decode server response.")
        else:
            QMessageBox.warning(None, 'Error', "No response from server.")
            self.setEnabled(True)  # Re-enable the MainWindow

    def process_finished(self, images, maze_strings):
        self.setEnabled(True)  # Re-enable the MainWindow
        self.progress_dialog.set_message("Finished training, let's see the results.")
        QTimer.singleShot(2000, self.progress_dialog.accept)
        QTimer.singleShot(2000, lambda: self.show_images(images, maze_strings))

    def show_progress_dialog_rounds(self, maze_strings): # Same as show_progress_dialog, but for the last round
        self.setEnabled(False)  # Disable the MainWindow
        self.progress_dialog = ProgressDialog()
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.show()
        response = send_to_server(self.participant_id, maze_strings)
        if response:
            try:
                images = json.loads(response)
                # Continue with the processing of images
                self.rounds_finished(images, maze_strings)
            except json.JSONDecodeError as e:
                print("JSON decoding error:", e)
                QMessageBox.warning(None, 'Error', "Failed to decode server response.")
        else:
            QMessageBox.warning(None, 'Error', "No response from server.")
            self.setEnabled(True)  # Re-enable the MainWindow

    def rounds_finished(self, images, maze_strings):  # Same as process_finished, but for the last round
        self.setEnabled(True)  # Re-enable the MainWindow
        self.progress_dialog.set_message("Congrats, you are done. Here are your final results")
        QTimer.singleShot(2000, self.progress_dialog.accept)
        QTimer.singleShot(2000, lambda: self.show_images_rounds(images))

    def show_images(self, images, maze_strings):
        image_window = ImageWindow(images, maze_strings, self.update_maze_data)
        image_window.exec_()

    def show_images_rounds(self, images): # Same as show_images, but for the last round
        image_window = ImageWindowRounds(images)
        image_window.exec_()
        self.start_end_window()

    def start_end_window(self):
        self.end_window = EndWindow(self)
        self.end_window.exec_()
	    
    # To updated mazes based on selected result
    def update_maze_data(self, new_maze_string):
        maze_data = new_maze_string
        self.update_mazes(maze_data)

    def update_mazes(self, maze_data):
        #print("Updating mazes with data:", maze_data)
        # Update all maze widgets with the new maze data
        for widgets in self.variable_widgets1:
            maze_widget = self.maze_widgets1[self.variable_widgets1.index(widgets)]
            self.set_maze_widget_data(widgets, maze_data)
            maze_widget.set_maze(self._maze_data_from_string_data(maze_data))

        for widgets in self.variable_widgets2:
            maze_widget = self.maze_widgets2[self.variable_widgets2.index(widgets)]
            self.set_maze_widget_data(widgets, maze_data)
            maze_widget.set_maze(self._maze_data_from_string_data(maze_data))

    def set_maze_widget_data(self, widgets, data):
        #print("Setting maze widget data with:", data)
        widgets["Seed"].setValue(data["Seed"]),
        widgets["Size"].setValue(data["Size"]),
        widgets["Traps"].setValue(data["Traps"])
        widgets["Without intersections"].setChecked(data["Without intersections"]),
        widgets["Start"].setCurrentText(data["Start"])

    def _maze_data_from_string_data(self, data):
        return amaze.Maze.BuildData(
            seed=data["Seed"],
            width=data["Size"],
            height=data["Size"],
            unicursive=data["Without intersections"],
            rotated=True,
            start=amaze.StartLocation[data["Start"]],
            clue=[amaze.Sign(value=1)],
            p_lure=0, # Changed from lures
            lure=[],
            p_trap=data["Traps"] / 100, # Keep it at 100
            trap=[amaze.Sign(value=.5)]
        )




def main(is_test=False):
    app = amaze.application()
    window = MainWindow()
    window.show()

    if is_test:
        QTimer.singleShot(1000, lambda: window.close())
    app.exec_()

if __name__ == "__main__":
    main()






