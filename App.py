from tkinter import *
from PIL import ImageTk,Image
from tkinter import filedialog as fd
from Google import Create_Service
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import pytesseract
import pandas as pd
import difflib
import time
import cv2
import os
import io

ACCURACY = 0.75
SYMBOLSTOFILTER = [ ' ','!','*','/','?','{','}','[',']','(',')','+','-',
                    '_','~','\n','\r',"'",'"','|','.','<','>',',','%','^',
                    '&','#','№',':',';']

FOLDERID = '12E8Kjmh01FYSd_LctJjVKJPrAudAhRND'
TEXTNAME = 'photo_data'

image = []

DELTA_X = 25
current_x = 0
future_x = 0

def getFileId(file_name):
    global FOLDERID
    query = f"parents = '{FOLDERID}'"
    response = service.files().list(q=query).execute()
    files = response.get('files')
    nextPageToken = response.get('nextPageToken')
    while nextPageToken:
        response = service.files().list(q=query).execute()
        files.extend(response.get('files'))
        nextPageToken = response.get('nextPageToken')
    for line in files:
        if line['name'] == file_name:
            return line['id']

def getNumberOfFiles():
    global FOLDERID
    query = f"parents = '{FOLDERID}'"
    response = service.files().list(q=query).execute()
    files = response.get('files')
    nextPageToken = response.get('nextPageToken')
    while nextPageToken:
        response = service.files().list(q=query).execute()
        files.extend(response.get('files'))
        nextPageToken = response.get('nextPageToken')
    df = pd.DataFrame(files)
    size = df.size
    return size

def comparizon(text_1, text_2):
    text_1.lower()
    text_2.lower()
    for letter in SYMBOLSTOFILTER:
        text_1.replace(letter, '')
        text_2.replace(letter, '')
    return difflib.SequenceMatcher(None, text_1, text_2).ratio()

def getTextFromPicture(image_name):
    img = cv2.imread(image_name)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    filename = "{}.png".format(os.getpid())
    cv2.imwrite(filename, gray)
    custom_config = r'-l eng+rus --oem 3 --psm 6'
    text = pytesseract.image_to_string(Image.open(filename), config=custom_config)
    os.remove(filename)
    return text

# open file function
def openFile():
    file_name = fd.askopenfilename()
    text_inf = getTextFromPicture(file_name)
    text.option_clear()
    text.insert(1.0, text_inf)

# save to some folder
def saveFile():
    file_name = fd.asksaveasfilename(
        filetypes=( ("PNG files", "*.png"),
                    ("JPG files", "*.jpg;*.jpeg"),
                    ("All files", "*.*")))
    f = open(file_name, 'w')
    #s = text.get(1.0, END)
    #f.write(s)
    f.close()

# function for convert picture to work with it like 
# default tkinter files
def loadImage(name):
    img = Image.open(name)
    width, height = img.size
    global future_x
    future_x += width + DELTA_X
    img.resize((500, 500), Image.ANTIALIAS)
    return ImageTk.PhotoImage(img)

# to work with "default" pictures
def setImage(image_current):
    global current_x
    global future_x
    canvas.create_image(current_x, 0, anchor='nw', image=image_current)
    current_x = future_x

# function to download file from drive
def downloadFile(file_id, file_name):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    download = MediaIoBaseDownload(fd=fh, request=request)
    done = False
    while not done:
        status, done = download.next_chunk()
        print('download progress {0}'.format(status.progress() * 100))
    fh.seek(0)
    with open(os.path.join('./', file_name), 'wb') as f:
        f.write(fh.read())
    f.close()

