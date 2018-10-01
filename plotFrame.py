from tkinter import *
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


from pyproj import Proj, transform
from copy import deepcopy

import traceback

import matplotlib
import matplotlib.pyplot

import shapefile
import os

matplotlib.use('TkAgg')

class PlotFrame(Frame):

    def import_shp(self):
        self.filename = filedialog.askopenfilename(initialdir=os.getcwd(), title="Waehle die zu öffnende Shape-Datei(.shp) aus",filetypes = (("Shape-Dateien","*.shp"),("Alle Dateien","*.*")))
        if not self.filename:
            return
        #print(self.filename)

        sf = shapefile.Reader(self.filename)

        print('number of shapes imported:', len(sf.shapes()))
        print(' ')
        print('geometry attributes in each shape:')
        for name in dir(sf.shape()):
            if not name.startswith('__'):
                print(name)
        self.sf = sf
        self.plot_sf()

    def plot_sf(self):
        matplotlib.pyplot.clf()
        shapes = list()
        i = 0
        multiple_part_polygons_count = 0
        shape_types = {}

        for shape in list(self.sf.iterShapes()):
            shape_types[shape.shapeType] = shape_types.get(shape.shapeType,0) + 1
            npoints = len(shape.points)  # total points
            nparts = len(shape.parts)  # total parts

            if nparts == 1:
                shapes.append([])
                for ip in range(len(shape.points)):
                    shapes[-1].append(shape.points[ip])

                xs = [coords[0] for coords in shapes[-1]]
                ys = [coords[1] for coords in shapes[-1]]
                matplotlib.pyplot.plot(xs, ys)
                print(shapes)
            else:
                multiple_part_polygons_count += 1
            i = i + 1
        print(shape_types)
        print(multiple_part_polygons_count)

        if multiple_part_polygons_count > 0:
            messagebox.showwarning("Mehrere Teile in Polygon", "{} Polygon(s) bzw. Felder bestehen aus mehreren Teilen und konnten nicht verarbeitet werden.".format(multiple_part_polygons_count))

        self.fig.canvas.draw()
        self.shapes = shapes
        self.export_button.config(state="normal")

    def export_cerea(self, c, KBS_IN,KBS_OUT):
        c = int(c)
        inProj = Proj(init='epsg:' + KBS_IN)
        outProj = Proj(init='epsg:' + KBS_OUT)

        messagebox.showinfo("Ordnerauswahl", "Wähle den Kundenordner in C:/Cerea-Versionsnr/datos/ aus")
        self.foldername = filedialog.askdirectory(initialdir="C:/", title="Waehle den Kundenordner aus")

        if not self.foldername:
            return
        if not os.path.isdir(self.foldername):
            messagebox.showerror("Error","Das hätte nicht passieren dürfen, der Ordner den du angegeben hast existiert nicht")
        ### create extra points on straight lines, because cerea can't handle simple polygons

        self.shapes_subdivided = deepcopy(self.shapes)

        for z in range(len(self.shapes_subdivided)):
            for b in range(len(self.shapes_subdivided[z])):
                self.shapes_subdivided[z][b] = transform(inProj,outProj,self.shapes[z][b][0],self.shapes[z][b][1])


        for z in range(len(self.shapes_subdivided)):
            points_tmp = list()
            ## unterteile c mal
            for a in range(c):
                # den z-ten shape (polygon/feld) unterteilen
                for b in range(len(self.shapes_subdivided[z]) - 1):
                    points_tmp.append(self.shapes_subdivided[z][b])
                    points_tmp.append([(float(self.shapes_subdivided[z][b][0]) + float(self.shapes_subdivided[z][b + 1][0])) / 2,
                                       (float(self.shapes_subdivided[z][b][1]) + float(self.shapes_subdivided[z][b + 1][1])) / 2])
                points_tmp.append(self.shapes_subdivided[z][-1])
                self.shapes_subdivided[z] = points_tmp
                points_tmp = list()

        # saving to folders like cerea would

        # header of file

        # offsetDirContorno
        # -1
        # indexContorno
        # 2
        # iniPosition
        # offset_x,offset_y
        # points
        path = os.getcwd()

        try:
            not_overwritten = 0
            for z in range(len(self.shapes_subdivided)):
                offset_x = self.shapes_subdivided[z][0][0]
                offset_y = self.shapes_subdivided[z][0][1]
                os.makedirs(self.foldername+"/"+str(z)+"/",exist_ok=True)
                if self.is_checked.get() or not os.path.isfile(self.foldername + "/" + str(z) + "/contour.txt"):
                    with open(self.foldername + "/" + str(z) + "/contour.txt", "w") as f:
                        f.write("offsetDirContorno\n")
                        f.write("-1\n")
                        f.write("indexContorno\n")
                        f.write("2\n")
                        f.write("iniPosition\n")
                        f.write(str(offset_x) + "," + str(offset_y) + "\n")
                        f.write("points\n")
                        for coords in self.shapes_subdivided[z]:
                            f.write(str(coords[0] - offset_x) + ", " + str(coords[1] - offset_y) + ", 0.0\n")
                else:
                    not_overwritten += 1
            messagebox.showinfo("Erfolg!","Von {} Dateien wurden {} erfolgreich geschrieben, die restlichen wurden nicht überschrieben".format(len(self.shapes_subdivided),len(self.shapes_subdivided) - not_overwritten))

        except Exception as e :
            messagebox.showerror("Fehler","Etwas hat nicht funktioniert: " + traceback.format_exc())


    def __init__(self, master, width, height):

        super().__init__(master,width=width,height=height)
        self.fig = matplotlib.pyplot.figure(1)

        # Special type of "canvas" to allow for matplotlib graphing
        canvas = FigureCanvasTkAgg(self.fig, master=self)
        plot_widget = canvas.get_tk_widget()
        Button(self,text="Import",command=self.import_shp).grid(row=1, column=0)
        self.export_button = Button(self,text="Export",state=DISABLED,command=lambda : self.export_cerea(self.subdivisions.get(),self.KBS_IN.get(),self.KBS_OUT.get()))
        self.export_button.grid(row=1, column=1)
        #KBS

        self.label_KBS_IN = Label(self, text="SHP-Format\tepsg:")
        self.label_KBS_OUT = Label(self, text="Cerea-Format\tepsg:")
        self.label_subdivisions = Label(self,text="Unterverteilungen", cursor="question_arrow")

        def action(event):
            messagebox.showinfo("Erklärung","Cerea scheint eckpunkte als falsche gps punkte zu werten wenn sie weit außerhalb liegen, deshalb müssen auf den Geraden der Shape-Dateien weitere Punkte gesetzt werden, damit es so aussieht als ob man der Gerade folgt. Bei 5 Unterverteilungen wird die Gesamteckenanzahl auf n^4 erhöht.")
        self.label_subdivisions.bind("<Button-1>", action)


        KBS_in_text = StringVar(self, value='6172')
        KBS_out_text = StringVar(self, value='7417')
        subdivisions = StringVar(self, value='5')

        self.KBS_IN = Entry(self,textvariable=KBS_in_text)
        self.KBS_OUT = Entry(self,textvariable=KBS_out_text)
        self.subdivisions = Entry(self,textvariable=subdivisions)


        self.label_KBS_IN.grid(row=2,sticky=E)
        self.label_KBS_OUT.grid(row=3,sticky=E)
        self.label_subdivisions.grid(row=4,sticky=E)
        self.KBS_IN.grid(row=2, column=1)
        self.KBS_OUT.grid(row=3,column=1)
        self.subdivisions.grid(row=4,column=1)

        self.is_checked = IntVar()
        self.checkbox_overwrite = Checkbutton(self,text="Überschreibe existierende Konturen",onvalue=1, offvalue=0, variable=self.is_checked)
        self.checkbox_overwrite.grid(row=0,column=1)
        # Add the plot to the tkinter widget
        plot_widget.grid(row=0, column=0)

