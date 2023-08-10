from flask import Blueprint, render_template, request, redirect, flash, url_for, \
    session, send_file, jsonify, make_response, Response, send_from_directory, current_app
from flask_login import login_required, current_user, login_user, logout_user
from sqlalchemy import and_, inspect
from project.models import bids, bid_contact, admin_login, supplier_info, \
    project_meta, supplier_login, applicant_docs, chat_history
from datetime import datetime
import pytz
from dateutil import parser
import datetime
from flask_mail import Message
from . import db, mail
from helpers import generate_sitemap, utc_to_central
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
from io import BytesIO, StringIO
from werkzeug.datastructures import Headers
import logging
import csv


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html',
                           user = current_user
                           )


@views.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        VERIFY_URL = 'https://www.google.com/recaptcha/api/siteverify'
        secret_key = os.getenv('reCAPTCHA_secret_key')
        recaptcha_site_key = os.getenv('reCAPTCHA_site_key')

        # Get the reCAPTCHA response from the form
        recaptcha_response = request.form.get('g-recaptcha-response')
        if recaptcha_response:
            # Verify the reCAPTCHA response using the Google reCAPTCHA API
            response = requests.post(url=VERIFY_URL + '?secret=' + secret_key + '&response=' + recaptcha_response).json()

            if response['success'] == True:
                first_name = request.form['first_name']
                last_name = request.form['last_name']
                email = request.form['email']
                phone = request.form['phone']
                message = request.form['message']

                if not first_name:
                    error = 'First name is required.'
                elif not email:
                    error = 'Email field is required.'
                elif not message:
                    error = 'Message is required.'
                else:
                    error = None
                
                if not error:
                    msg = Message('New Contact Form Submission',
                                    sender = ("STAR", 'hello@stxresources.org'),
                                    recipients = ['bharding80@gmail.com'
                                                ]
                                    )
                                    #'Micah@earl-law.com'
                    

                    msg.html = render_template('contact_email.html',
                                            first_name = first_name,
                                            last_name = last_name,
                                            email = email,
                                            phone = phone,
                                            message = message
                                            )

                    mail.send(msg)

                    return render_template('contact_success.html', 
                                            first_name = first_name,
                                            email = email, 
                                            phone = phone, 
                                            message = message,
                                            user = current_user
                                            )
                else:
                    flash(error, category='error')
                    recaptcha_site_key = os.getenv('reCAPTCHA_site_key')
                    return render_template('contact.html', 
                                           user = current_user,
                                           recaptcha_site_key = recaptcha_site_key,
                                           first_name = first_name,
                                           last_name = last_name,
                                           email = email,
                                           phone = phone,
                                           message = message)


            else:
                flash('Invalid reCAPTCHA. Please try again.')
                return redirect(url_for('views.contact'))
        else:
            flash('Please complete the reCAPTCHA.')
            return redirect(url_for('views.contact'))



    recaptcha_site_key = os.getenv('reCAPTCHA_site_key')
    return render_template('contact.html', 
                           user = current_user,
                           recaptcha_site_key = recaptcha_site_key)




@views.route('/registration-personal', methods=['GET', 'POST'])
def registration_personal():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        company_name = request.form['company_name']
        email = request.form['email']
        phone = request.form['phone']
        password1 = request.form['password1']
        password2 = request.form['password2']

        email_already_exists = db.session.query(db.exists().where(supplier_info.email == email)).scalar()
        if email_already_exists:
            flash('That email is already in use. Please use another email.', category='error')
            return render_template('registration_personal.html',
                                   user = current_user,
                                   first_name = first_name,
                                   last_name = last_name,
                                   company_name = company_name,
                                   email = email,
                                   phone = phone
                                   )

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


@views.route('/registration-location', methods=['GET', 'POST'])
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


