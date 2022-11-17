import functools, logging, os, json
from flask import(
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, Markup, send_from_directory
)

from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from semnas.db import get_db, get_users, get_user, insert_user, update_user, delete_user, get_bill_category
from . import utils
from bson.objectid import ObjectId

bp = Blueprint('submit', __name__, url_prefix='/')

@bp.before_app_request
def load_logged_in_user():
    user = session.get('user')    
    
    if user is None:
        g.user = None
    else:
        user_id = user.get('id')
        #collection = get_collection('user')
        #doc = collection.find_one({"_id" : ObjectId(user_id)})
        doc = get_user({"_id" : ObjectId(user_id)})
        g.user = doc
        current_app.logger.debug("g.user: " + str(g.user))
        
def signin_check(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is not None:
            return redirect(url_for('submit.profile'))
        return view(**kwargs)
    return wrapped_view

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('submit.login'))
        return view(**kwargs)
    return wrapped_view

@bp.route('/login', methods=['GET'])
@signin_check
def login():
    return render_template('login.html')

@bp.route('/login', methods=['POST'])
def login_submit():
    email = request.form['email']
    passw = request.form['pass']

    errors = []
    data = {"email": email,
            #"password": generate_password_hash(passw)
            }            

    doc = get_user(data)  
    current_app.logger.debug("seek result: " + str(doc))
    passw_hash = generate_password_hash(passw)
    current_app.logger.debug("pass hash: " + passw_hash)
    if not doc:
        errors.append("Incorrect username")
        
    elif not check_password_hash(doc.get('password'), passw):
        errors.append("Incorrect password")

    if not errors:                                            
        #register session
        session.clear()
        session['user'] = {"id" : str(doc.get('_id'))}
        flash("You have been signed in successfully")
        if(doc.get('type') == "master"):
            return redirect(url_for('user.admin_home'))
        return redirect(url_for('submit.profile'))        

    return render_template('login.html', error=errors)

@bp.route('/regconf', methods=['GET'])
def form_register():
    return render_template('register.html')

@bp.route('/regconf', methods=['POST'])
def register():    
    email = request.form['email']
    name = request.form['name']
    institution = request.form['institution']
    telephone = request.form['telephone']
    profession = request.form['profession']
    #TODO: get id_card request
    
    errors = []
    #for now error handling is done on server    
    if not email:
        errors.append('E-mail is required.')        

    #db = get_db()
    #collection = get_collection('user')
    doc = get_user({"email" : email})       

    if doc is not None:            
        errors.append('email is existed, please entry a different one!')            
        return render_template('register.html', error=errors)
    
    #current_app.logger.debug(request.form);
    #current_app.logger.debug(request.files);        

    if not name:
        errors.append('Name is required.')
    if not institution:
        errors.append('Institution is required')
    if not telephone:
        errors.append('Phone is required')        
    if 'id_card' not in request.files:
        errors.append('please choose a file!')                
    
    if not errors :  
        #generate password      
        password = utils.generate_passphrase(current_app.config['PASS_LENGTH'])
        
        data = {"email": email, 
                "password": generate_password_hash(password), 
                "name" : name, 
                "institution" : institution, 
                "telephone" : telephone, 
                "profession": profession
                }
        #this instruction bsonify data 
        #row = collection.insert_one(data)
        row = insert_user(data)
        #remove _id from data
        data.pop('_id')
        #next save the file
        file = request.files['id_card']  
        
        try: 
            if file and utils.allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filename = utils.pad_timestamp(filename)
                path = os.path.join(current_app.instance_path, current_app.config['UPLOAD_DIR'])
                try:
                    os.makedirs(path)
                except OSError:
                    pass
                filepath = os.path.join(path, filename)
                file.save(filepath)
                current_app.logger.debug(filepath);
                #update the record here
                #collection.update_one({'_id': row.inserted_id}, {'$set': {'filename': filename}})
                update_user({'_id': row.inserted_id}, {'$set': {'filename': filename}})

                #set session
                session.clear()
                session['user'] = {"id": str(row.inserted_id)}                        
                current_app.logger.debug("session post: " + str(session['user']))
                
                warn_message = Markup("<span class='text-danger'>One time only</span>")            
                flash("Registration is completed successfully")            
                flash("Your generated password is: " + password + " (" + warn_message + ")")
                flash("Please record it for later sign in to change personal information if necessary")            
                return redirect(url_for('submit.regconf_success'))
        except:                
            #as there are no rollback mechanism in mongodb, we need to failover manually
            session.clear()
            errors.append("File must be in PDF, JPG, or PNG")
            #collection.delete_one({"_id": row.inserted_id})
            delete_user({"_id": row.inserted_id})

    return render_template('register.html',error=errors)

