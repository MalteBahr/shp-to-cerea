from tkinter import *
from plotFrame import PlotFrame
class ConverterGUI:
    def __init__(self, master):
        self.master = master
        master.title("SHP-To-Cerea-Converter")


        self.plotFrame = PlotFrame(master, width=300,height=300)
        self.plotFrame.pack()

root = Tk()
my_gui = ConverterGUI(root)
root.mainloop()























