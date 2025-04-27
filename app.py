from face_recognition_app import facial_recognition
from flask import *
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired, MultipleFileField
from wtforms import FileField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length, ValidationError
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import importlib
import time
import shutil
import subprocess
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ca258998190a853b6a12d1133e083a7463e25f260738307e617560b98394dce3'
app.config['UPLOAD_FOLDER'] = 'static/files'
app.config['FACE_LOCATION'] = 'face_recognition_app/dataset'
app.config['TRAINING_LOCATION'] = 'face_recognition_app/model_training.py'
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'users.db')
logs_path = os.path.join(basedir, 'logs.db')
pickle_path = os.path.join(basedir, 'face_recognition_app/encodings.pickle')
app.config['PICKLE_LOCATION'] = f'{pickle_path}'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}' # Connects app to the database for users
app.config['SQLALCHEMY_BINDS'] = {
            'logs': f'sqlite:///{logs_path}'
        }
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

print(logs_path)

bcrypt = Bcrypt(app)
facial_recognition.load_encodings()

# Create the pickle file if one doesn't exist
if (not os.path.exists(pickle_path)):
    f = open(pickle_path, "w")
    f.close()

# Creates the "upload" button for users to upload face files
class UploadFileForm(FlaskForm):
    file = FileField("File", validators=[InputRequired()])
    submit = SubmitField("Upload")

class AddUserForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=2, max=30)], render_kw={"placeholder": "Name"})
    files = MultipleFileField("Files", validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
        ])
    submit = SubmitField("Add User")

    def validate_name(self, name):
        folder_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                app.config["FACE_LOCATION"],
                secure_filename(name.data)
                )

        if os.path.isdir(folder_path):
            raise ValidationError("A user with that name already exists.")

# Represents a User in the database, with an id, a unique username, and a password
#for login
#class User(db.Model, UserMixin):
#    id = db.Column(db.Integer, primary_key=True)
#    username = db.Column(db.String(20), nullable=False, unique=True)
#    password = db.Column(db.String(80), nullable=False)
#
#    def __init__(self, username, password):
#        self.username = username
#        self.password = password

#Represents a User in the database with a name
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __init__(self, name):
        self.name = name

class Log(db.Model):
    __bind_key__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(100), unique=True)
    name = db.Column(db.String(50))
    photo_filename = db.Column(db.String(100))

    def __init__(self, date, name, photo_filename):
        self.date = date
        self.name = name
        self.photo_filename = photo_filename

with app.app_context():
    db.create_all()

class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
                username=username.data).first()

        if existing_user_username:
            raise ValidationError(
                    "That username already exists. Please choose a different one.")

class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")
	
@app.route('/', methods=["GET", "POST"])
def default():
    return render_template("index.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    return render_template("login.html", form=form)

@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()

    # If a user successfully registers, store their hashed password and redirect them to the login page
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template("register.html", form=form)

@app.route('/main', methods=["GET", "POST"])
def main():
    logs = Log.query.all()

    return render_template("main.html", logs=logs)

@app.route('/video')
def video():
    return Response(facial_recognition.generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/create_log', methods=["POST"])
def create_log():
    data = request.get_json()

    faces = data.get("faces", [])
    names = ", ".join(faces)
    names = names.replace("_", " ")

    date = data.get("time")

    photo_filename = data.get("photo_filename")

    # Add a new log to the database
    new_log = Log(date=date, name=names, photo_filename=photo_filename)
    db.session.add(new_log)
    db.session.commit()

    logs = Log.query.all()

    return render_template("main.html", logs=logs)

@app.route('/refresh_logs', methods=["GET", "POST"])
def refresh_logs():
    return redirect(url_for('main'))

@app.route('/delete_logs', methods=["GET", "POST"])
def delete_logs():
    logs = Log.query.all()
    folder = "log_photos"

    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        os.remove(file_path)

    Log.query.delete()
    db.session.commit()

    return redirect(url_for('main'))

@app.route('/log_photos/<path:filename>')
def serve_log_photos(filename):
    return send_from_directory('log_photos', filename)


@app.route('/add', methods=["GET", "POST"])
def add():
    add_form = AddUserForm()

    # If form is submitted, create a new directory in FACE_LOCATIONS with the new name 
    if add_form.submit.data and add_form.validate_on_submit():
        name = add_form.name.data.strip()
        files = request.files.getlist(add_form.files.name)
        
        # Create the directory
        dir = os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                app.config['FACE_LOCATION'],
                secure_filename(name))

        os.mkdir(dir)

        for file in files:
            file.save(os.path.join(dir, secure_filename(file.filename)))

        # Trains the model
        path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                app.config['TRAINING_LOCATION'])
        subprocess.run(['python3', path], check=True, cwd=os.path.dirname(path))
        facial_recognition.load_encodings()

        # Add the user to the database
        new_user = User(name=name)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("add"))

    users = User.query.all()

    return render_template("add.html", add_form=add_form, users=users)

@app.route('/remove_user/<int:user_id>', methods=["POST"])
def remove_user(user_id):
    user = db.session.get(User, user_id)
    name = user.name.strip()

    if user is None:
        abort(404)

    # Remove the dataset folder
    shutil.rmtree(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                app.config['FACE_LOCATION'],
                secure_filename(name))
            )

    # Re-train the model
    os.remove(
            os.path.join(
                os.path.abspath(os.path.dirname(__file__)),
                app.config['PICKLE_LOCATION'])
            )

    path = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            app.config['TRAINING_LOCATION'])
    subprocess.run(['python3', path], check=True, cwd=os.path.dirname(path))
    facial_recognition.load_encodings()

    # Remove from database
    db.session.delete(user)
    db.session.commit()

    return redirect(url_for("add"))

with app.app_context():
    db.create_all()
    db.create_all(bind_key=['logs'])

if __name__ == "__main__":
    app.run(host='0.0.0.0.', port=5000, debug=True, threaded=True)


