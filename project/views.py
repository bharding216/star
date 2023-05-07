from flask import Blueprint, render_template, request, redirect, flash, url_for, \
    session, send_file, jsonify, make_response, Response, send_from_directory
from flask_login import login_required, current_user, login_user, logout_user
from project.models import bids, bid_contact, admin_login, supplier_info, project_meta, supplier_login, applicant_docs
from datetime import datetime
import datetime
from flask_mail import Message
from . import db, mail
from helpers import generate_sitemap
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from itsdangerous.exc import BadSignature
from itsdangerous.url_safe import URLSafeSerializer
import os
import uuid
import string
import shutil
import boto3 
from botocore.exceptions import NoCredentialsError
import requests
from io import BytesIO
from werkzeug.datastructures import Headers


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html',
                           user = current_user
                           )


@views.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Handle the form data
        #
        #

        flash("Thanks for reaching out! We'll get back to you within 1 business day.", category='success')
        return redirect(url_for('views.index'))

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
            session['password'] = generate_password_hash(password1)

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
        legal_structure = request.form['legal_structure']
        session['legal_structure'] = legal_structure

        radio_type = request.form['radio_type']
        if radio_type == 'individual':
            ssn = request.form['ssn']
            session['ssn'] = ssn

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
                                                        ssn = session['ssn'],
                                                        legal_type = session['legal_structure']
                                                        )
                db_session.add(new_supplier_info_record)
                db_session.commit()
                
                new_supplier_info_record_id = new_supplier_info_record.id

                new_supplier_login_record = supplier_login(supplier_id = new_supplier_info_record_id,
                                                        email = session['email'],
                                                        password = session['password']
                                                        )
                db_session.add(new_supplier_login_record)
                db_session.commit()

        if radio_type == 'company':
            ein = request.form['ein']
            duns = request.form['duns']
            session['ein'] = ein
            session['duns'] = duns

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
                                                        ein = session['ein'],
                                                        duns = session['duns'],
                                                        legal_type = session['legal_structure']
                                                        )
            
                db_session.add(new_supplier_info_record)
                db_session.commit()

                new_supplier_info_record_id = new_supplier_info_record.id

                new_supplier_login_record = supplier_login(supplier_id = new_supplier_info_record_id,
                                                        email = session['email'],
                                                        password = session['password']
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
@login_required
def manage_project():
    if request.method == 'POST':
        files = request.files.getlist('file[]')
        now = datetime.datetime.now()
        date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        secure_date_time_stamp = secure_filename(date_time_stamp)
        user_id = current_user.id
        project_title = request.form['project_title']
        bid_type = request.form['bid_type']
        organization = request.form['organization']
        issue_date = request.form['issue_date']
        close_date = datetime.datetime.strptime(request.form['close_date'], '%Y-%m-%d')
        close_time_str = request.form['close_time']
        close_datetime_str = f"{close_date} {close_time_str}"
        close_datetime_obj = datetime.datetime.strptime(close_datetime_str, '%Y-%m-%d %H:%M')
        notes = request.form['notes']
        
        # First, create a new project record. Get the project record ID, then
        # use that ID to create a 'project_meta' record for each file that was uploaded.
        new_project_record = {
            'title': project_title,
            'type': bid_type,
            'organization': organization,
            'issue_date': issue_date,
            'close_date': close_datetime_obj,
            'notes': notes,
            'status': 'open'
        }

        with db.session() as db_session:
            new_project = bids(**new_project_record)
            db_session.add(new_project)
            db_session.commit()
            new_project_id = new_project.id


        # Configure S3 credentials
        s3 = boto3.client('s3', region_name='us-east-1',
                        aws_access_key_id=os.getenv('s3_access_key_id'),
                        aws_secret_access_key=os.getenv('s3_secret_access_key'))
        
        # Set the name of your S3 bucket
        S3_BUCKET = 'star-uploads-bucket'

        for file in files:
            s3_filename = f"{secure_date_time_stamp}_{secure_filename(file.filename)}"
            s3.upload_fileobj(file, S3_BUCKET, s3_filename)

            new_metadata_record = {
                'title': file.filename,
                'uploaded_by_user_id': user_id,
                'date_time_stamp': date_time_stamp,
                'bid_id': new_project_id
            }

            with db.session() as db_session:
                new_project = project_meta(**new_metadata_record)
                db_session.add(new_project)
                db_session.commit()

        flash('Project created successfully! All files have been uploaded.', 'success')
        return redirect(url_for('views.manage_project'))

    # Handle GET request:
    with db.session() as db_session:
        bid_list = db_session.query(bids).all()

    return render_template('manage_project.html',
                           user = current_user,
                           bid_list = bid_list
                           )



@views.route('/view_bid_details', methods=['GET', 'POST'])
def view_bid_details():
    if request.method == 'POST':
        bid_id = request.form['bid_id']

    with db.session() as db_session:
        bid_object = db_session.query(bids) \
                              .filter_by(id = bid_id) \
                              .first()

        project_meta_records = db_session.query(project_meta) \
                                         .filter_by(bid_id = bid_object.id) \
                                         .all()

        applications_for_bid = db_session.query(applicant_docs) \
                                         .filter_by(bid_id = bid_object.id) \
                                         .all()

        return render_template('view_bid_details.html', 
                                user = current_user,
                                bid_object = bid_object,
                                project_meta_records = project_meta_records,
                                applications_for_bid = applications_for_bid)



@views.route('/view_application', methods=['GET', 'POST'])
@login_required
def view_application():
    if request.method == 'POST':
        bid_id = request.form['bid_id']
        supplier_id = request.form['supplier_id']

    with db.session() as db_session:
        bid_object = db_session.query(bids) \
                              .filter_by(id = bid_id) \
                              .first()

        applications_for_bid_and_supplier = db_session.query(applicant_docs) \
                                         .filter_by(bid_id = bid_object.id) \
                                         .filter_by(supplier_id = supplier_id) \
                                         .all()

        return render_template('view_application.html', 
                                user = current_user,
                                bid_object = bid_object,
                                applications_for_bid_and_supplier = applications_for_bid_and_supplier)




@views.route('/apply_for_bid', methods=['GET', 'POST'])
@login_required
def apply_for_bid():
    if request.method == 'POST':
        files = request.files.getlist('file[]')
        bid_id = request.form['bid_id']
        supplier_id = current_user.supplier.id
        now = datetime.datetime.now()
        date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        secure_date_time_stamp = secure_filename(date_time_stamp)

        # Configure S3 credentials
        s3 = boto3.client('s3', region_name='us-east-1',
                        aws_access_key_id=os.getenv('s3_access_key_id'),
                        aws_secret_access_key=os.getenv('s3_secret_access_key'))
        
        # Set the name of your S3 bucket
        S3_BUCKET = 'star-uploads-bucket'

        for file in files:
            s3_filename = f"{secure_date_time_stamp}_{secure_filename(file.filename)}"
            s3.upload_fileobj(file, S3_BUCKET, s3_filename)

            new_applicant_record = {
                'filename': file.filename,
                'date_time_stamp': date_time_stamp,
                'supplier_id': supplier_id,
                'bid_id': bid_id
            }

            with db.session() as db_session:
                new_application = applicant_docs(**new_applicant_record)
                db_session.add(new_application)
                db_session.commit()

        flash('Your application was successfully submitted!', category='success')
        
        with db.session() as db_session:
            applications_for_bid_and_supplier = db_session.query(applicant_docs) \
                                                        .filter_by(bid_id = bid_id) \
                                                        .filter(applicant_docs.supplier_id == supplier_id) \
                                                        .all()

            if applications_for_bid_and_supplier is not None:
                applied_status = 'applied'
            else:
                applied_status = 'not applied'

            bid_object = db_session.query(bids) \
                                .filter_by(id = bid_id) \
                                .first()

            project_meta_records = db_session.query(project_meta) \
                                            .filter_by(bid_id = bid_object.id) \
                                            .all()

            applications_for_bid = db_session.query(applicant_docs) \
                                            .filter_by(bid_id = bid_object.id) \
                                            .all()

            return render_template('view_bid_details.html', 
                                    user = current_user,
                                    bid_object = bid_object,
                                    project_meta_records = project_meta_records,
                                    applied_status = applied_status,
                                    applications_for_bid_and_supplier = applications_for_bid_and_supplier,
                                    applications_for_bid = applications_for_bid)


@views.route('/download_application_doc', methods = ['GET', 'POST'])
def download_application_doc():
    if request.method == 'POST':
        filename = request.form['filename']
        date_time_stamp = request.form['date_time_stamp']
        secure_date_time_stamp = secure_filename(date_time_stamp)

        s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

        s3 = boto3.client('s3', region_name='us-east-1',
                        aws_access_key_id=os.getenv('s3_access_key_id'),
                        aws_secret_access_key=os.getenv('s3_secret_access_key'))

        S3_BUCKET = 'star-uploads-bucket'

        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': s3_filename
            },
            ExpiresIn=3600
        )

        response = requests.get(url)

        download_filename = secure_filename(filename)

        headers = Headers()
        headers.add('Content-Disposition', 'attachment', filename=download_filename)
        response.headers['Content-Disposition'] = 'attachment; filename=' + download_filename

        return Response(BytesIO(response.content), headers=headers)


