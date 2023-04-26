from flask import Blueprint, render_template, request, redirect, flash, url_for, \
    session, send_file, jsonify, make_response, Response, send_from_directory
# from flask_login import login_required, current_user, login_user
from project.models import bids, bid_contact, gov_login, supplier_info, supplier_login
# from flask_mail import Message
from . import db, mail
# from helpers import generate_sitemap
# from werkzeug.security import generate_password_hash, check_password_hash
# from itsdangerous.exc import BadSignature
# import os

views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@views.route('/contact', methods=['GET', 'POST'])
def contact():
    return render_template('contact.html')


@views.route('/registration', methods=['GET', 'POST'])
def registration():
    return render_template('registration.html')


@views.route('/current_bids', methods=['GET', 'POST'])
def current_bids():
    with db.session() as db_session:
        current_bids = db_session.query(bids) \
            .filter(bids.status == 'open') \
            .order_by(bids.issue_date.desc()) \
            .all()
      
    return render_template('current_bids.html',
                            current_bids = current_bids
                            )

@views.route('/closed_bids', methods=['GET', 'POST'])
def closed_bids():
    return render_template('closed_bids.html')

@views.route('/awarded_bids', methods=['GET', 'POST'])
def awarded_bids():
    return render_template('awarded_bids.html')

@views.route('/bid_details', methods=['GET', 'POST'])
def bid_details():
    return render_template('bid_details.html')

@views.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


@views.route('/terms', methods=['GET', 'POST'])
def terms():
    return render_template('terms.html')


@views.route('/privacy_policy', methods=['GET', 'POST'])
def privacy():
    return render_template('privacy.html')