@views.route('/registration-business', methods=['GET', 'POST'])
def registration_business():
    if request.method == "POST":
        legal_structure = request.form['legal_structure']
        session['legal_structure'] = legal_structure

        current_time = datetime.datetime.now().time()
        current_time_str = current_time.strftime('%H:%M:%S')
        s = URLSafeSerializer(os.getenv('secret_key'))

        radio_type = request.form['radio_type']
        if radio_type == 'individual':
            ssn = request.form['ssn']
            ssn_serialized = s.dumps([ssn, current_time_str])
            session['ssn'] = ssn_serialized
            logging.info('ssn_serialized: %s', ssn_serialized)

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
            db.session.add(new_supplier_info_record)
            db.session.commit()
            
            new_supplier_info_record_id = new_supplier_info_record.id

            new_supplier_login_record = supplier_login(supplier_id = new_supplier_info_record_id,
                                                    email = session['email'],
                                                    password = session['password']
                                                    )
            logging.info('new_supplier_info_record: %s', new_supplier_info_record)
            db.session.add(new_supplier_login_record)
            db.session.commit()

        if radio_type == 'company':
            ein = request.form['ein']
            if ein:
                ein_serialized = s.dumps([ein, current_time_str])
                session['ein'] = ein_serialized
                session['duns'] = ""
                logging.info('serialized_ein: %s', ein_serialized)
                logging.info('duns record is not applicable for this user')

            duns = request.form['duns']
            if duns:
                duns_serialized = s.dumps([duns, current_time_str])
                session['duns'] = duns_serialized
                session['ein'] = ""
                logging.info('serialized_duns: %s', duns_serialized)
                logging.info('ein record is not applicable for this user')


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
            logging.info('new_supplier_info_record: %s', new_supplier_info_record)
            db.session.add(new_supplier_info_record)
            db.session.commit()

            new_supplier_info_record_id = new_supplier_info_record.id

            new_supplier_login_record = supplier_login(supplier_id = new_supplier_info_record_id,
                                                    email = session['email'],
                                                    password = session['password']
                                                    )
            db.session.add(new_supplier_login_record)
            db.session.commit()

        msg = Message('New Vendor Account Created',
                        sender = ("STAR", 'hello@stxresources.org'),
                        recipients = ['bharding80@gmail.com',
                                      'CCallanen@wbpconsult.com'  
                                    ]
                        )

        
        msg.html = render_template('new_vendor_account_email.html',
                                vendor_info = new_supplier_info_record
                                )

        mail.send(msg)

        flash('New supplier profile created! Please login using your email and password to \
              apply for open bids.', category='success')
        return redirect(url_for('views.index'))


    return render_template('registration_business.html',
                           user = current_user
                           )





@views.route('/admin-data-view')
def admin_data_view():
    return render_template('admin_data_view.html', user = current_user)




@views.route('/download-vendor-list')
def download_vendor_list():
    supplier_data = supplier_info.query.all()

    csv_output = StringIO()
    csv_writer = csv.writer(csv_output)

    inspector = inspect(db.engine)
    columns = [column['name'] for column in inspector.get_columns('supplier_info')]
    csv_writer.writerow(columns)

    for data in supplier_data:
        csv_writer.writerow([getattr(data, column) for column in columns])

    filename = 'supplier_info.csv'

    headers = {
        'Content-Disposition': 'attachment; filename=' + filename,
        'Content-Type': 'text/csv'
    }

    return Response(
        csv_output.getvalue(),
        mimetype='text/csv',
        headers=headers
    )






@views.route('/manage-project', methods=['GET', 'POST'])
@login_required
def manage_project():
    if request.method == 'POST':
        logging.info('ADMIN IS CREATING NEW BID')

        files = request.files.getlist('file[]')

        # Timestamp to be used in S3 filename:
        now = datetime.datetime.now()
        date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")
        secure_date_time_stamp = secure_filename(date_time_stamp)
        logging.info('SECURE DATETIME STAMP: %s', secure_date_time_stamp)

        user_id = current_user.id
        project_title = request.form['project_title']
        bid_type = request.form['bid_type']
        organization = request.form['organization']
        issue_date = request.form['issue_date']
        notes = request.form['notes']
        
        close_date = request.form['close_date']
        close_time_central = request.form['close_time']
        datetime_str = close_date + ' ' + close_time_central
        datetime_obj_central = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')

        central_timezone = pytz.timezone('US/Central')
        datetime_obj_central_localized = central_timezone.localize(datetime_obj_central)

        utc_timezone = pytz.timezone('UTC')
        datetime_obj_utc = datetime_obj_central_localized.astimezone(utc_timezone)

        # First, create a new project record. Get the project record ID, then
        # use that ID to create a 'project_meta' record for each file that was uploaded.
        new_project_record = {
            'title': project_title,
            'type': bid_type,
            'organization': organization,
            'issue_date': issue_date,
            'close_date': datetime_obj_utc,
            'notes': notes,
            'status': 'open'
        }

        with db.session() as db_session:
            new_project = bids(**new_project_record)
            db_session.add(new_project)
            db_session.commit()
            new_project_id = new_project.id
            logging.info('NEW PROJECT CREATED: %s', new_project_record)

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
        logging.info('COMPLETE BID LIST: %s', bid_list)

        for bid in bid_list:
            close_date_utc = bid.close_date
            close_date_central = utc_to_central(close_date_utc)
            bid.close_date = close_date_central

        return render_template('manage_project.html',
                            user = current_user,
                            bid_list = bid_list
                            )