@views.route('/delete_application_doc', methods = ['GET', 'POST'])
@login_required
def delete_application_doc():
    bid_id = request.form['bid_id']
    doc_id = request.form['doc_id']
    filename = request.form['filename']
    date_time_stamp = request.form['date_time_stamp']
    secure_date_time_stamp = secure_filename(date_time_stamp)
    supplier_id = current_user.supplier.id

    s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

    # Configure S3 credentials
    s3 = boto3.client('s3', region_name='us-east-1',
                    aws_access_key_id=os.getenv('s3_access_key_id'),
                    aws_secret_access_key=os.getenv('s3_secret_access_key'))

    # Set the name of your S3 bucket
    S3_BUCKET = 'star-uploads-bucket'

    s3.delete_object(Bucket=S3_BUCKET, Key=s3_filename)

    # Then delete the meta data from the project_meta table.
    with db.session() as db_session:
        record_to_delete = db_session.query(applicant_docs).get(doc_id)
        db_session.delete(record_to_delete)
        db_session.commit()

        applications_for_bid_and_supplier = db_session.query(applicant_docs) \
                                                    .filter_by(bid_id = bid_id) \
                                                    .filter(applicant_docs.supplier_id == supplier_id) \
                                                    .all()

        if applications_for_bid_and_supplier is not None:
            applied_status = 'applied'
        else:
            applied_status = 'not applied'

        flash('Document deleted successfully.', 'success')
        bid_object = db_session.query(bids) \
                                .filter_by(id = bid_id) \
                                .first()

        project_meta_records = db_session.query(project_meta) \
                                            .filter_by(bid_id = bid_object.id) \
                                            .all()

        return render_template('view_bid_details.html', 
                                user = current_user,
                                bid_object = bid_object,
                                project_meta_records = project_meta_records,
                                applied_status = applied_status,
                                applications_for_bid_and_supplier = applications_for_bid_and_supplier)





