from flask import Blueprint, render_template, request, redirect, flash, url_for, \
    session, send_file, jsonify, make_response, Response, send_from_directory, current_app
from flask_login import login_required, current_user, login_user
from sqlalchemy import and_, inspect
from project.models import (
    bids, admin_login, supplier_info,
    project_meta, supplier_login, applicant_docs, chat_history
)
from datetime import datetime
import pytz
from dateutil import parser
import datetime
from flask_mail import Message
from .. import db, mail
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
from project.config.star import Config

star = Blueprint('star', __name__)


# @star.route('/')
# def index():
#     return render_template(Config.CLIENT_NAME + '/index.html')