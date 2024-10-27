import cv2
import os
from flask import Flask, request, jsonify
from datetime import date, datetime
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import numpy as np
import pandas as pd
from flask_pymongo import PyMongo
from flask_cors import CORS
from train_model import model as train_model

# Defining Flask App
app = Flask(__name__)
CORS(app)

port_app = 8000

app.config["MONGO_URI"] = "mongodb://localhost:27017/pep"  # Update with your MongoDB URI
mongo = PyMongo(app)

current_date = datetime.now().strftime("%Y%m%d")
nimgs = 10
model_path = "static/model.pth"  # Path to your saved PyTorch model

# Saving Date today in 2 different formats
datetoday = date.today().strftime("%m_%d_%y")
datetoday2 = date.today().strftime("%d-%B-%Y")

# Initializing VideoCapture object to access WebCam
face_detector = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# If these directories don't exist, create them
if not os.path.isdir('Attendance'):
    os.makedirs('Attendance')
if not os.path.isdir('static'):
    os.makedirs('static')
if not os.path.isdir('static/faces'):
    os.makedirs('static/faces')
if f'Attendance-{datetoday}.csv' not in os.listdir('Attendance'):
    with open(f'Attendance/Attendance-{datetoday}.csv', 'w') as f:
        f.write('Name,Roll,Time')

# Extract the face from an image
def extract_faces(img):
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        face_points = face_detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(20, 20))
        return face_points
    except Exception as e:
        print(f"Error in face detection: {e}")
        return []

IMG_SHAPE = (224, 224)  # Adjust based on your model's input requirements

def load_model():
    """Load the trained PyTorch model."""
    model = models.resnet18(pretrained=False)
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, len(os.listdir('static/faces')))  # Number of classes based on your database
    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()  # Set the model to evaluation mode
    return model

def verify_identity(face, model, transform, threshold=0.60):
    """Verify the identity of a person using the trained PyTorch model."""
    face = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))  # Convert to PIL image
    face = transform(face).unsqueeze(0)  # Apply transformations and add batch dimension

    with torch.no_grad():
        outputs = model(face)
        prob = torch.nn.functional.softmax(outputs, dim=1)
        confidence, predicted_class = torch.max(prob, 1)

    if confidence.item() > threshold:
        class_names = os.listdir('static/faces')
        return class_names[predicted_class.item()], confidence.item()

    return None, None

def identify_face(face, model):
    """Identify the face using the trained model."""
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    name, score = verify_identity(face, model, transform, threshold=0.60)
    if name:
        return f'{name} ({score:.2f})'
    else:
        return "Unknown"

def add_attendance(name):
    pass
    # username = name.split('_')[0]
    # userid = name.split('_')[1]
    # current_time = datetime.now().strftime("%H:%M:%S")
    
    # filter = {
    #     "domain": g_domain,
    #     "batch": int(g_batch),
    #     "students.regisno": int(userid),
    # }
    
    # update = {
    #     "$set": {
    #         "students.$.afterPresent": True
    #     }
    # }
    
    # result = mongo.db.mains.update_one(filter, update)
    
    # if result.matched_count > 0:
    #     print("Student updated successfully")
    # else:
    #     print("Student not found")
    
    # df = pd.read_csv(f'Attendance/Attendance-{datetoday}.csv')
    # if int(userid) not in list(df['Roll']):
    #     with open(f'Attendance/Attendance-{datetoday}.csv', 'a') as f:
    #         f.write(f'\n{username},{userid},{current_time}')

################## ROUTING FUNCTIONS #########################
g_domain = "FullStack"
g_batch = 1

@app.route('/')
def home():
    if not os.path.isdir(f'static/faces/{g_domain}'): 
        os.makedirs(f'static/faces/{g_domain}')
    if not os.path.isdir(f'static/faces/{g_domain}/{g_batch}'): 
        os.makedirs(f'static/faces/{g_batch}')
    return jsonify({})

## Delete functionality
@app.route('/deleteuser', methods=['GET'])
def deleteuser():
    duser = request.args.get('user')
    deletefolder(f'static/faces/{duser}')

    if os.listdir('static/faces/') == []:
        os.remove('static/model.pth')
    
    try:
        train_model()
    except:
        pass
    return jsonify({})

# Face Recognition and Attendance Route
@app.route('/start/', methods=['GET', 'POST'])
def start():
    print("Received request to take attendance")

    if 'model.pth' not in os.listdir('static'):
        return jsonify({
            "message": 'There is no trained model in the static folder. Please add a new face to continue.'
        }), 400

    model = load_model()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return jsonify({"message": "Webcam not accessible"}), 500

    ret = True
    while ret:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture image from webcam")
            break
        faces = extract_faces(frame)
        if len(faces) > 0:
            (x, y, w, h) = faces[0]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (86, 32, 251), 1)
            cv2.rectangle(frame, (x, y), (x+w, y-40), (86, 32, 251), -1)
            face = frame[y:y+h, x:x+w]
            identified_person = identify_face(face, model)
            if identified_person != "Unknown":
                add_attendance(identified_person)
                cv2.putText(frame, f'{identified_person}', (x+5, y-5),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imshow('Attendance', frame)
        if cv2.waitKey(1) == 27:  # Escape key to exit
            break
    cap.release()
    cv2.destroyAllWindows()
    return jsonify({"message": "Attendance process completed"})

@app.route('/add/', methods=['GET', 'POST'])
def add():
    newusername = request.form['newusername']
    newuserid = request.form['newuserid']
    userimagefolder = f'static/faces/{newusername}_{newuserid}'
    if not os.path.isdir(userimagefolder):
        os.makedirs(userimagefolder)
    i, j = 0, 0
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return jsonify({"message": "Webcam not accessible"}), 500

    while 1:
        _, frame = cap.read()
        faces = extract_faces(frame)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 20), 2)
            cv2.putText(frame, f'Images Captured: {i}/{nimgs}', (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 20), 2, cv2.LINE_AA)
            if j % 5 == 0:
                name = f'{newusername}_{str(i)}.jpg'
                cv2.imwrite(f'{userimagefolder}/{name}', frame[y:y+h, x:x+w])
                i += 1
            j += 1
        if j == nimgs * 5:
            break
        cv2.imshow('Adding new User', frame)
        if cv2.waitKey(1) == 27:  # Escape key to exit
            break
    cap.release()
    cv2.destroyAllWindows()
    print('Training Model')
    train_model()
    return jsonify({})

# Run Flask App
if __name__ == '__main__':
    print(f"Python server is running at {port_app}")
    app.run(debug=True, port=port_app)