@views.route('/view-bid-details/<int:bid_id>', methods=['GET', 'POST'])
def view_bid_details(bid_id):
    logging.info('LOADING THE VIEW-BID-DETAILS PAGE')

    bid_object = db.session.query(bids) \
                        .filter_by(id = bid_id) \
                        .first()
    if bid_object:
        close_date_utc = bid_object.close_date
        close_date_central = utc_to_central(close_date_utc)
        bid_object.close_date = close_date_central

    project_meta_records = db.session.query(project_meta) \
                                    .filter_by(bid_id = bid_object.id) \
                                    .all()

    logging.info('BID OBJECT: %s', bid_object)
    logging.info('PROJECT META RECORDS: %s', project_meta_records)

    if 'user_type' not in session or session.get('user_type') is None:
        logging.info('USER TYPE NOT IN SESSION')
        applied_status = 'not applied - undefined user type'
        applications_for_bid_and_supplier = []
        chat_history_records = []
        vendor_chat_list = []
        applications_for_bid = []

    elif session.get('user_type') == 'admin':
        applications_for_bid = db.session.query(applicant_docs) \
                                        .filter_by(bid_id = bid_object.id) \
                                        .all()

        for application in applications_for_bid:
            application_submitted_datetime_utc = application.date_time_stamp
            application_submitted_datetime_central = utc_to_central(application_submitted_datetime_utc)
            application.date_time_stamp = application_submitted_datetime_central

        applied_status = 'not applied - user type is admin'
        applications_for_bid_and_supplier = []
        chat_history_records = []

        distinct_supplier_ids = db.session.query(chat_history.supplier_id).distinct().all()
        supplier_ids = [supplier_id for supplier_id, in distinct_supplier_ids]
        supplier_info_data = db.session.query(supplier_info.id, supplier_info.company_name).\
                                                filter(supplier_info.id.in_(supplier_ids)).all()
        vendor_chat_list = {supplier_id: company_name for supplier_id, company_name in supplier_info_data}
        logging.info('VENDOR CHATS AVAILABLE FOR THIS BID: %s', vendor_chat_list)

    elif session.get('user_type') == 'supplier':
        logging.info('SUPPLIER ID: %s', current_user.supplier_id)
        applications_for_bid = []
        vendor_chat_list = []

        chat_history_records = chat_history.query \
            .filter_by(supplier_id=current_user.supplier_id, bid_id=bid_id) \
            .all()
        
        if not chat_history_records:
            chat_history_records = []
        else:
            for message in chat_history_records:
                chat_timestamp_utc = message.datetime_stamp
                chat_timestamp_central = utc_to_central(chat_timestamp_utc)
                message.datetime_stamp = chat_timestamp_central


        vendor_has_applied = db.session.query(applicant_docs) \
            .filter(and_(applicant_docs.bid_id == bid_id, applicant_docs.supplier_id == current_user.supplier_id)) \
            .first() is not None # returns true or false

        if vendor_has_applied:
            applied_status = 'applied'

            applications_for_bid_and_supplier = db.session.query(applicant_docs) \
                                .filter_by(bid_id = bid_object.id) \
                                .filter_by(supplier_id = current_user.supplier_id) \
                                .all()
        else:
            applied_status = 'not applied'
            applications_for_bid_and_supplier = []

    else:
        logging.info('WARNING: UNDEFINED USER TYPE')
        return 'Undefined user type. Please contact us so we can help resolve this error!'


    request_data = request.stream.read()

    logging.info('APPLIED STATUS: %s', applied_status)
    logging.info('APPLICATIONS FOR BID AND SUPPLIER: %s', applications_for_bid_and_supplier)
    logging.info('CHAT HISTORY RECORDS: %s', chat_history_records)

    return render_template('view_bid_details.html', 
                            user = current_user,
                            bid_object = bid_object,
                            project_meta_records = project_meta_records,
                            applications_for_bid = applications_for_bid,
                            applied_status = applied_status,
                            chat_history_records = chat_history_records,
                            applications_for_bid_and_supplier = applications_for_bid_and_supplier,
                            vendor_chat_list = vendor_chat_list)

    # RE-WROTE THE CODE BELOW FOR CLARITY. DELETE THESE COMMENTS ONCE YOU TEST THE CODE ABOVE.
    # applications_for_bid = db.session.query(applicant_docs) \
    #                                 .filter_by(bid_id = bid_object.id) \
    #                                 .all()

    # vendor_chat_list = []
    

    # logging.info('APPLICATIONS FOR THIS BID: %s', applications_for_bid)

    # for application in applications_for_bid:
    #     application_submitted_datetime_utc = application.date_time_stamp
    #     application_submitted_datetime_central = utc_to_central(application_submitted_datetime_utc)
    #     application.date_time_stamp = application_submitted_datetime_central


    # if 'user_type' in session:
    #     logging.info('SESSION USER_TYPE: %s', session['user_type'])

    #     if session['user_type'] is not None:
    #         logging.info('SESSION USER_TYPE IS NOT NONE')

    #         if session['user_type'] == 'supplier':
    #             try:
    #                 logging.info('SUPPLIER ID: %s', current_user.supplier_id)
    #             except:
    #                 logging.info('SUPPLIER ID: UNKNOWN')

    #             chat_history_records = chat_history.query \
    #                 .filter_by(supplier_id=current_user.supplier_id, bid_id=bid_id) \
    #                 .all()

    #             if chat_history_records:
    #                 for message in chat_history_records:
    #                     chat_timestamp_utc = message.datetime_stamp
    #                     chat_timestamp_central = utc_to_central(chat_timestamp_utc)
    #                     message.datetime_stamp = chat_timestamp_central
    #             else: # no chat history
    #                 chat_history_records = []

    #             has_applied = db.session.query(applicant_docs) \
    #                 .filter(and_(applicant_docs.bid_id == bid_id, applicant_docs.supplier_id == current_user.supplier_id)) \
    #                 .first() is not None # returns true or false

    #             if has_applied:
    #                 applied_status = 'applied'

    #                 applications_for_bid_and_supplier = db.session.query(applicant_docs) \
    #                                     .filter_by(bid_id = bid_object.id) \
    #                                     .filter_by(supplier_id = current_user.supplier_id) \
    #                                     .all()
                                
    #             else: # supplier has not applied
    #                 applied_status = 'not applied'
    #                 applications_for_bid_and_supplier = []

    #         else: # user is admin
    #             applied_status = 'not applied'
    #             applications_for_bid_and_supplier = []
    #             chat_history_records = []

    #             distinct_supplier_ids = db.session.query(chat_history.supplier_id).distinct().all()
    #             supplier_ids = [supplier_id for supplier_id, in distinct_supplier_ids]
    #             supplier_info_data = db.session.query(supplier_info.id, supplier_info.company_name).\
    #                 filter(supplier_info.id.in_(supplier_ids)).all()
    #             vendor_chat_list = {supplier_id: company_name for supplier_id, company_name in supplier_info_data}
    #             logging.info('VENDOR CHAT LIST: %s', vendor_chat_list)


    #     else: # user is not logged in
    #         applied_status = 'not applied'
    #         applications_for_bid_and_supplier = []
    #         chat_history_records = []

    # else: # user_type key not in session
    #     applied_status = 'not applied'
    #     applications_for_bid_and_supplier = []
    #     chat_history_records = []

    # request_data = request.stream.read()

    # logging.info('HAS THE VENDOR APPLIED TO THIS BID: %s', applied_status)
    # logging.info('APPLICATIONS FOR BID AND SUPPLIER: %s', applications_for_bid_and_supplier)
    # logging.info('CHAT HISTORY RECORDS: %s', chat_history_records)

    # return render_template('view_bid_details.html', 
    #                         user = current_user,
    #                         bid_object = bid_object,
    #                         project_meta_records = project_meta_records,
    #                         applications_for_bid = applications_for_bid,
    #                         applied_status = applied_status,
    #                         chat_history_records = chat_history_records,
    #                         applications_for_bid_and_supplier = applications_for_bid_and_supplier,
    #                         vendor_chat_list = vendor_chat_list)