@views.route('/upload_doc', methods=['GET', 'POST'])
def upload_doc():
    if request.method == 'POST':
        bid_id = request.form['bid_id']
        files = request.files.getlist('file[]')
        now = datetime.datetime.now()
        date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        secure_date_time_stamp = secure_filename(date_time_stamp)
        user_id = current_user.id


        # Configure S3 credentials
        s3 = boto3.client('s3', region_name='us-east-1',
                        aws_access_key_id=os.getenv('s3_access_key_id'),
                        aws_secret_access_key=os.getenv('s3_secret_access_key'))
        
        # Set the name of your S3 bucket
        S3_BUCKET = 'star-uploads-bucket'

        for file in files:
            s3_filename = f"{secure_date_time_stamp}_{secure_filename(file.filename)}"
            s3.upload_fileobj(file, S3_BUCKET, s3_filename)

            new_metadata_record = {
                'title': file.filename,
                'uploaded_by_user_id': user_id,
                'date_time_stamp': date_time_stamp,
                'bid_id': bid_id
            }

            with db.session() as db_session:
                new_project = project_meta(**new_metadata_record)
                db_session.add(new_project)
                db_session.commit()

        flash('File(s) uploaded successfully!', 'success')

        with db.session() as db_session:
            bid_object = db_session.query(bids) \
                                .filter_by(id = bid_id) \
                                .first()

            project_meta_records = db_session.query(project_meta) \
                                            .filter_by(bid_id = bid_object.id) \
                                            .all()

            return render_template('view_bid_details.html', 
                                    user = current_user,
                                    bid_object = bid_object,
                                    project_meta_records = project_meta_records)






