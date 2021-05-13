# web-app for API image manipulation

from flask import Flask, request, render_template, send_from_directory
import os
import cv2
from skimage import data,filters
import numpy as np
from PIL import Image
import pytesseract
import sys

app = Flask(__name__)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))


# default access page
@app.route("/")
def main():
    return render_template('index.html')


# upload selected image and forward to processing page
@app.route("/upload", methods=["POST"])
def upload():
    target = os.path.join(APP_ROOT, 'static/images/')

    # create image directory if not found
    if not os.path.isdir(target):
        os.mkdir(target)

    # retrieve file from html file-picker
    upload = request.files.getlist("file")[0]
    print("File name: {}".format(upload.filename))
    filename = upload.filename

    # file support verification
    ext = os.path.splitext(filename)[1]
    if (ext == ".jpg") or (ext == ".png") or (ext == ".bmp"):
        print("File accepted")
    else:
        return render_template("error.html", message="The selected file is not supported"), 400

    # save file
    destination = "/".join([target, filename])
    print("File saved to to:", destination)
    upload.save(destination)

    img = Image.open(destination)
    width = img.size[0]
    height = img.size[1]

    # forward to processing page
    return render_template("processing.html", image_name=filename,  w = width, h = height )


# rotate filename the specified degrees
@app.route("/rotate", methods=["POST"])
def rotate():
    # retrieve parameters from html form
    filename = request.form['image']

    # open and process image
    target = os.path.join(APP_ROOT, 'static/images')
    destination = "/".join([target, filename])

    img = cv2.imread(destination)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cascPath = "haarcascade_frontalface_default.xml"

    # Create the haar cascade
    faceCascade = cv2.CascadeClassifier(cascPath)
    faces = faceCascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
    )
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

    
    # save and return image
    destination = "/".join([target, 'temp.png'])
    if os.path.isfile(destination):
        os.remove(destination)
    cv2.imwrite(destination, img)

    return send_image('temp.png')


# flip filename 'vertical' or 'horizontal'
@app.route("/flip", methods=["POST"])
def flip():
    filename = request.form['image']
    target = os.path.join(APP_ROOT, 'static/images')
    destination = "/".join([target, filename])

    img = Image.open(destination)
    # Adding custom options
    custom_config = r'--oem 3 --psm 6'
    Text = pytesseract.image_to_string(img, config=custom_config)
    if 'horizontal' in request.form['mode']:
        return render_template("result.html", message = Text)
    elif 'vertical' in request.form['mode']:
        Words = Text.split()
        w = request.form['word']

        if w in Words:
            Text = w + ' is present in the image'
        else:
            Text = w + ' is not present in the image'
        return render_template("result.html", message = Text)
    elif 'evaluate' in request.form['mode']:
        val = []
        e = ''
        for i in range(len(Text)):
            if Text[i] in '0123456789':
                if e == '':
                    e = Text[i]
                else:
                    e = e + Text[i]
            else:
                if e != '':
                    val.append(e)
                    e = ''
                val.append(Text[i])
        if e != '':
            val.append(e)

        postfix = []
        stack = []
        for i in val:
            if i[0] in '0123456789':
                postfix.append(i)
            else:
                if i != '=':
                    if i == '(':
                        stack.append(i)
                    elif (i == '+') or (i == '-'):
                        while (len(stack) != 0) and (stack[len(stack)-1] != '('):
                            postfix.append(stack.pop())
                        stack.append(i)
                    elif (i in 'x*') or (i == '/'):
                        while (len(stack) != 0) and (stack[len(stack)-1] not in '(+-'):    
                            postfix.append(stack.pop())
                        stack.append(i)
                    elif i == ')':
                        if '(' in stack:
                            while stack[len(stack)-1] != '(':
                                postfix.append(stack.pop())
                            stack.pop()
                        else:
                            continue 
                        
        while len(stack) != 0:
            postfix.append(stack.pop())

        stack = []
        for i in postfix:
            if  i[0] in '0123456789':
                stack.append(float(i))
            else:
                val2 = stack.pop()
                val1 = stack.pop()
                if i == '+':
                    stack.append(val1 + val2)
                elif i == '-':
                    stack.append(val1 - val2)
                elif i in 'x*':
                    stack.append(val1 * val2)
                elif i == '/':
                    stack.append(val1 / val2)
        
        if len(stack) == 1:
            result = stack.pop()
            Text = 'Result of the expression ' + Text + ' is ' + str(result)
        else:
            Text = 'Invalid Expression'

        return render_template("result.html", message = Text)
    
# retrieve file from 'static/images' directory
@app.route('/static/images/<filename>')
def send_image(filename):
    return send_from_directory("static/images", filename)


if __name__ == "__main__":
    app.run(debug=True)