@views.route('/post-chat-message', methods=['GET', 'POST'])
@login_required
def post_chat_message():
    message = request.form['message']
    bid_id = request.form['bid_id']
    now = datetime.datetime.utcnow()
    datetime_stamp = now.strftime("%Y-%m-%d %H:%M:%S")

    with db.session() as db_session:

        if session['user_type'] == 'supplier':
            author_type = 'vendor'
            supplier_id = current_user.supplier_id

        elif session['user_type'] == 'admin':
            author_type = 'admin'
            supplier_id = request.form['supplier_id']

            new_comment = chat_history(author_type = author_type, 
                                    datetime_stamp = datetime_stamp, 
                                    comment = message, 
                                    bid_id = bid_id,
                                    supplier_id = supplier_id
                                    )
            
            logging.info('new_comment: %s', new_comment)

            db.session.add(new_comment)
            db.session.commit()

            flash('New comment successfully added!', category='success')

            return redirect(url_for('views.view_application', 
                            bid_id = bid_id,
                            supplier_id = supplier_id
                            ))



        else:
            return 'Error: Session user_type not set'

        new_comment = chat_history(author_type = author_type, 
                                datetime_stamp = datetime_stamp, 
                                comment = message, 
                                bid_id = bid_id,
                                supplier_id = supplier_id
                                )
        
        logging.info('new_comment: %s', new_comment)

        db.session.add(new_comment)
        db.session.commit()

        flash('New comment successfully added!', category='success')

        return redirect(url_for('views.view_bid_details', 
                        bid_id = bid_id
                        ))