@views.route('/download_project', methods = ['GET', 'POST'])
def download_project():
    if request.method == 'POST':
        filename = request.form['filename']
        date_time_stamp = request.form['date_time_stamp']
        secure_date_time_stamp = secure_filename(date_time_stamp)

        s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

        s3 = boto3.client('s3', region_name='us-east-1',
                        aws_access_key_id=os.getenv('s3_access_key_id'),
                        aws_secret_access_key=os.getenv('s3_secret_access_key'))

        S3_BUCKET = 'star-uploads-bucket'

        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': S3_BUCKET,
                'Key': s3_filename
            },
            ExpiresIn=3600
        )

        response = requests.get(url)

        download_filename = secure_filename(filename)

        headers = Headers()
        headers.add('Content-Disposition', 'attachment', filename=download_filename)
        response.headers['Content-Disposition'] = 'attachment; filename=' + download_filename

        return Response(BytesIO(response.content), headers=headers)










@views.route('/delete_doc', methods = ['GET', 'POST'])
@login_required
def delete_doc():
    bid_id = request.form['bid_id']
    doc_id = request.form['doc_id']
    filename = request.form['filename']
    date_time_stamp = request.form['date_time_stamp']
    secure_date_time_stamp = secure_filename(date_time_stamp)

    s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

    # Configure S3 credentials
    s3 = boto3.client('s3', region_name='us-east-1',
                    aws_access_key_id=os.getenv('s3_access_key_id'),
                    aws_secret_access_key=os.getenv('s3_secret_access_key'))

    # Set the name of your S3 bucket
    S3_BUCKET = 'star-uploads-bucket'

    s3.delete_object(Bucket=S3_BUCKET, Key=s3_filename)

    # Then delete the meta data from the project_meta table.
    with db.session() as db_session:
        record_to_delete = db_session.query(project_meta).get(doc_id)
        db_session.delete(record_to_delete)
        db_session.commit()

    flash('Document deleted successfully.', 'success')
    bid_object = db_session.query(bids) \
                            .filter_by(id = bid_id) \
                            .first()

    project_meta_records = db_session.query(project_meta) \
                                        .filter_by(bid_id = bid_object.id) \
                                        .all()

    return render_template('view_bid_details.html', 
                            user = current_user,
                            bid_object = bid_object,
                            project_meta_records = project_meta_records)




@views.route('/delete_project', methods = ['GET', 'POST'])
@login_required
def delete_project():
    if request.method == 'POST':
        bid_id = request.form['bid_id']

        with db.session() as db_session:
            project_meta_records_to_delete = db_session.query(project_meta) \
                                                       .filter_by(bid_id = bid_id) \
                                                       .all()

            # Configure S3 credentials
            s3 = boto3.client('s3', region_name='us-east-1',
                            aws_access_key_id=os.getenv('s3_access_key_id'),
                            aws_secret_access_key=os.getenv('s3_secret_access_key'))

            # Set the name of your S3 bucket
            S3_BUCKET = 'star-uploads-bucket'

            for record in project_meta_records_to_delete:
                filename = record.title
                date_time_stamp = record.date_time_stamp
                secure_date_time_stamp = secure_filename(date_time_stamp.strftime('%Y-%m-%d %H:%M:%S'))

                s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

                s3.delete_object(Bucket=S3_BUCKET, Key=s3_filename)
                db_session.delete(record)

            bid_to_delete = db_session.query(bids).filter_by(id = bid_id).first()
            db_session.delete(bid_to_delete)
            db_session.commit()
                

        with db.session() as db_session:
            bid_list = db_session.query(bids).all()

            flash('Project successfully deleted!', category='error')
            return render_template('manage_project.html',
                                user = current_user,
                                bid_list = bid_list
                                )




