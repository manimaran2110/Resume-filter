from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory, send_file
import zipfile
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import PyPDF2
import docx
import shutil
import re
import hashlib
from config import config

app = Flask(__name__)
app.config.from_object(config['development'])  # or 'production', 'testing'
app.config['UPLOAD_FOLDER'] = 'resumes'
app.config['MATCH_FOLDER'] = 'Matching job description'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'Manimaran@1234'  # Replace with a strong secret key

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Ensure base directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MATCH_FOLDER'], exist_ok=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Resume(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(200), nullable=False)
    new_filename = db.Column(db.String(200), nullable=False)
    keywords = db.Column(db.String(200), nullable=False)
    condition = db.Column(db.String(10), nullable=False)
    job_description = db.Column(db.String(200), nullable=False)
    file_hash = db.Column(db.String(32), unique=False, nullable=False)
    email = db.Column(db.String(100), nullable=True)
    contact_number = db.Column(db.String(20), nullable=True)
    name = db.Column(db.String(100), nullable=True)  # New column for storing name
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_id = db.Column(db.String(10), nullable=False, unique=True)

    def __init__(self, original_filename, new_filename, keywords, condition, job_description, file_hash, email, contact_number, name, user_id, job_id):
        self.original_filename = original_filename
        self.new_filename = new_filename
        self.keywords = keywords
        self.condition = condition
        self.job_description = job_description
        self.file_hash = file_hash
        self.email = email
        self.contact_number = contact_number
        self.name = name  # Assign name
        self.user_id = user_id
        self.job_id = job_id


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('upload_file'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def pdf_to_text(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    return text

def docx_to_text(file_path):
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text
    
def txt_to_text(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def sanitize_filename(filename):
    filename = re.sub(r'\s+', '', filename)  # removes whitespace
    return filename

def calculate_hash(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as file:
        buf = file.read()
        hasher.update(buf)
    return hasher.hexdigest()

def extract_email(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None

def extract_contact_number(text):
    contact_pattern = r'\b(?:\d{10}|\+\d{1,2}\s?\d{10}|\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})\b'
    match = re.search(contact_pattern, text)
    return match.group(0) if match else None

# renamed using filename - keywords and extension

# def search_for_keywords(keywords, condition, source_directory, destination_directory, job_description):
#     matching_files = []
#     user_folder = os.path.join(destination_directory, f"user_{current_user.id}")
#     job_folder = os.path.join(user_folder, sanitize_filename(job_description))
#     os.makedirs(job_folder, exist_ok=True)

#     for file_name in os.listdir(source_directory):
#         file_path = os.path.join(source_directory, file_name)

#         if file_name.endswith(".pdf"):
#             text = pdf_to_text(file_path)
#         elif file_name.endswith(".docx"):
#             text = docx_to_text(file_path)
#         elif file_name.endswith(".txt"):
#             text = txt_to_text(file_path)
#         else:
#             continue

#         file_hash = calculate_hash(file_path)
#         if Resume.query.filter_by(file_hash=file_hash, job_description=job_description, user_id=current_user.id).first():
#             continue

#         matched_keywords = [keyword.strip() for keyword in keywords if keyword.lower() in text.lower()]
#         email = extract_email(text)
#         contact_number = extract_contact_number(text)

#         if condition == "and" and all(keyword.lower() in text.lower() for keyword in keywords):
#             new_keywords = '_'.join(keywords)
#             new_filename = f"{sanitize_filename(file_name)}${new_keywords}.pdf"
#             matching_files.append(new_filename)
#             shutil.copy(file_path, os.path.join(job_folder, new_filename))
#             job_id = generate_job_id()  # Generate job ID
#             resume = Resume(
#                 original_filename=file_name,
#                 new_filename=new_filename,
#                 keywords=new_keywords,
#                 condition=condition,
#                 job_description=job_description,
#                 file_hash=file_hash,
#                 email=email,
#                 contact_number=contact_number,
#                 user_id=current_user.id,
#                 job_id=job_id  # Assign job ID to the resume
#             )
#             db.session.add(resume)
#             db.session.commit()
#         elif condition == "or" and matched_keywords:
#             new_keywords = '_'.join(matched_keywords)
#             new_filename = f"{sanitize_filename(file_name)}${new_keywords}.pdf"
#             matching_files.append(new_filename)
#             shutil.copy(file_path, os.path.join(job_folder, new_filename))
#             job_id = generate_job_id()  # Generate job ID
#             resume = Resume(
#                 original_filename=file_name,
#                 new_filename=new_filename,
#                 keywords=new_keywords,
#                 condition=condition,
#                 job_description=job_description,
#                 file_hash=file_hash,
#                 email=email,
#                 contact_number=contact_number,
#                 user_id=current_user.id,
#                 job_id=job_id  # Assign job ID to the resume
#             )
#             db.session.add(resume)
#             db.session.commit()

#     return matching_files


def search_for_keywords(keywords, condition, source_directory, destination_directory, job_description):
    matching_files = []
    user_folder = os.path.join(destination_directory, f"user_{current_user.id}")
    job_folder = os.path.join(user_folder, sanitize_filename(job_description))
    os.makedirs(job_folder, exist_ok=True)

    for file_name in os.listdir(source_directory):
        file_path = os.path.join(source_directory, file_name)

        if file_name.endswith(".pdf"):
            text = pdf_to_text(file_path)
        elif file_name.endswith(".docx"):
            text = docx_to_text(file_path)
        elif file_name.endswith(".txt"):
            text = txt_to_text(file_path)
        else:
            continue

        file_hash = calculate_hash(file_path)
        if Resume.query.filter_by(file_hash=file_hash, job_description=job_description, user_id=current_user.id).first():
            continue

        # Extract name from text
        name = extract_name(text)

        matched_keywords = [keyword.strip() for keyword in keywords if keyword.lower() in text.lower()]
        email = extract_email(text)
        contact_number = extract_contact_number(text)

        if condition == "and" and all(keyword.lower() in text.lower() for keyword in keywords):
            new_keywords = '_'.join(keywords)
            new_filename = f"{generate_job_id()}_{sanitize_filename(file_name)}"
            matching_files.append(new_filename)
            shutil.copy(file_path, os.path.join(job_folder, new_filename))
            job_id = generate_job_id()  # Generate job ID
            resume = Resume(
                original_filename=file_name,
                new_filename=new_filename,
                keywords=new_keywords,
                condition=condition,
                job_description=job_description,
                file_hash=file_hash,
                email=email,
                contact_number=contact_number,
                name=name,  # Assign extracted name
                user_id=current_user.id,
                job_id=job_id  # Assign job ID to the resume
            )
            db.session.add(resume)
            db.session.commit()
        elif condition == "or" and matched_keywords:
            new_keywords = '_'.join(matched_keywords)
            new_filename = f"{generate_job_id()}_{sanitize_filename(file_name)}"
            matching_files.append(new_filename)
            shutil.copy(file_path, os.path.join(job_folder, new_filename))
            job_id = generate_job_id()  # Generate job ID
            resume = Resume(
                original_filename=file_name,
                new_filename=new_filename,
                keywords=new_keywords,
                condition=condition,
                job_description=job_description,
                file_hash=file_hash,
                email=email,
                contact_number=contact_number,
                name=name,  # Assign extracted name
                user_id=current_user.id,
                job_id=job_id  # Assign job ID to the resume
            )
            db.session.add(resume)
            db.session.commit()

    return matching_files

def extract_name(text):
    name_pattern = r'([A-Z][a-z]+(?: [A-Z][a-z]+)*)'  # Simple pattern to match capitalized words (assuming it's a name)
    match = re.search(name_pattern, text)
    return match.group(0) if match else None


def clear_directory(directory):
    for file_name in os.listdir(directory):
        file_path = os.path.join(directory, file_name)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def generate_job_id():
    last_resume = Resume.query.order_by(Resume.id.desc()).first()
    if last_resume:
        last_job_id = last_resume.job_id
        last_num = int(last_job_id[3:])  # Extract numeric part and convert to int
        new_num = last_num + 1
        new_job_id = f"JID{new_num:07}"  # Format with leading zeros
    else:
        new_job_id = "JID0000001"  # Starting job ID if no resumes exist

    return new_job_id


@app.route('/', methods=['GET', 'POST'])
@login_required
def upload_file():
    user_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], f"user_{current_user.id}")
    os.makedirs(user_upload_folder, exist_ok=True)

    if request.method == 'POST':
        clear_directory(user_upload_folder)
        
        job_description = request.form['jobDescription']
        num_keywords = int(request.form['numKeywords'])
        keywords = [request.form.get(f'keyword{i}') for i in range(1, num_keywords + 1) if request.form.get(f'keyword{i}')]
        condition = request.form['condition']
        files = request.files.getlist('file')
        
        for file in files:
            filename = file.filename
            file.save(os.path.join(user_upload_folder, filename))
        
        matching_files = search_for_keywords(keywords, condition, user_upload_folder, app.config['MATCH_FOLDER'], job_description)
        resumes = {file.new_filename: file for file in Resume.query.filter_by(user_id=current_user.id).all()}
        return render_template('result.html', keywords=keywords, files=matching_files, condition=condition, job_description=job_description, resumes=resumes)
    
    return render_template('upload.html')

@app.route('/download_file/<filename>', methods=['GET'])
@login_required
def download_file(filename):
    user_id = current_user.id
    resume = Resume.query.filter_by(new_filename=filename, user_id=user_id).first()
    if resume:
        user_folder = os.path.join(app.config['MATCH_FOLDER'], f"user_{user_id}", sanitize_filename(resume.job_description))
        return send_from_directory(user_folder, filename)
    flash('File not found or unauthorized', 'danger')
    return redirect(url_for('upload_file'))

@app.route('/download_all', methods=['GET'])
def download_all():
    zipf_name = 'all_files.zip'
    zipf_path = os.path.join(app.config['UPLOAD_FOLDER'], zipf_name)
    
    with zipfile.ZipFile(zipf_path, 'w') as zipf:
        for root, _, files in os.walk(app.config['UPLOAD_FOLDER']):
            for file in files:
                zipf.write(os.path.join(root, file), file)
    
    return send_file(zipf_path, as_attachment=True, mimetype='application/zip')


@app.route('/view_db')
@login_required
def view_db():
    resumes = Resume.query.filter_by(user_id=current_user.id).all()
    return render_template('view_db.html', resumes=resumes)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