@views.route('/applications-summary-page', methods=['GET', 'POST'])
@login_required
def applications_summary_page():
    with db.session() as db_session:
        supplier_id = current_user.supplier_id

        bid_ids = [row.bid_id for row in applicant_docs.query.filter_by(supplier_id=supplier_id).all()]
    
        bid_list = bids.query.filter(bids.id.in_(bid_ids)).all() # list of bid objects

        for bid in bid_list:
            close_date_utc = bid.close_date
            close_date_central = utc_to_central(close_date_utc)
            bid.close_date = close_date_central

        logging.info('supplier_id: %s', supplier_id)
        logging.info('bid_ids: %s', bid_ids)
        logging.info('bid_list: %s', bid_list)

        return render_template('applications_summary_page.html',
                            bid_list = bid_list,
                            user = current_user
                            )



@views.route('/view-vendor-chats/<int:bid_id>/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
def view_vendor_chats(bid_id, supplier_id):
    chat_history_records = chat_history.query \
        .filter_by(supplier_id=supplier_id, bid_id=bid_id) \
        .all()

    central_tz = pytz.timezone('America/Chicago')  # Set the timezone to Central Time
    for message in chat_history_records:
        utc_datetime = message.datetime_stamp
        central_datetime = utc_datetime.replace(tzinfo=pytz.utc).astimezone(central_tz)
        message.datetime_stamp = central_datetime

    return render_template('view_vendor_chats.html', 
                            user = current_user,
                            chat_history_records = chat_history_records,
                            supplier_id = supplier_id,
                            bid_id = bid_id)



@views.route('/view-application/<int:bid_id>/<int:supplier_id>', methods=['GET', 'POST'])
@login_required
def view_application(bid_id, supplier_id):
    with db.session() as db_session:
        bid_object = db_session.query(bids) \
                            .filter_by(id = bid_id) \
                            .first()

        applications_for_bid_and_supplier = db_session.query(applicant_docs) \
                                        .filter_by(bid_id = bid_object.id) \
                                        .filter_by(supplier_id = supplier_id) \
                                        .all()

        chat_history_records = chat_history.query \
            .filter_by(supplier_id=supplier_id, bid_id=bid_id) \
            .all()

        central_tz = pytz.timezone('America/Chicago')  # Set the timezone to Central Time
        for message in chat_history_records:
            utc_datetime = message.datetime_stamp
            central_datetime = utc_datetime.replace(tzinfo=pytz.utc).astimezone(central_tz)
            message.datetime_stamp = central_datetime

        return render_template('view_application.html', 
                                user = current_user,
                                bid_object = bid_object,
                                applications_for_bid_and_supplier = applications_for_bid_and_supplier,
                                chat_history_records = chat_history_records,
                                supplier_id = supplier_id)




@views.route('/apply-for-bid', methods=['GET', 'POST'])
@login_required
def apply_for_bid():
    if request.method == 'POST':
        files = request.files.getlist('file[]')
        bid_id = request.form['bid_id']
        bid = bids.query.get(bid_id)
        close_date_utc = bid.close_date

        logging.info('VENDOR TRYING TO UPLOAD THESE FILES: %s', files)
        logging.info('BID ID: %s', bid_id)

        if 'user_type' in session:
            logging.info('SESSION USER_TYPE: %s', session['user_type'])
        else:
            logging.info('WARNING: USER TYPE NOT IN SESSION')
            return 'We seem to be having an issue confirming your user log in credentials. Please contact us if you continue having issues.'

        if current_user.supplier_id:
            supplier_id = current_user.supplier_id
            logging.info('SUPPLIER ID: %s', supplier_id)

        else: # user is logged in as admin
            flash('Please log in as a vendor to apply to this bid.', category='error')
            return redirect(url_for('views.view_bid_details', bid_id=bid_id))

        now = datetime.datetime.utcnow()

        logging.info('BID CLOSE DATE: %s', close_date_utc)
        logging.info('CURRENT DATETIME: %s', now)
        logging.info('SUPPLIER ID: %s', supplier_id)
        logging.info('BID OBJECT: %s', bid)

        if close_date_utc < now: # all times in UTC
            flash('The close date for this bid has passed. Please contact us if you have any questions.', category='error')
            return redirect(url_for('views.view_bid_details', bid_id=bid_id))

        date_time_stamp = now.strftime("%Y-%m-%d %H:%M:%S")      
        secure_date_time_stamp = secure_filename(date_time_stamp)

        s3 = boto3.client('s3', region_name='us-east-1',
                        aws_access_key_id=os.getenv('s3_access_key_id'),
                        aws_secret_access_key=os.getenv('s3_secret_access_key'))
        
        S3_BUCKET = 'star-uploads-bucket'
        logging.info('UPLOADING TO THIS S3 BUCKET: %s', S3_BUCKET)

        for file in files:
            s3_filename = f"{secure_date_time_stamp}_{secure_filename(file.filename)}"
            logging.info('S3_FILENAME: %s', s3_filename)

            s3.upload_fileobj(file, S3_BUCKET, s3_filename)

            new_applicant_record = {
                'filename': file.filename,
                'date_time_stamp': date_time_stamp,
                'supplier_id': supplier_id,
                'bid_id': bid_id
            }

            logging.info('NEW APPLICANT FILE AND BID DETAILS: %s', new_applicant_record)

            with db.session() as db_session:
                new_application = applicant_docs(**new_applicant_record)
                db_session.add(new_application)
                db_session.commit()
                logging.info('NEW DB RECORD CREATED')

        flash('Your application was successfully submitted! Feel free to log out. We will \
              contact you via email or phone with next steps. Scroll down to view your application documents.', \
                category='success')


        bid_object = db_session.query(bids) \
                            .filter_by(id = bid_id) \
                            .first()

        supplier_object = db_session.query(supplier_info) \
                                        .filter_by(id = supplier_id) \
                                        .first()

        logging.info('BID OBJECT: %s', bid_object)
        logging.info('SUPPLIER/VENDOR OBJECT: %s', supplier_object)


        admin_msg = Message('New Application Submitted',
                        sender = ("STAR", 'hello@stxresources.org'),
                        recipients = ['brandon@getsurmount.com'
                                    ]
                        )

        admin_msg.html = render_template('new_application_email.html',
                                bid_object = bid_object,
                                supplier_object = supplier_object
                                )

        mail.send(admin_msg)
        logging.info('SUCCESS EMAIL SENT TO ADMIN')


        msg_to_vendor = Message('Thank You For Applying',
                        sender = ("STAR", 'hello@stxresources.org'),
                        recipients = [supplier_object.email
                                    ]
                        )

        msg_to_vendor.html = render_template('new_app_email_to_vendor.html',
                                bid_object = bid_object,
                                supplier_object = supplier_object
                                )

        mail.send(msg_to_vendor)
        logging.info('SUCCESS EMAIL SENT TO VENDOR')

        logging.info('REDIRECTING BACK TO VIEW-BID-DETAILS PAGE')
        return redirect(url_for('views.view_bid_details', bid_id=bid_id))


    else: # user is trying to send a GET request
        logging.info('User trying to send a GET request to "apply-for-bid" view function.')
        return 'This URL only accepts POST requests. Please return to the STAR homepage.'


@views.route('/download-application-doc', methods = ['GET', 'POST'])
def download_application_doc():
    if request.method == 'POST':
        logging.info('DOWNLOADING APPLICATION DOCUMENT FROM S3')

        filename = request.form['filename']
        date_time_stamp = request.form['date_time_stamp']

        dt = parser.parse(date_time_stamp)
        ct_timezone = pytz.timezone('America/Chicago')
        ct_datetime = dt.astimezone(ct_timezone)
        utc_datetime = ct_datetime.astimezone(pytz.utc)
        utc_timestamp = utc_datetime.strftime('%Y-%m-%d %H:%M:%S')

        secure_date_time_stamp = secure_filename(utc_timestamp)

        s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"

        s3 = boto3.client('s3', region_name='us-east-1',
                        aws_access_key_id=os.getenv('s3_access_key_id'),
                        aws_secret_access_key=os.getenv('s3_secret_access_key'))
        
        logging.info('central_date_time_stamp: %s', date_time_stamp)
        logging.info('utc_date_time_stamp: %s', utc_timestamp)
        logging.info('s3_filename: %s', s3_filename)

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


@views.route('/delete-application-doc', methods = ['GET', 'POST'])
@login_required
def delete_application_doc():
    bid_id = request.form['bid_id']
    doc_id = request.form['doc_id']
    filename = request.form['filename']
    date_time_stamp = request.form['date_time_stamp']
    secure_date_time_stamp = secure_filename(date_time_stamp)
    supplier_id = current_user.supplier.id

    s3_filename = f"{secure_date_time_stamp}_{secure_filename(filename)}"
    logging.info('S3 FILENAME: %s', s3_filename)

    s3 = boto3.client('s3', region_name='us-east-1',
                    aws_access_key_id=os.getenv('s3_access_key_id'),
                    aws_secret_access_key=os.getenv('s3_secret_access_key'))

    S3_BUCKET = 'star-uploads-bucket'

    try:
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_filename)
        logging.info('S3 OBJECT DELETED: %s', s3_filename)
    except Exception as e:
        logging.error('FAILED TO DELETE S3 OBJECT: %s', s3_filename)
        logging.error(str(e))

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

        return redirect(url_for('views.view_bid_details',
                                bid_id = bid_object.id))