@views.route("/supplier_settings", methods=['GET', 'POST'])
@login_required
def supplier_settings():
    if request.method == 'POST':
        # The name of the category you are updating.
        field_name = request.form['field_name']

        return render_template('update_supplier_settings.html', 
                               user = current_user, 
                               field_name = field_name)

    return render_template('supplier_settings.html', user = current_user)


@views.route("/update_supplier_settings/<string:field_name>", methods=['GET', 'POST'])
@login_required
def update_supplier_settings(field_name):
    if request.method == 'POST':
        new_value = request.form[field_name]

        if field_name == 'password':
            password2 = request.form['password2']
            if new_value == password2:
                new_value = generate_password_hash(new_value)
                current_user.password = new_value

                with db.session() as db_session:
                    db_session.add(current_user)
                    db_session.commit()

                    flash('Password successfully updated!', 'success')
                    return redirect(url_for('views.supplier_settings'))

            else:
                flash('Those password do not match, please try again.', 'error')
                return render_template('update_supplier_settings.html',
                                    user = current_user,
                                    field_name = field_name)

        supplier_info_obj = current_user.supplier
        setattr(supplier_info_obj, field_name, new_value)

        with db.session() as db_session:
            db_session.commit()
            flash('Your settings have been successfully updated!', 'success')
            return redirect(url_for('views.supplier_settings'))
    else:
        return render_template('update_supplier_settings.html')




@views.route('/current_bids', methods=['GET', 'POST'])
def current_bids():
    with db.session() as db_session:
        bid_list = db_session.query(bids).all()

    return render_template('current_bids.html',
                        bid_list = bid_list,
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


@views.route("/reset_password_request/<string:user_type>", methods=['GET', 'POST'])
def reset_password_request(user_type):
    if request.method == "POST":
        email = request.form.get("email")
        
        if user_type == 'supplier':
            user = supplier_login.query.filter_by(email=email).first()
        # else: admin code block to go here

        if user:
            current_time = datetime.datetime.now().time()
            current_time_str = current_time.strftime('%H:%M:%S')

            s = URLSafeSerializer(os.getenv('secret_key'))

            # 'dumps' takes a list as input and serializes it into a string representation.
            # This returns a string representation of the data - encoded using your secret key.
            token = s.dumps([email, current_time_str])

            reset_password_url = url_for('views.reset_password', 
                                          token = token, 
                                          _external=True
                                          )

            msg = Message('Password Reset Request', 
                sender = ("STAR", 'hello@stxresources.org'),
                recipients = [email],
                body=f'Reset your password by visiting the following link: {reset_password_url}')

            mail.send(msg) 
            flash('Success! We sent you an email containing a link where you can reset your password.', category = 'success')
            return redirect(url_for('views.index'))

        else:
            flash('That email does not exist in our system. Please try again.', category = 'error')
            return redirect(url_for('views.reset_password_request',
                                     user_type = user_type,
                                     user = current_user
                                     )
                            )
    
    else:
        return render_template("reset_password_form.html", 
                               user_type = user_type,
                               user = current_user)




@views.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if request.method == "POST":

        s = URLSafeSerializer(os.getenv('secret_key'))
        try: 
            # loads => take in a serialized string and generate the original list of string inputs.
            # The first element in the list is the user's email.
            user_email_from_token = (s.loads(token))[0]
        except BadSignature:
            flash('You do not have permission to change the password for this email. Please contact us if you continue to have issues.', category = 'error')
            return redirect(url_for('views.reset_password', 
                                    token = token))

        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if new_password != confirm_password:
            flash('Those passwords do not match. Please try again.', category='error')
            return redirect(url_for('views.reset_password', 
                                    token = token))

        hashed_password = generate_password_hash(new_password)
        
        user = supplier_login.query.filter_by(email = user_email_from_token).first()
        if user is None: # Then it must have been an admin requesting a new password
            user = admin_login.query.filter_by(email = user_email_from_token).first()

        user.password = hashed_password
        db.session.commit()

        flash('Your password has been successfully updated! Please login.', category = 'success')
        return redirect(url_for('views.index'))

    else:
        return render_template("reset_password.html", 
                               user = current_user, 
                               token = token
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