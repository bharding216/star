from flask import Blueprint, render_template, request, redirect, flash, url_for, \
    session, send_file, jsonify, make_response, Response, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from project.models import bids, bid_contact, admin_login, supplier_info, project_meta, supplier_login, \
                            gov_login
from datetime import datetime
import datetime
# from flask_mail import Message
from . import db, mail
# from helpers import generate_sitemap
from werkzeug.security import generate_password_hash, check_password_hash
# from itsdangerous.exc import BadSignature
import os
import uuid
import string
import shutil

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html',
                           user = current_user
                           )


@views.route('/contact', methods=['GET', 'POST'])
def contact():
    return render_template('contact.html',
                           user = current_user
                           )




@views.route('/registration_personal', methods=['GET', 'POST'])
def registration_personal():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        company_name = request.form['company_name']
        email = request.form['email']
        phone = request.form['phone']
        password1 = request.form['password1']
        password2 = request.form['password2']

        if password1 != password2:
            flash('Passwords do not match. Please try again.', category='error')
            return render_template('registration_personal.html',
                                   user = current_user,
                                   first_name = first_name,
                                   last_name = last_name,
                                   company_name = company_name,
                                   email = email,
                                   phone = phone
                                   )
        else:
            session['first_name'] = first_name
            session['last_name'] = last_name
            session['company_name'] = company_name
            session['email'] = email
            session['phone'] = phone
            session['password'] = password1

        return redirect(url_for('views.registration_location'))

    return render_template('registration_personal.html',
                           user = current_user
                           )


@views.route('/registration_location', methods=['GET', 'POST'])
def registration_location():
    if request.method == "POST":
        address_1 = request.form['address_1']
        address_2 = request.form['address_2']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']

        session['address_1'] = address_1
        session['address_2'] = address_2
        session['city'] = city
        session['state'] = state
        session['zip_code'] = zip_code

        return redirect(url_for('views.registration_business'))

    return render_template('registration_location.html',
                           user = current_user
                           )


@views.route('/registration_business', methods=['GET', 'POST'])
def registration_business():
    if request.method == "POST":
        duns = request.form['duns']
        ein = request.form['ein']
        legal_structure = request.form['legal_structure']

        session['duns'] = duns
        session['ein'] = ein
        session['legal_structure'] = legal_structure

        hashed_password = generate_password_hash(session['password'])

        with db.session() as db_session:
            new_supplier_info_record = supplier_info(first_name = session['first_name'],
                                                     last_name = session['last_name'],
                                                     company_name = session['company_name'],
                                                     email = session['email'],
                                                     phone = session['phone'],
                                                     address_1 = session['address_1'],
                                                     address_2 = session['address_2'],
                                                     city = session['city'],
                                                     state = session['state'],
                                                     zip_code = session['zip_code'],
                                                     duns = session['duns'],
                                                     tax_id = session['ein'],
                                                     legal_type = session['legal_structure'],
                                                     )
            db_session.add(new_supplier_info_record)
            db_session.commit()

            new_supplier_info_record_id = new_supplier_info_record.id

            new_supplier_login_record = supplier_login(supplier_id = new_supplier_info_record_id,
                                                       email = session['email'],
                                                       password = hashed_password
                                                       )
            db_session.add(new_supplier_login_record)
            db_session.commit()

        flash('New supplier profile created! Please login using your email and password to \
              apply for open bids.', category='success')
        return redirect(url_for('views.index'))



    return render_template('registration_business.html',
                           user = current_user
                           )