# create function if first button clicked
def searchText():
    s = (text.get(1.0, END)).replace('\n', ' ').replace('\r', '')
    count = 0
    # loading file with text information about all pictures
    file_data_id = getFileId(TEXTNAME)
    byteData = service.files().get_media(
        fileId=file_data_id
    ).execute()
    file_information_data = ((str(byteData.decode("UTF-8"))).replace("\ufeff","").replace(" ", "")).split('\r')
    for line in file_information_data:
        count+=1
        if count % 3 == 0:
            current_ratio = comparizon(line, s)
            if current_ratio >= ACCURACY:
                name = file_information_data[count-3]
                downloadFile(file_information_data[count-2], name)
                image.append(loadImage(name))
                setImage(image[-1])
    global future_x
    canvas.config(scrollregion=[0,0,future_x,1000])

def UpdateDataBase():
    #save picture of that file
    text_id=getFileId(TEXTNAME)
    file_tray = fd.askopenfilename()
    file_name = "{}.png".format(int(getNumberOfFiles() / 4))
    file_metadata = {
        'name': [file_name],
        'parents': [FOLDERID]
    }
    media = MediaFileUpload(file_tray, mimetype='image/png')
    service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    file_id = getFileId(file_name)
    # data from text file
    text_of_file = getTextFromPicture(file_tray).replace('\n', ' ')
    # take data from text file in drive
    byteData = service.files().get_media(
        fileId=text_id,
    ).execute()
    # write data back to google drive
    text_name = 'photo_data.txt'
    text = ((str(byteData.decode("UTF-8"))).replace("\\ufeff","").replace("'b\\'", "").replace("\\r\\n", "\\n")).split("\\n")
    f = open(text_name, "w+")
    for i in text:
        if not i.isspace():
            i.replace('/', '').replace("\\", "")
            f.write(i)
            f.write("\n")
    f.write(file_name)
    f.write("\n")
    f.write(file_id)
    f.write("\n")
    f.write(text_of_file)
    f.write("\n")
    f.close()
    file_metadata = {
        'name': [TEXTNAME],
        'parents': [FOLDERID]
    }
    media = MediaFileUpload('./{0}'.format(text_name), mimetype='text/plain')
    service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    service.files().delete(fileId=text_id).execute()
    time.sleep(1)
    if os.path.exists(text_name):
        os.remove(text_name)
    else:
        print("The file does not exist")

# create that should tkinter object do if closed
def close():
    root.destroy()
    root.quit()

# preparation tesseract for work with
pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
# preparation google client file for work with google drive api
CLIENT_SECRET_FILE = 'client_secret.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)
# pretuning of pandas library
pd.set_option('display.max_columns', 100)
pd.set_option('display.max_rows', 500)
pd.set_option('display.min_rows', 500)
pd.set_option('display.max_colwidth', 150)
pd.set_option('display.width', 200)
pd.set_option('expand_frame_repr', True)
# start tkinter
root = Tk()
# name program
root.title("Program")
# create size of window
root.geometry('1500x1000')
# take place for future pictures
canvas=Canvas(root, width=1450, height=750, borderwidth=0, highlightthickness=0)
canvas.place(x=25, y= 120)
hbar=Scrollbar(root,orient=HORIZONTAL)
hbar.pack(padx=25, pady=100, fill=X)

hbar.config(command=canvas.xview)
canvas.config(xscrollcommand=hbar.set)
canvas.xview_moveto(1.0)

# Button to search by text
search_button = Button(root, text="Search by text", padx=100, pady=25, command=searchText, fg="#000000", bg="#ffffff")
search_button.place(x=10, y=10)
# Button to search by photo
local_button = Button(root, text="Search by photo", padx=100, pady=25, command=openFile, fg="#000000", bg="#ffffff")
local_button.place(x=10, y=900)
# Button to save file in data base
global_button1 = Button(root, text="Update data base", padx=150, pady=25, command=UpdateDataBase, fg="#000000", bg="#ffffff")
global_button1.place(x=500, y=900)
# text input window 
text = Text(width=100, height=5, fg="#000000", bg="#ffffff", wrap=WORD)
text.place(x=350, y=10)
# closing window
root.protocol('WM_DELETE_WINDOW', close)
root.mainloop()

