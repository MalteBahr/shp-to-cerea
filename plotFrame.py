import math
from tkinter import *
from tkinter import filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


from pyproj import Proj, transform
from pyproj import _datadir, datadir
from copy import deepcopy
datadir.set_data_dir("./proj/")
import traceback

import matplotlib
import matplotlib.pyplot

import shapefile
import os
import numpy as np
matplotlib.use('TkAgg')


class PlotFrame(Frame):
    def clamp(self,n,smallest,largest):
        val = max(smallest,min(n,largest))
        if n>largest or n < smallest:
            print("WARNING: Clamped " + n + " to " + val+ " for arccos")
        return val

    def disable_stuff(self):
        self.importbutt.config(state="normal")
        self.KBS_IN.config(state="readonly")
        self.KBS_OUT.config(state="readonly")
        self.subdivisions.config(state="readonly")
        self.submitbut.config(state="disabled")


    # direction (of points): -1 = clockwise, 1 = anticlockwise
    def offset_polygon(self, poly, direction, distance):
        normal_vectors = list()
        for i in range(len(poly)):
            #grab 2 points for line:
            a = np.array(poly[(i-1)%len(poly)])
            b = np.array(poly[i])
            c = np.array(poly[(i+1)%len(poly)])
            if (a==b).all() or (b==c).all():
                raise Exception()
            # # line g from point a to point b:
            # #   g = a + t*(b-a)
            # # or
            # #        /a1\         /b1 - a1\
            # #   g = |    | + t * |         |
            # #        \a2/         \b2 - a2/
            # # let's call b-a the direction vector d
            # d = [b[0]-a[0],b[1]-a[1]]
            # # now find 2 parallel lines with distance of variable "distance"
            # # perpendicular vector in R2:
            # # a = (a1)      a_p = (-a2)
            # #     (a2)            (a1 )  because scalar product should be zero, and a1*(-a2)+a2*a1 = -a1*a2+a1*a2=0
            # # also make sure the vector points inwards, if we follow the points in anticlockwise direction,
            # # the vector will always point "inwards" of the polygon, in clockwise direction the vector needs to be reversed
            # d_p = [direction*-d[1],direction*d[0]]
            # #scale perpendicular vector to length distance
            # d_len = math.sqrt(d[0]*d[0]+d[1]*d[1])
            # print(d_len)
            # d_p = [(d_p[0]/d_len)*distance, (d_p[1]/d_len)*distance]
            # print(d)
            # print(d_p)
            d1 = a-b
            d2 = c-b
            d1_n = d1 / np.sqrt(np.sum(d1 ** 2))
            d2_n = d2 / np.sqrt(np.sum(d2 ** 2))

            dot_prod = d1_n[0]*d2_n[0]+d1_n[1]*d2_n[1]
            alpha = np.arccos(self.clamp(dot_prod,-1,1))
            #print(alpha)
            zcross = d1_n[0]*d2_n[1] - d1_n[1]*d2_n[0]

            if zcross > 0:
                sina = np.sin(alpha/2)
            else:
                sina = np.sin(alpha/2+np.pi)
            if (sina != 0):
                multiplier = 1 / sina * -1
            else:
                raise Exception()


            nvector = d1_n + d2_n
            nvector_n = nvector / np.sqrt(np.sum(nvector ** 2))

            normal_vectors.append(nvector_n*multiplier)
        return normal_vectors
            
            
            
    def import_shp(self,KBS_IN,KBS_OUT):
        self.filename = filedialog.askopenfilename(initialdir=os.getcwd(), title="Waehle die zu öffnende Shape-Datei(.shp) aus",filetypes = (("Shape-Dateien","*.shp"),("Alle Dateien","*.*")))
        if not self.filename:
            return
        #print(self.filename)
        self.importbutt.config(state="disabled")
        sf = shapefile.Reader(self.filename)

        print('number of shapes imported:', len(sf.shapes()))
        print(' ')
        print('geometry attributes in each shape:')
        for name in dir(sf.shape()):
            if not name.startswith('__'):
                print(name)
        self.sf = sf
        self.plot_sf(KBS_IN,KBS_OUT)

    def plot_sf(self,KBS_IN,KBS_OUT):
        inProj = Proj(init='epsg:' + KBS_IN)
        outProj = Proj(init='epsg:' + KBS_OUT)
        matplotlib.pyplot.clf()
        shapes = list()
        shapes_vgw = list()
        i = 0
        multiple_part_polygons_count = 0
        shape_types = {}

        for shape in list(self.sf.iterShapes()):
            shape_types[shape.shapeType] = shape_types.get(shape.shapeType,0) + 1
            npoints = len(shape.points)  # total points
            nparts = len(shape.parts)  # total parts

            #transform(inProj,outProj,self.shapes[z][b][0],self.shapes[z][b][1])
            if nparts == 1:
                shapes.append([])
                for ip in range(len(shape.points)):
                    coord = transform(inProj,outProj,shape.points[ip][0],shape.points[ip][1])
                    if len(shapes[-1]) > 0:
                        last = shapes[-1][-1]
                        if last != coord:
                            shapes[-1].append(coord)
                    else:
                        shapes[-1].append(coord)
                if shapes[-1][-1] == shapes[-1][0]:
                    shapes[-1].pop()

                xs = [coords[0] for coords in shapes[-1]]
                ys = [coords[1] for coords in shapes[-1]]
                matplotlib.pyplot.plot(xs, ys)



                poly2 = self.offset_polygon(shapes[-1][:-1], -1, 1)
                poly2.append(poly2[0])
                shapes_vgw.append(poly2)
                #print(shapes)
            else:
                multiple_part_polygons_count += 1
            i = i + 1
        #print(shape_types)
        #print(multiple_part_polygons_count)

        if multiple_part_polygons_count > 0:
            messagebox.showwarning("Mehrere Teile in Polygon", "{} Polygon(s) bzw. Felder bestehen aus mehreren Teilen und konnten nicht verarbeitet werden.".format(multiple_part_polygons_count))

        self.fig.canvas.draw()
        self.shapes = shapes
        self.shapes_vgw = shapes_vgw
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

        path = os.getcwd()

        try:
            not_overwritten = 0
            for z in range(len(self.shapes)):
                offset_x = self.shapes[z][0][0]
                offset_y = self.shapes[z][0][1]
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
                        for coords in self.shapes[z]:
                            for abc in range(c):
                                f.write(str(coords[0] - offset_x) + ", " + str(coords[1] - offset_y) + ", 0.0\n")
                        f.write("dir\n")
                        for coords in self.shapes_vgw[z]:
                            for abc in range(c):
                                f.write(str(-coords[1]) + ", " + str(coords[0]) + ", 0.0\n")
                else:
                    not_overwritten += 1
            messagebox.showinfo("Erfolg!","Von {} Dateien wurden {} erfolgreich geschrieben, die restlichen wurden nicht überschrieben".format(len(self.shapes),len(self.shapes) - not_overwritten))

        except Exception as e :
            print(len(self.shapes_vgw))
            print(len(self.shapes))
            messagebox.showerror("Fehler","Etwas hat nicht funktioniert: " + traceback.format_exc())




    def __init__(self, master, width, height):

        self.countvar = 0
        super().__init__(master,width=width,height=height)
        self.fig = matplotlib.pyplot.figure(1)

        # Special type of "canvas" to allow for matplotlib graphing
        canvas = FigureCanvasTkAgg(self.fig, master=self)
        plot_widget = canvas.get_tk_widget()
        self.importbutt = Button(self,text="Import",state=DISABLED,command=lambda : self.import_shp(self.KBS_IN.get(),self.KBS_OUT.get()))
        self.importbutt.grid(row=1, column=1)
        self.export_button = Button(self,text="Export",state=DISABLED,command=lambda : self.export_cerea(self.subdivisions.get(),self.KBS_IN.get(),self.KBS_OUT.get()))
        self.export_button.grid(row=2, column=1)
        #KBS

        self.label_KBS_IN = Label(self, text="SHP-Format\tepsg:")
        self.label_KBS_OUT = Label(self, text="Cerea-Format\tepsg:")
        self.label_subdivisions = Label(self,text="Koordinaten doppeln (für Explorer) [?]", cursor="question_arrow")

        def action(event):
            messagebox.showinfo("Erklärung","Im Explorer werden Punkte vermutlich aus Performancegründen weggelassen, deshalb werden die Eckpunkte des Feldes mehrfach in die Datei geschrieben, um das Feld komplett im Explorer anzuzeigen")
        self.label_subdivisions.bind("<Button-1>", action)


        KBS_in_text = StringVar(self, value='32632')
        KBS_out_text = StringVar(self, value='32632')
        subdivisions = StringVar(self, value='5')

        self.KBS_IN = Entry(self,textvariable=KBS_in_text)
        self.KBS_OUT = Entry(self,textvariable=KBS_out_text)
        self.submitbut = Button(self, text="Bestätige Konvertierung",command=lambda : self.disable_stuff())
        self.submitbut.grid(row=1,column=0)
        self.subdivisions = Entry(self,textvariable=subdivisions)


        self.label_KBS_IN.grid(row=2,sticky=W)
        self.label_KBS_OUT.grid(row=3,sticky=W)
        self.label_subdivisions.grid(row=4,sticky=W)
        self.KBS_IN.grid(row=2, column=0)
        self.KBS_OUT.grid(row=3,column=0)
        self.subdivisions.grid(row=4,column=0)

        self.is_checked = IntVar()
        self.checkbox_overwrite = Checkbutton(self,text="Überschreibe existierende Konturen",onvalue=1, offvalue=0, variable=self.is_checked)
        self.checkbox_overwrite.grid(row=0,column=1)
        # Add the plot to the tkinter widget
        plot_widget.grid(row=0, column=0)