@views.route('/manage_project', methods=['GET', 'POST'])
def manage_project():
    if request.method == 'POST':
        file = request.files['file']
        filename = file.filename
        now = datetime.datetime.now()
        date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        user_id = current_user.id
        project_title = request.form['project_title']
        bid_type = request.form['bid_type']
        organization = request.form['organization']
        issue_date = request.form['issue_date']
        close_date = request.form['close_date']
        notes = request.form['notes']
        
        # Replace any invalid characters in the title and date_time_stamp_for_dir strings with underscores
        valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
        fixed_filename = ''.join(c if c in valid_chars else '_' for c in filename)
        # date_time_stamp_for_dir = ''.join(c if c in valid_chars else '_' for c in date_time_stamp)

        UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

        # ORIGINAL CODE
        # The purpose of the following if-statements is to check if the 
        # directories already exist. This way, you won't try to create
        # two folders in the same directory with the same name. 
        user_dir = os.path.join(UPLOAD_FOLDER, str(user_id))
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)

        project_dir = os.path.join(user_dir, str(project_title))
        if not os.path.exists(project_dir):
            os.makedirs(project_dir)

        upload_dir = os.path.join(project_dir, str(fixed_filename))
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        os.makedirs(upload_dir, exist_ok=True)

        # Generate a random UUID. This value is based on current time stamp 
        # and a random 14-bit sequence number. It is used to give a unique name
        # to each uploaded file. Here, you save the file at that filepath
        # with that UUID filename.
        file_identifier = str(uuid.uuid4())
        filepath = os.path.join(upload_dir, file_identifier)
        file.save(filepath)

        new_project_record = {
            'title': project_title,
            'type': bid_type,
            'organization': organization,
            'issue_date': issue_date,
            'close_date': close_date,
            'notes': notes,
            'status': 'open'
        }

        with db.session() as db_session:
            new_project = bids(**new_project_record)
            db_session.add(new_project)
            db_session.commit()
            new_project_id = new_project.id

        new_metadata_record = {
            'title': fixed_filename,
            'uploaded_by_user_id': user_id,
            'date_time_stamp': date_time_stamp,
            'filename_uuid': file_identifier,
            'bid_id': new_project_id
        }

        with db.session() as db_session:
            new_project = project_meta(**new_metadata_record)
            db_session.add(new_project)
            db_session.commit()

        flash('Project created successfully!', 'success')
        return redirect(url_for('views.manage_project'))

    # Handle GET request:
    with db.session() as db_session:
        bid_list = db_session.query(project_meta, bids) \
                              .join(bids) \
                              .all()

    return render_template('manage_project.html',
                           user = current_user,
                           bid_list = bid_list
                           )




@views.route('/download_project', methods = ['GET', 'POST'])
def download_project():
    # date_time_stamp = request.form['date_time_stamp']
    project_title = request.form['project_title']
    filename = request.form['filename']
    filename_uuid = request.form['filename_uuid']
    user_id = request.form['uploaded_by_user_id']

    # Replace any invalid characters in the title and date_time_stamp_for_dir strings with underscores
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    project_title = ''.join(c if c in valid_chars else '_' for c in project_title)
    filename = ''.join(c if c in valid_chars else '_' for c in filename)

    # date_time_stamp_for_dir = ''.join(c if c in valid_chars else '_' for c in date_time_stamp)

    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    upload_dir = os.path.join(UPLOAD_FOLDER, str(user_id), str(project_title), str(filename))

    # Force download as a PDF.
    response = make_response(send_from_directory(upload_dir, filename_uuid, as_attachment=True, mimetype='application/pdf'))
    response.headers["Content-Disposition"] = f"attachment; filename={filename}.pdf"
    return response






@views.route('/delete_project', methods = ['GET', 'POST'])
@login_required
def delete_project():
    project_id = request.form['project_id']
    # date_time_stamp = request.form['date_time_stamp']
    project_title = request.form['project_title']
    filename = request.form['filename']
    filename_uuid = request.form['filename_uuid']
    user_id = request.form['uploaded_by_user_id']

    # Replace any invalid characters in the title and date_time_stamp_for_dir strings with underscores.
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    project_title = ''.join(c if c in valid_chars else '_' for c in project_title)
    filename = ''.join(c if c in valid_chars else '_' for c in filename)
    # date_time_stamp_for_dir = ''.join(c if c in valid_chars else '_' for c in date_time_stamp)

    # Delete the folder from the app.
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    dir_to_delete = os.path.join(UPLOAD_FOLDER, str(user_id), str(project_title), str(filename))
    shutil.rmtree(dir_to_delete)

    # Then delete the meta data from the database.
    with db.session() as db_session:
        obj = db_session.query(project_meta).get(project_id)
        db_session.delete(obj)
        db_session.commit()

        bid_to_delete = db_session.query(bids).filter_by(id = obj.bid_id).first()
        db_session.delete(bid_to_delete)
        db_session.commit()

    flash('Project deleted successfully.', 'success')
    return redirect(url_for('views.manage_project'))








