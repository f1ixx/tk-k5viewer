#!/bin/python3

from tkinter import *   
from tkinter import ttk
from tkinter import messagebox
from PIL import ImageGrab
import serial
import time

try:
	mySerial = serial.Serial()
	mySerial = serial.Serial("/dev/ttyUSB0", 38400, timeout=1)
except:
    mySerial = ""
    print("Serial error")

pixel_size = 5
lcd_pixel = 0
lcd_inv = 0
WIDTH = 128
HEIGHT = 64
VERSION = "1.0"
BASE_TITLE = f"Quansheng K5Viewer v{VERSION} by F4HWN (mod Boris)"

frame_count=0
last_time=0

hexaSerial = ""
asciiSerial = ""

    
COLOR_SETS = {  # {key: (name, foreground, background)}
    "g": ("Grey", "#000000", "#cacaca"),
    "o": ("Orange", "#000000", "#ffc125"),
    "b": ("Blue", "#000000", "#1c86e4"),
    "w": ("White", "#000000", "#ffffff")
    }

framebuffer = bytearray([0] * 1024)


####################################################################################################
##
## Affiche le comptenu du buffer dans le Canvas
##
def display():
    global pic
    global frame_count
    global last_time
    
    if (lcd_inv):
        color_pixel = color[0]
        color_screen = color[1]
    else:
        color_pixel = color[1]
        color_screen = color[0]
    
    pic.create_rectangle(0, 0, WIDTH*(pixel_size-1), HEIGHT*pixel_size, fill=color_screen, outline=color_screen)
    
    for block_index in range(0, 1024):
        x = (block_index % 16)
        y = (block_index // 16)

        for numbin in range(0, 8):  
            if ( framebuffer[block_index] & pow(2, numbin) ):
                x1 = (x*8 + numbin) * (pixel_size-1)
                y1 = y * pixel_size
                if (lcd_pixel):
                    pic.create_rectangle(x1, y1, x1+(pixel_size-1), y1+pixel_size, fill=color_pixel, outline=color_screen)
                else:
                    pic.create_rectangle(x1, y1, x1+(pixel_size-1), y1+pixel_size, fill=color_pixel, outline=color_pixel)

    frame_count += 1
    now = time.monotonic()
    if now - last_time >= 1.0:
        fps = frame_count / (now - last_time)
        app.title(f"{BASE_TITLE} – FPS: {fps:>04.1f}")
        frame_count = 0
        last_time = now
        frame_lost = 0
                
####################################################################################################
##
## Si on change de tab et qu'on revien sur la 1er, on redessine l'ecran
##
def onChange_tab(event):
	nb = event.widget
	tab = nb.select()
	if (tab == ".!notebook.!frame"):
		print("click")

####################################################################################################
##
## Remplissage du buffer avec les nouvelle donnees recu
##
def apply_diff(diff_payload: bytes) -> bytearray:
    i = 0
    while i + 9 <= len(diff_payload):
        block_index = diff_payload[i]
        i += 1
        if block_index >= 128:
            break
        framebuffer[block_index * 8 : block_index * 8 + 8] = diff_payload[i : i + 8]
        i += 8

##################################################################################################
##
## Procedure de lecture du port serial et gestion de ce qu'on fait des donnees
##
def timer_app():
    global framebuffer, mySerial
    global hexaSerial, asciiSerial
    global hexaText, asciiText
    
    payload = 0
    
    while mySerial.in_waiting:  # Or: while ser.inWaiting():
        t = mySerial.read(1)
        if (t == b'\xaa'):
            t = mySerial.read(1)
            if (t == b'\x55'):
                typeFrame = mySerial.read(1)
                size_bytes = mySerial.read(2)
                size = int.from_bytes(size_bytes, 'big')
                if ( (typeFrame == b'\x01') and (size == 1024) ):
                    payload = mySerial.read(size)
                    framebuffer = bytearray(payload)
                elif ( (typeFrame == b'\x02') and (size % 9 == 0) ):
                    payload = mySerial.read(size) 
                    apply_diff(payload)
            else:
                t = ord(t.decode())
                hexaSerial += f"{t:02x} "
                if ( (t > 32) and (t < 128) ):
                    asciiSerial += chr(t)
                else:
                    asciiSerial += "."
        else:
            t = ord(t.decode())
            hexaSerial += f"{t:02x} "
            if ( (t > 32) and (t < 128) ):
                asciiSerial += chr(t)
            else:
                asciiSerial += "."
    
        if (len(asciiSerial) >= 16):
            print(hexaSerial,"\t", asciiSerial)
            hexaSerial = ""
            asciiSerial = ""

    if (payload):
        display()
    mySerial.write(b'\x55\xAA\x00\x00')  # Keepalive frame
    app.after(50, timer_app)


##################################################################################################
##
## Gestion du clavier
##
def keyboard(event):
    global color
    global lcd_pixel
    global lcd_inv
    global pixel_size
    global pic

    #print(event.keysym)
    key = event.keysym.lower()
    if ( key == "h"):
        strTmp = """
        space : Prendre une capture avec Date et heure
        p : passe en mode lcd pixel
        o : Couleur orange
        b : Couleur bleu
        w : Couleur blanche
        g : Couleur gris
        Flech Haut/bas : change la taille de l'image
        q : Quitter l'application"""
        messagebox.showinfo("viewer K5 - Help", strTmp)
        return
        
    if (key == "space"):
        t = time.localtime()
        filename = f"screenshot_{t.tm_year}{t.tm_mon:02}{t.tm_mday:02}_{t.tm_hour:02}{t.tm_min:02}{t.tm_sec:02}.png"
        x = pic.winfo_rootx()
        y = pic.winfo_rooty()
        w = x + int(pic["width"])
        h = y + int(pic["height"])
        im = ImageGrab.grab((x, y, w, h))
        im.save(filename)
        print("Saved :", filename)
        return
    
    if (key == "q"):
        mySerial.close()
        quit()
            
    change = False
    
    if (key in COLOR_SETS):
        color = [COLOR_SETS[event.keysym][2], COLOR_SETS[event.keysym][1]]
        change = True
        
    if (key == "p"):
        lcd_pixel = 1 - lcd_pixel
        change = True

    if (key == "i"):
        lcd_inv = 1 - lcd_inv
        change = True
        
    if (key  == "up"):
        pixel_size += 1
        if (pixel_size > 10):
            pixel_size = 10
        pic["width"] = WIDTH * (pixel_size-1)
        pic["height"] = HEIGHT * pixel_size
        change = True
        
    if (key == "down"):
        pixel_size -= 1
        if (pixel_size < 2):
            pixel_size = 2
        pic["width"] = WIDTH * (pixel_size-1)
        pic["height"] = HEIGHT * pixel_size
        change = True
        
    if (change):
        display()
	
##################################################################################################
##
## Boucle principal. Creation du GUI
##
app = Tk()
app.resizable(False, False)
app.bind("<KeyRelease>", keyboard)
app.title(BASE_TITLE)

pic = Canvas(app, width=WIDTH*(pixel_size-1), height=HEIGHT*pixel_size, bg=COLOR_SETS["o"][2])
pic.grid()

color = [COLOR_SETS["o"][2], COLOR_SETS["o"][1]]

if (mySerial != ""):
    mySerial.write(b'\x55\xAA\x00\x00')  # Keepalive frame
    timer_app()

try:
    app.mainloop()
except KeyboardInterrupt:
    mySerial.close()
    quit()
