import functools, logging, os, json
from flask import(
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, Markup, send_from_directory
)

from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from semnas.db import get_db, get_collection, get_user, get_users, insert_user, update_user
from . import utils
from bson.objectid import ObjectId

bp = Blueprint('user', __name__, url_prefix='/')

@bp.route('/admin_home')
def admin_home():
    name = g.user['name']    
    filter = {}
    filter['type'] = {'$exists': 0}
    doc = get_users(filter)
    count = doc.count()

    #query all users
    return render_template('admin_home.html', name = name, nuser = count, users = doc)

@bp.route('/create_admin/<email>/<passw>')
def create_admin(email, passw):
    #email = "semnasmath@unj.ac.id"
    data = {"email": email,
                "password": generate_password_hash(passw), 
                "name" : "Admin", 
                "type" : "master",                 
                }
    row = insert_user(data)
    flash("Admin " + email + " is created successfully") 
    return render_template('user_success.html')

@bp.route('/update_password/<email>/<passw>')
def update_password(email, passw):
    data = {
            "password": generate_password_hash(passw), 
            }

    # result = update_user({'_id': ObjectId(user_id)}, {'$set': data})
    result = update_user({'email': email}, {'$set': data})  
    flash("User " + email + " password has been updated")
    return render_template('user_success.html')



