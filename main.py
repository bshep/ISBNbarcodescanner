#   AKIAJMGPOHDSOJFMDJPQ
#   /8wk6z6nOo7Vs/Hkhojj4Zb7GMllSXDbml7iC8VP


import cv
import zbar
import hmac
import hashlib
import base64
import urllib2
import datetime
import xml.dom.minidom
import sqlite3
import numpy
import sys

from config import AWSAccessKeyID, AWSSecret

cv.NamedWindow("w1", cv.CV_WINDOW_AUTOSIZE)
capture = cv.CaptureFromCAM(0)

scanner = zbar.ImageScanner()
scanner.parse_config('enable')

lastSymbol = None

logLines = []

def imageLoop():    
    global lastSymbol
    
    frame = cv.QueryFrame(capture)
    
    width_percent = 100.0 / 100
    height_percent = 90.0 / 100
    
    origin_x = int(frame.width * (1 - width_percent)/2)
    origin_y = int(frame.height * (1 - height_percent)/2)
    width = int(frame.width * width_percent)
    height = int(frame.height * height_percent)
    
    # print origin_x, origin_y, width, height
    
    subsection = cv.GetSubRect(frame, (origin_x+1, origin_y+1, width-1, height-1))
    # subsection = frame
    
    cv.Rectangle(frame, (origin_x, origin_y), (origin_x + width, origin_y + height), (255,0,0))
    
    cm_im = cv.CreateImage((subsection.width, subsection.height), cv.IPL_DEPTH_8U, 1)
    cv.ConvertImage(subsection, cm_im)
    image = zbar.Image(cm_im.width, cm_im.height, 'Y800', cm_im.tostring())
    
    scanner.scan(image)
    # extract results
    for symbol in image:
        # do something useful with results
        if symbol.type == zbar.Symbol.ISBN10 and lastSymbol != symbol.data:
            lastSymbol = symbol.data
            searchBook(symbol.data)
            
            # print 'decoded', symbol.type, 'symbol', '"%s"' % symbol.data
            
    # cv.ShowImage("w1", frame)
    # cv.ShowImage("w2", subsection)
    refreshWindow("w1", frame)
    
    key = cv.waitKey(100)
    if key != -1:
        if key == 113:
            sys.exit(0)
        logText("Key: ", key)

def searchBook(isbn_num):
    logText("Searching for: ", isbn_num)
    
    query = "AWSAccessKeyId=" + AWSAccessKeyID + "&AssociateTag=abc&Keywords="
    query += isbn_num 
    query += "&Operation=ItemSearch&ResponseGroup=ItemAttributes&SearchIndex=Books&Service=AWSECommerceService"
    query += "&Timestamp=" + urllib2.quote(datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"))[:-1]
    # query += "&Version=2011-08-01"
    
    data = "GET\n"
    data += "ecs.amazonaws.com\n"
    data += "/onca/xml\n"
    data += query
    
    a = hmac.new(AWSSecret, data, hashlib.sha256)
    signature = urllib2.quote(base64.encodestring(a.digest())[:-1])
    
    url = "http://ecs.amazonaws.com/onca/xml?" + query + "&Signature=" + signature
    
    # print "URL : ", url
    
    url_obj = urllib2.urlopen(url)
    
    
    data = url_obj.read()
    
    book_info = getInfoFromXML(data)
        
    logText( " - Title: ", book_info[0])
    logText( " - Price: ", book_info[1])
    storeInDB( (book_info[0], isbn_num, book_info[1]) )
    
def storeInDB(book_data):
    conn = sqlite3.connect("books.sqlite")
    
    conn.execute('CREATE TABLE IF NOT EXISTS "main"."book" ("title" TEXT NOT NULL , "isbn" TEXT PRIMARY KEY  NOT NULL  UNIQUE , "price" TEXT NOT NULL , "sold" BOOL NOT NULL  DEFAULT 0)')
    
    try:
        conn.execute('INSERT INTO book ("title", "isbn", "price") VALUES ( ?, ?, ? )', (book_data[0], book_data[1], book_data[2]) )
        logText("Added to DB")
    except sqlite3.IntegrityError:
        logText("Book already in DB")
    
    conn.commit()
    
    conn.close()

def getInfoFromXML(xmlstring):
    doc = xml.dom.minidom.parseString(xmlstring)
    
    title = ""
    price = ""
    
    for item in doc.getElementsByTagName("Item"):
        for item_title in item.getElementsByTagName("Title"):
            title = item_title.childNodes[0].wholeText
        
        for item_price in item.getElementsByTagName("ListPrice"):
            price = item_price.getElementsByTagName("FormattedPrice")[0].childNodes[0].wholeText    
            
    return (title, price)

def logText(*text):
    global logLines
    
    tmpText = ""
    for it in text:
        tmpText += str(it) + " "
        
    logLines.append(tmpText)
    
    if len(logLines) > 5:
        logLines.pop(0)
        
    # print tmpText
    
def refreshWindow(window, image):
    font = cv.InitFont(cv.CV_FONT_HERSHEY_PLAIN,1,1,0,2)
    
    yPos = image.height / 2
    for logLine in logLines:
        (rv, baseline) = cv.getTextSize(logLine, cv.CV_FONT_HERSHEY_PLAIN, 1, 1)
        cv.PutText(image, logLine, (10, yPos),font , (255,0,0))
        yPos += rv[1] + baseline
    
    cv.ShowImage(window, image)
    
    
while True:
    imageLoop()