@bp.route('/regconf_success')
@login_required
def regconf_success():
    #should create session based on user     
    type = g.user['profession']    
    #use switch case here
    switcher = {"Umum": "non_pemakalah_umum",
                "Guru": "non_pemakalah_guru",
                "Mahasiswa": "non_pemakalah_mhs"
                }
    cat = switcher[type]
    current_app.logger.debug("Cat: " + cat)
    #collection = get_collection('bill')    
    #row = collection.find_one({"type" : cat})    
    row = get_bill_category({"type" : cat})    
    cost = utils.number_to_currency(row['cost'])
    current_app.logger.debug("type: " + type)
    current_app.logger.debug("cost: " + cost)
    return render_template('register_success.html', type=type, cost=cost)

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@bp.route('/profile')
@login_required
def profile():
    #load user data    
    email = g.user.get('email')
    name = g.user.get('name')
    institution = g.user.get('institution')
    phone = g.user.get('telephone')
    profession = g.user.get('profession')    
    filename = g.user.get('filename')        
    return render_template('view_profile.html', email=email, name=name, institution=institution, phone=phone, profession=profession, filename=filename)

@bp.route('/download/<filename>')
def download(filename):
    path = os.path.join(current_app.instance_path, current_app.config['UPLOAD_DIR'])
    return send_from_directory(path, filename, as_attachment=True)

@bp.route('regconf_edit', methods=['GET'])
def regconf_edit():
    email = g.user.get('email')
    name = g.user.get('name')
    institution = g.user.get('institution')
    phone = g.user.get('telephone')
    profession = g.user.get('profession')    
    filename = g.user.get('filename')        
    return render_template('edit_profile.html', email=email, name=name, institution=institution, phone=phone, profession=profession, filename=filename)

@bp.route('regconf_edit', methods=['POST'])
def regconf_edit_submit():    
    email = g.user.get('email')
    name = request.form['name']
    institution = request.form['institution']
    telephone = request.form['telephone']
    profession = request.form['profession']
    filename = g.user.get('filename')   
    
    errors = []       

    #db = get_db()    
    user_id = session.get('user').get('id')        
    #collection = get_collection('user')
    #doc = collection.find_one({"_id" : ObjectId(user_id)})       
    doc = get_user({"_id" : ObjectId(user_id)})

    if not name:
        errors.append('Name is required.')
    if not institution:
        errors.append('Institution is required')
    if not telephone:
        errors.append('Phone is required')        
    if 'id_card' not in request.files:
        errors.append('please choose a file!')                
    
    if not errors :                  
        data = {                
                "name" : name, 
                "institution" : institution, 
                "telephone" : telephone, 
                "profession": profession
                }
        
        #this instruction bsonify data 
        #get current id
        #result = collection.update_one({'_id': ObjectId(user_id)}, {'$set': data})
        result = update_user({'_id': ObjectId(user_id)}, {'$set': data})
                
        #next save the file
        file = request.files['id_card']  
        
        if file and utils.allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = utils.pad_timestamp(filename)
            path = os.path.join(current_app.instance_path, current_app.config['UPLOAD_DIR'])
            try:
                os.makedirs(path)
            except OSError:
                pass
            filepath = os.path.join(path, filename)
            file.save(filepath)
            current_app.logger.debug(filepath);
            #update the record here
            #collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'filename': filename}})            
            update_user({'_id': ObjectId(user_id)}, {'$set': {'filename': filename}})
            flash("Profile is Updated successfully")               
            return redirect(url_for('submit.profile'))
                
        #as there is no rollback mechanism in mongodb, we need to failover manually
        errors.append("File must be in PDF, JPG, or PNG")        

    return render_template('edit_profile.html', email=email, name=name, institution=institution, phone=telephone, profession=profession, filename=filename, error=errors)