@views.route('/upload-doc', methods=['GET', 'POST'])
def upload_doc():
    if request.method == 'POST':
        bid_id = request.form['bid_id']
        files = request.files.getlist('file[]')
        now = datetime.datetime.utcnow()
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

        return redirect(url_for('views.view_bid_details',
                                bid_id = bid_id))






@views.route('/download-project', methods = ['GET', 'POST'])
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

        # headers = Headers()
        # headers.add('Content-Disposition', 'attachment', filename=download_filename)
        # response.headers['Content-Disposition'] = 'attachment; filename=' + download_filename

        headers = {
            'Content-Disposition': f'attachment; filename="{download_filename}"',
            'Content-Type': 'application/pdf'  # Specify the content type as PDF
        }


        return Response(BytesIO(response.content), headers=headers)










@views.route('/delete-doc', methods = ['GET', 'POST'])
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




@views.route('/delete-project', methods = ['GET', 'POST'])
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
            return redirect(url_for('views.manage_project', user = current_user))




@views.route("/vendor-settings", methods=['GET', 'POST'])
@login_required
def supplier_settings():
    if request.method == 'POST':
        # The name of the category you are updating.
        field_name = request.form['field_name']

        return render_template('update_supplier_settings.html', 
                               user = current_user, 
                               field_name = field_name)

    return render_template('supplier_settings.html', user = current_user)


