# /Users/arrosid/Dev/project-tkj-rekognition/app.py
import os
import uuid
from flask import Flask, render_template, request, jsonify
import boto3

def _load_env_file():
    p = os.path.join(os.path.dirname(__file__), '.env')
    try:
        with open(p, 'r') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                if '=' in s:
                    k, v = s.split('=', 1)
                    v = v.strip().strip('"').strip("'")
                    os.environ.setdefault(k.strip(), v)
    except FileNotFoundError:
        pass

_load_env_file()

app = Flask(__name__)
region = os.environ.get('AWS_REGION')
bucket = os.environ.get('S3_BUCKET_NAME')
collection_id = os.environ.get('REKOGNITION_COLLECTION_ID')
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.environ.get('AWS_SESSION_TOKEN')
session = boto3.Session(
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    aws_session_token=aws_session_token,
    region_name=region
)
s3 = session.client('s3')
rek = session.client('rekognition')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if not bucket:
        return jsonify({'error': 'S3_BUCKET_NAME not set'}), 400
    file = request.files.get('photo')
    if not file:
        return jsonify({'error': 'No photo'}), 400
    key = 'uploads/' + uuid.uuid4().hex + '.jpg'
    data = file.read()
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType='image/jpeg')
    recognized = False
    name = None
    similarity = None
    if collection_id:
        r = rek.search_faces_by_image(
            CollectionId=collection_id,
            Image={'S3Object': {'Bucket': bucket, 'Name': key}},
            MaxFaces=5,
            FaceMatchThreshold=80
        )
        face_matches = r.get('FaceMatches', [])
        if face_matches:
            best = max(face_matches, key=lambda x: x.get('Similarity', 0))
            f = best.get('Face', {})
            name = f.get('ExternalImageId')
            similarity = best.get('Similarity')
            recognized = True
    if recognized:
        return jsonify({'bucket': bucket, 'key': key, 'recognized': True, 'name': name, 'similarity': similarity})
    det = rek.detect_faces(
        Image={'S3Object': {'Bucket': bucket, 'Name': key}},
        Attributes=['ALL']
    )
    faces = det.get('FaceDetails', [])
    face0 = faces[0] if faces else None
    gender = face0.get('Gender', {}).get('Value') if face0 else None
    age = face0.get('AgeRange', {}) if face0 else {}
    emotions = face0.get('Emotions', []) if face0 else []
    dominant = None
    if emotions:
        dominant = max(emotions, key=lambda e: e.get('Confidence', 0)).get('Type')
    analysis = {
        'facesDetected': len(faces),
        'gender': gender,
        'ageRange': {'low': age.get('Low'), 'high': age.get('High')},
        'dominantEmotion': dominant,
        'emotions': [{'type': e.get('Type'), 'confidence': e.get('Confidence')} for e in emotions[:5]]
    }
    return jsonify({'bucket': bucket, 'key': key, 'recognized': False, 'message': 'kamu tidak dikenali', 'analysis': analysis})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5001')))