@views.route('/current_bids', methods=['GET', 'POST'])
def current_bids():
    with db.session() as db_session:
        open_bids = db_session.query(project_meta, bids) \
                              .join(bids) \
                              .filter(bids.status=='open') \
                              .all()

    return render_template('current_bids.html',
                        open_bids = open_bids,
                        user = current_user
                        )





@views.route('/closed_bids', methods=['GET', 'POST'])
def closed_bids():
    return render_template('closed_bids.html',
                           user = current_user
                           )

@views.route('/awarded_bids', methods=['GET', 'POST'])
def awarded_bids():
    return render_template('awarded_bids.html',
                           user = current_user
                           )

@views.route('/bid_details', methods=['GET', 'POST'])
def bid_details():
    return render_template('bid_details.html',
                           user = current_user
                           )






@views.route('/login_supplier', methods=['GET', 'POST'])
def login_supplier():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        user = supplier_login.query.filter_by(email = email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember = True)
                session['user_type'] = 'supplier'
                session.permanent = True
                flash('Login successful!', category = 'success')
                return redirect(url_for('views.index'))
            else:
                flash('Incorrect password. Please try again.', category = 'error')
                return redirect(url_for('views.login_supplier', email = email))
        else:
            flash('That email is not associated with an account.', category = 'error')

    return render_template('login_supplier.html',
                           user = current_user
                           )


@views.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        user = admin_login.query.filter_by(email = email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember = True)
                session['user_type'] = 'admin'
                session.permanent = True
                flash('Login successful!', category = 'success')
                return redirect(url_for('views.index'))
            else:
                flash('Incorrect password. Please try again.', category = 'error')
                return redirect(url_for('views.login_admin', email = email))
        else:
            flash('That email is not associated with an account.', category = 'error')

    return render_template('login_admin.html',
                           user = current_user
                           )


@views.route('/login_gov', methods=['GET', 'POST'])
def login_gov():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        user = gov_login.query.filter_by(email = email).first()
        if user:
            if check_password_hash(user.password, password):
                login_user(user, remember = True)
                session['user_type'] = 'gov'
                session.permanent = True
                flash('Login successful!', category = 'success')
                return redirect(url_for('views.index'))
            else:
                flash('Incorrect password. Please try again.', category = 'error')
                return redirect(url_for('views.login_gov', email = email))
        else:
            flash('That email is not associated with an account.', category = 'error')

    return render_template('login_gov.html',
                           user = current_user
                           )



@views.route('/admin_signup', methods=['GET', 'POST'])
def admin_signup():
    if request.method == "POST":
        email = request.form['email']
        password1 = request.form['password1']
        password2 = request.form['password2']
        secret_code = request.form['secret_code']

        if secret_code != os.getenv('secret_admin_code'):
            flash('That secret code is incorrect. Please contact us if you need assistance.', category='error')
            return render_template('admin_signup.html',
                                   email = email,
                                   user = current_user)            

        if password1 != password2:
            flash('Passwords do not match. Please try again.', category='error')
            return render_template('admin_signup.html',
                                   user = current_user)

        else:
            hashed_password = generate_password_hash(password1)
            new_admin = admin_login(password=hashed_password, 
                                    email=email
                                    )
            db.session.add(new_admin)
            db.session.commit()
            flash('Admin account successfully created!', category='success')
            return redirect(url_for('views.index'))

    else:
        return render_template('admin_signup.html',
                               user = current_user
                               )


@views.route("/logout")
@login_required
def logout():
    flash('User successfully logged out', category='success')
    logout_user()

    return redirect(url_for('views.index'))


@views.route('/terms', methods=['GET', 'POST'])
def terms():
    return render_template('terms.html',
                           user = current_user
                           )


@views.route('/privacy_policy', methods=['GET', 'POST'])
def privacy():
    return render_template('privacy.html',
                           user = current_user
                           )