@views.route("/update-vendor-settings/<string:field_name>", methods=['GET', 'POST'])
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




@views.route('/current-bids', methods=['GET', 'POST'])
def current_bids():
    open_bids_to_check = bids.query.filter(bids.status == 'open').all()
    logging.info('OPEN BIDS TO CHECK ON CLOSE DATE: %s', open_bids_to_check)

    current_datetime_utc = datetime.datetime.utcnow()
    logging.info('CURRENT DATETIME UTC: %s', current_datetime_utc)

    bids_to_update = []
    for bid in open_bids_to_check:
        logging.info('CHECKING THE CLOSE DATE ON THIS BID: %s', bid)
        logging.info('UTC CLOSE DATE FOR THIS ^ BID: %s', bid.close_date)
        if bid.close_date < current_datetime_utc: # close_date has passed
            bid.status = 'closed'
            bids_to_update.append(bid)
            logging.info('SUCCESSFULLY CLOSED BID: %s', bid)

    db.session.bulk_save_objects(bids_to_update)
    db.session.commit()

    open_bids = bids.query.filter(bids.status == 'open').all()
    logging.info('RESULTING OPEN BIDS: %s', open_bids)

    for bid in open_bids:
        close_date_utc = bid.close_date
        close_date_central = utc_to_central(close_date_utc)
        bid.close_date = close_date_central

    return render_template('current_bids.html',
                        open_bids = open_bids,
                        user = current_user
                        )





