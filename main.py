from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import hashlib
import os
import re

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'resources.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), nullable=False, unique=True)
    password = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def __init__(self, username, password, is_admin=False):
        self.username = username
        self.password = hashlib.sha256(password.encode()).hexdigest()
        self.is_admin = is_admin

# Course model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), index=True, nullable=False)
    description = db.Column(db.Text)
    resources = db.relationship('Resource', backref='course', lazy=True)

# Resource model
class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# Enrollment model
class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

# Authentication routes
@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    is_admin = request.form.get('is_admin', False)

    # Input validation
    if not username or not password or len(username) > 10:
        return jsonify({'message': 'Invalid username'}), 400

    password_pattern = r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$'
    if not re.match(password_pattern, password):
        return jsonify({'message': 'Password must contain at least one uppercase letter, one digit and one special character'}), 400


    user = User(username=username, password=password, is_admin=is_admin)
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.password == hashlib.sha256(password.encode()).hexdigest():
        return jsonify({'message': 'Login successful', 'is_admin': user.is_admin})
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

# Course routes (accessible to admins only)
@app.route('/courses', methods=['GET', 'POST'])
def courses():
    if request.method == 'GET':
        courses = Course.query.all()
        return jsonify([{'id': course.id, 'name': course.name, 'description': course.description} for course in courses])

    elif request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')

        course = Course(name=name, description=description)
        db.session.add(course)
        db.session.commit()

        return jsonify({'message': 'Course added successfully'}), 201

@app.route('/courses/<int:course_id>', methods=['PUT', 'DELETE'])
def course(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'PUT':
        name = request.form.get('name', course.name)
        description = request.form.get('description', course.description)
        course.name = name
        course.description = description
        db.session.commit()
        return jsonify({'message': 'Course updated successfully'})

    elif request.method == 'DELETE':
        db.session.delete(course)
        db.session.commit()
        return jsonify({'message': 'Course deleted successfully'})

# Resource routes (accessible to admins only)
@app.route('/courses/<int:course_id>/resources', methods=['GET', 'POST'])
def resources(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'GET':
        resources = course.resources
        return jsonify([{'id': resource.id, 'name': resource.name, 'file_path': resource.file_path} for resource in resources])

    elif request.method == 'POST':
        name = request.form.get('name')
        file = request.files.get('file')

        # Input validation
        if not name or len(name) < 3 or not file:
            return jsonify({'message': 'Invalid resource name or file'}), 400

        file_path = file.filename
        file.save(file_path)

        resource = Resource(name=name, file_path=file_path, course_id=course_id)
        db.session.add(resource)
        db.session.commit()

        return jsonify({'message': 'Resource added successfully'}), 201

@app.route('/resources/<int:resource_id>', methods=['DELETE'])
def delete_resource(resource_id):
    resource = Resource.query.get_or_404(resource_id)
    os.remove(resource.file_path)
    db.session.delete(resource)
    db.session.commit()
    return jsonify({'message': 'Resource deleted successfully'})

# Enrollment routes
@app.route('/courses/<int:course_id>/enroll', methods=['POST'])
def enroll(course_id):
    username = request.form.get('username')
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    enrollment = Enrollment(user_id=user.id, course_id=course_id)
    db.session.add(enrollment)
    db.session.commit()

    return jsonify({'message': 'Enrolled successfully'})
if __name__ == '__main__':
    app.run(debug=True)