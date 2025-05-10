# Force redeploy: ensure latest code is deployed
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from collections import Counter
import csv
from io import StringIO
from sqlalchemy import and_
from werkzeug.utils import secure_filename
import json
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'dental_clinic.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['DEBUG'] = True  # Enable debugging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
csrf = CSRFProtect(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    patient_email = db.Column(db.String(120), nullable=False)
    patient_phone = db.Column(db.String(20), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    service_type = db.Column(db.String(100), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tooth_conditions = db.relationship('ToothCondition', backref='appointment', lazy=True)

class ToothCondition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    tooth_number = db.Column(db.Integer, nullable=False)  # 1-32
    condition = db.Column(db.String(50), nullable=False)  # e.g., 'cavity', 'crown', 'filling'
    notes = db.Column(db.Text)
    image_url = db.Column(db.String(200))  # Path to uploaded image
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logger.error(f"Internal server error: {error}")
    return render_template('500.html'), 500

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    # Get filter parameters
    service = request.args.get('service', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Base query
    query = Appointment.query
    
    # Apply filters
    if service:
        query = query.filter(Appointment.service_type == service)
    if date_from:
        query = query.filter(Appointment.appointment_date >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Appointment.appointment_date <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    # Get appointments
    appointments = query.order_by(Appointment.appointment_date.desc()).all()
    
    # Get unique services for filter dropdown
    services = db.session.query(Appointment.service_type).distinct().all()
    services = [s[0] for s in services]
    
    # Get service statistics
    service_stats = Counter(appointment.service_type for appointment in appointments)
    
    return render_template('admin.html',
                         appointments=appointments,
                         service_stats=service_stats,
                         services=services,
                         selected_service=service,
                         date_from=date_from,
                         date_to=date_to)

@app.route('/api/appointments/<int:id>', methods=['GET'])
@login_required
def get_appointment(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    appointment = Appointment.query.get_or_404(id)
    return jsonify({
        'id': appointment.id,
        'patient_name': appointment.patient_name,
        'patient_email': appointment.patient_email,
        'patient_phone': appointment.patient_phone,
        'service_type': appointment.service_type,
        'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
        'notes': appointment.notes
    })

@app.route('/api/appointments/<int:id>', methods=['PUT'])
@login_required
def update_appointment(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    appointment = Appointment.query.get_or_404(id)
    data = request.get_json()
    
    try:
        appointment.patient_name = data['patient_name']
        appointment.patient_email = data['patient_email']
        appointment.patient_phone = data['patient_phone']
        appointment.service_type = data['service_type']
        appointment.appointment_date = datetime.strptime(data['appointment_date'], '%Y-%m-%d')
        appointment.notes = data.get('notes', '')
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating appointment {id}: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/appointments/<int:id>', methods=['DELETE'])
@login_required
def delete_appointment(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    appointment = Appointment.query.get_or_404(id)
    try:
        db.session.delete(appointment)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting appointment {id}: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/export/appointments')
@login_required
def export_appointments():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    # Create CSV in memory
    si = StringIO()
    cw = csv.writer(si)
    
    # Write header
    cw.writerow(['ID', 'Patient Name', 'Email', 'Phone', 'Service', 'Date', 'Notes', 'Created At'])
    
    # Write data
    appointments = Appointment.query.order_by(Appointment.appointment_date.desc()).all()
    for appointment in appointments:
        cw.writerow([
            appointment.id,
            appointment.patient_name,
            appointment.patient_email,
            appointment.patient_phone,
            appointment.service_type,
            appointment.appointment_date.strftime('%Y-%m-%d'),
            appointment.notes,
            appointment.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    # Prepare response
    output = si.getvalue()
    si.close()
    
    return send_file(
        StringIO(output),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'appointments_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/appointments', methods=['GET', 'POST'])
def appointments():
    if request.method == 'POST':
        try:
            # Log the full request context
            logger.debug("Processing appointment request")
            logger.debug("Request form data: %s", request.form)
            logger.debug("Request headers: %s", dict(request.headers))
            
            # Validate required fields
            required_fields = ['name', 'email', 'phone', 'date', 'service']
            for field in required_fields:
                if not request.form.get(field):
                    raise ValueError(f"Missing required field: {field}")
            
            # Create appointment object
            new_appointment = Appointment(
                patient_name=request.form['name'],
                patient_email=request.form['email'],
                patient_phone=request.form['phone'],
                appointment_date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
                service_type=request.form['service'],
                notes=request.form.get('notes', '')
            )
            
            # Log the appointment object
            logger.debug("Created appointment object: %s", {
                'patient_name': new_appointment.patient_name,
                'patient_email': new_appointment.patient_email,
                'appointment_date': new_appointment.appointment_date,
                'service_type': new_appointment.service_type
            })
            
            # Check database connection
            try:
                db.session.execute('SELECT 1')
            except Exception as db_error:
                logger.error("Database connection error: %s", str(db_error))
                raise RuntimeError("Database connection error. Please try again later.")
            
            # Save the appointment
            db.session.add(new_appointment)
            db.session.commit()
            
            logger.info("Appointment created successfully: ID=%d", new_appointment.id)
            flash('Appointment scheduled successfully!', 'success')
            return redirect(url_for('appointments'))
            
        except ValueError as ve:
            db.session.rollback()
            error_msg = str(ve)
            logger.warning("Validation error: %s", error_msg)
            flash(f'Please check your input: {error_msg}', 'error')
            return redirect(url_for('appointments'))
            
        except Exception as e:
            db.session.rollback()
            error_msg = str(e)
            logger.error("Error creating appointment: %s", error_msg, exc_info=True)
            logger.error("Database path: %s", app.config['SQLALCHEMY_DATABASE_URI'])
            flash('An error occurred while scheduling the appointment. Please try again later.', 'error')
            return redirect(url_for('appointments'))
            
    return render_template('appointments.html')

@app.route('/services')
def services():

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/api/appointments/<int:id>/teeth', methods=['GET'])
@login_required
def get_tooth_conditions(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    appointment = Appointment.query.get_or_404(id)
    conditions = ToothCondition.query.filter_by(appointment_id=id).all()
    
    return jsonify({
        'conditions': [{
            'id': c.id,
            'tooth_number': c.tooth_number,
            'condition': c.condition,
            'notes': c.notes
        } for c in conditions]
    })

@app.route('/api/appointments/<int:id>/teeth', methods=['POST'])
@login_required
def add_tooth_condition(id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    appointment = Appointment.query.get_or_404(id)
    
    try:
        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(f"{id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                image_url = f"/static/uploads/teeth/{filename}"
        
        condition = ToothCondition(
            appointment_id=id,
            tooth_number=int(request.form['tooth_number']),
            condition=request.form['condition'],
            notes=request.form.get('notes', ''),
            image_url=image_url
        )
        db.session.add(condition)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'condition': {
                'id': condition.id,
                'tooth_number': condition.tooth_number,
                'condition': condition.condition,
                'notes': condition.notes,
                'image_url': image_url
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding tooth condition for appointment {id}: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/appointments/<int:id>/teeth/<int:condition_id>', methods=['DELETE'])
@login_required
def delete_tooth_condition(id, condition_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    condition = ToothCondition.query.filter_by(id=condition_id, appointment_id=id).first_or_404()
    try:
        db.session.delete(condition)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting tooth condition {condition_id} for appointment {id}: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/appointments/<int:id>/teeth')
@login_required
def view_tooth_diagram(id):
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    appointment = Appointment.query.get_or_404(id)
    return render_template('tooth_diagram.html', appointment=appointment)

@app.route('/debug')
def debug():
    headers = dict(request.headers)
    user_agent = request.headers.get('User-Agent', 'No User-Agent')
    return jsonify({
        'headers': headers,
        'user_agent': user_agent,
        'remote_addr': request.remote_addr,
        'is_mobile': 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent
    })

@app.before_request
def before_request():
    # Temporarily disable HTTPS redirect for development
    # if not request.is_secure and app.config.get('ENV') != "development":
    #     url = request.url.replace('http://', 'https://', 1)
    #     return redirect(url, code=301)
    pass

def init_db():
    with app.app_context():
        # Ensure instance directory exists
        instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
        os.makedirs(instance_path, exist_ok=True)
        
        # Set proper permissions for the instance directory
        os.chmod(instance_path, 0o777)
        
        db_path = os.path.join(instance_path, 'dental_clinic.db')
        if os.path.exists(db_path):
            os.chmod(db_path, 0o666)
            
        db.create_all()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@dentalclinic.com',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            
        if os.path.exists(db_path):
            os.chmod(db_path, 0o666)
            
        print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)