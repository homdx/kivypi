import kivy
import requests
kivy.require("1.9.0")
 
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty
from kivy.uix.listview import ListItemButton 
 
class StudentListButton(ListItemButton):
    pass
 
 
class Test(BoxLayout):
 
    # Connects the value in the TextInput widget to these
    # fields
    first_name_text_input = ObjectProperty()
    last_name_text_input = ObjectProperty()
    student_list = ObjectProperty()
 
    def submit_student(self):
 
        # Get the student name from the TextInputs
        student_name = self.first_name_text_input.text + " " + self.last_name_text_input.text
 
        # Add the student to the ListView
        self.student_list.adapter.data.extend([student_name])
 
        # Reset the ListView
        self.student_list._trigger_reset_populate()
 
    def delete_student(self, *args):
 
        # If a list item is selected
        if self.student_list.adapter.selection:
 
            # Get the text from the item selected
            selection = self.student_list.adapter.selection[0].text
 
            # Remove the matching item
            self.student_list.adapter.data.remove(selection)
 
            # Reset the ListView
            self.student_list._trigger_reset_populate()
 
    def replace_student(self, *args):
 
        # If a list item is selected
        if self.student_list.adapter.selection:
 
            # Get the text from the item selected
            selection = self.student_list.adapter.selection[0].text
 
            # Remove the matching item
            self.student_list.adapter.data.remove(selection)
 
            # Get the student name from the TextInputs
            student_name = self.first_name_text_input.text + " " + self.last_name_text_input.text
 
            # Add the updated data to the list
            self.student_list.adapter.data.extend([student_name])
 
            # Reset the ListView
            self.student_list._trigger_reset_populate()
 
class CalcGridLayout(GridLayout):

    def build(self):
        print('test')
        return Test()
    # Function called when equals is pressed
    def calculate(self, calculation):
        if calculation:
            try:
                # Solve formula and display it in entry
                # which is pointed at by display
                #r = requests.post("https://maker.ifttt.com/trigger/post_to_slack/with/key/UcYrm-X3zGUSSCqyH8UVl")
                print("test2")
                self.display.text = str(eval(calculation))
            except Exception:
                self.display.text = "Error"
 
class CalculatorApp(App):
 
    def build(self):
        print('test')
        return CalcGridLayout()
 
calcApp = CalculatorApp()
calcApp.run()