@views.route('/closed-bids', methods=['GET', 'POST'])
def closed_bids():
    closed_bids = bids.query.filter(bids.status == 'closed').all()

    for bid in closed_bids:
        close_date_utc = bid.close_date
        close_date_central = utc_to_central(close_date_utc)
        bid.close_date = close_date_central

    return render_template('closed_bids.html',
                           closed_bids = closed_bids,
                           user = current_user
                           )



@views.route('/awarded-bids', methods=['GET', 'POST'])
def awarded_bids():

    awarded_bids = bids.query.filter(bids.status == 'awarded').all()

    for bid in awarded_bids:
        close_date_utc = bid.close_date
        close_date_central = utc_to_central(close_date_utc)
        bid.close_date = close_date_central

    return render_template('awarded_bids.html',
                           awarded_bids = awarded_bids,
                           user = current_user
                           )









@views.route('/bid-details', methods=['GET', 'POST'])
def bid_details():
    return render_template('bid_details.html',
                           user = current_user
                           )





@views.route('/login-vendor', methods=['GET', 'POST'])
def login_vendor():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        logging.info('LOGGING IN THIS VENDOR EMAIL: %s', email)

        user = supplier_login.query.filter_by(email = email).first()

        if user:
            logging.info('USER TRYING TO LOG IN WITH THIS EMAIL: %s', email)

            if check_password_hash(user.password, password):
                login_user(user, remember = True)
                session['user_type'] = 'supplier'
                logging.info('suppler_id: %s', user.supplier_id)
                session.permanent = True
                flash('Login successful!', category = 'success')
                logging.info('SUCCESSFULLY LOGGED IN VENDOR EMAIL: %s', email)
                logging.info('SESSION USER_TYPE: %s', session['user_type'])
                return redirect(url_for('views.index'))
            else:
                flash('Incorrect password. Please try again.', category = 'error')
                return render_template('login_vendor.html',
                                       email = email,
                                       user = current_user)
        else:
            flash('That email is not associated with an account.', category = 'error')

    return render_template('login_vendor.html',
                           user = current_user
                           )


@views.route("/reset_password_request/<string:user_type>", methods=['GET', 'POST'])
def reset_password_request(user_type):
    if request.method == "POST":
        email = request.form.get("email")
        
        if user_type == 'supplier':
            user = supplier_login.query.filter_by(email=email).first()
        else:
            user = admin_login.query.filter_by(email=email).first()


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




@views.route('/login-admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        logging.info('LOGGING IN THIS ADMIN EMAIL: %s', email)

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



@views.route('/admin-signup', methods=['GET', 'POST'])
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
    session['user_type'] = None
    flash('User successfully logged out', category='success')
    logout_user()

    return redirect(url_for('views.index'))


@views.route('/terms', methods=['GET', 'POST'])
def terms():
    return render_template('terms.html',
                           user = current_user
                           )


@views.route('/privacy-policy', methods=['GET', 'POST'])
def privacy():
    return render_template('privacy.html',
                           user = current_user
                           )