from flask import Flask, request, render_template, redirect, url_for, session
import hashlib
import mysql.connector
from io import BytesIO
from PIL import Image
import base64
import os, requests, uuid, json
import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key'

def get_db_connection():
    return mysql.connector.connect(
        host="sql12.freemysqlhosting.net",
        user="sql12614943",
        password="pWJDutLDC9",
        database="sql12614943"
    )

def translating(text):
    subscription_key = 'cd13ecbed41d4d3fbf44fcdd3190d381'
    region = 'centralindia'
    constructed_url = 'https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=auto&to=en'
    headers = {
        'Ocp-Apim-Subscription-Key': subscription_key,
        'Ocp-Apim-Subscription-Region': region,
        'Content-type': 'application/json',
        'X-ClientTraceId': str(uuid.uuid4())
    }
    language_url = 'https://api.cognitive.microsofttranslator.com/detect?api-version=3.0'
    language_headers = headers.copy()
    language_headers['Content-type'] = 'application/json'
    language_request = requests.post(language_url, headers=language_headers, json=[{'text': text}])
    language_response = language_request.json()
    detected_language = language_response[0]['language']
    body = [{
        'text': text
    }]
    constructed_url = constructed_url.replace('from=auto', f'from={detected_language}')
    request1 = requests.post(constructed_url, headers=headers, json=body)
    response = request1.json()
    translation = response[0]['translations'][0]['text']
    return translation

@app.route('/translate/<int:post_id>',methods = ['POST','GET'])
def translate(post_id):
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE Post SET translate = 1 WHERE post_id = %s',(post_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(request.referrer)
    else:
        return redirect(url_for('index'))

@app.route('/untranslate/<int:post_id>',methods = ['POST','GET'])
def untranslate(post_id):
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE Post SET translate = 0 WHERE post_id = %s',(post_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(request.referrer)
    else:
        return redirect(url_for('index'))
      
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # if (not request.form['email']) or (not request.form['username']) or (not request.form['password']):
        #     return redirect(url_for('register'))
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # biodata = request.form['biodata']
        cnpassword = request.form['confirm-password']
        if len(password) < 8:
            return render_template('register.html', error='Password should be at least 8 characters long.')

        if len(username) < 3:
            return render_template('register.html',error='Username should be at least 3 characters long.')
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        data = cursor.fetchone()
        if data is not None:
            return redirect(url_for('register'))
        else:
            # if password
            if cnpassword == password:
                pasw = password.encode()
                passw1 = hashlib.sha256(pasw).hexdigest()
                if request.form['biodata']:
                    biodata = request.form['biodata']
                    cursor.execute("INSERT INTO User ( email, biodata,username,password) VALUES (%s, %s, %s,%s)", (email, biodata,username,passw1))
                    conn.commit()
                    cursor.close()
                    conn.close()
                else:
                    cursor.execute("INSERT INTO User ( email,biodata,username,password) VALUES ( %s,'', %s,%s)", (email,username,passw1))
                    conn.commit()
                    cursor.close()
                    conn.close()
            else:
                return render_template('register.html')
            return redirect(url_for('register_success'))
    return render_template('register.html')

@app.route('/register_success')
def register_success():
    return render_template('login.html')


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['POST','GET'])
def login():
    if request.method=='GET':
        return render_template('login.html')
    username = request.form['username']
    password = request.form['password']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
    data = cursor.fetchone()
    if data is not None:
        db_password = data[5]
        pasw = password.encode()
        passw1 = hashlib.sha256(pasw).hexdigest()
        if  passw1 == db_password:
            session['username'] = username
            session['user_id'] = data[0]
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password.')
    else:
        return render_template('login.html', error='Invalid username.')


@app.route('/dashboard',methods = ['GET','POST'])
def dashboard():
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()
        user_id = user['user_id']
        cursor.execute('SELECT following_id FROM Following_list WHERE user_id=%s',(user_id,))
        follow = cursor.fetchall()
        posts=[]
        for i in range(len(follow)):
            cursor.execute('SELECT Post.post_Time, Post.post_text,Post.post_id,Post.upvotes,Post.downvotes,Post.post_photo,User.user_photo AS user_photo,User.username AS user_username,Post.translate FROM Post INNER JOIN User ON Post.user_id = User.user_id  WHERE User.user_id=%s ORDER BY Post.post_Time DESC',(follow[i]['following_id'],) )
            post = cursor.fetchall()
            posts =posts+post
        # for i  in range(len(posts)):
            # if posts[i].translate==1:
                # posts[i].post_text=translating(posts[i].post_text)
        posts.reverse()
        cursor.close()
        conn.close()
        return render_template('dashboard.html', user=user, posts=posts)
    else:
        return redirect(url_for('index'))

@app.route("/post/add",methods=['GET','POST'])
def add_post():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method =="POST":
        post_text = request.form['post_text']
        user_id = session['user_id']
        # post_time = datetime.datetime.now()
        post_tag = int(request.form['post_tag'])
        if request.files['image'] : 
            image = request.files["image"]
            img = Image.open(image)
            img_io = BytesIO()
            img.save(img_io, "JPEG")
            img_io.seek(0)
            encoded_img = base64.b64encode(img_io.getvalue())
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Post (post_text, post_Time,upvotes,downvotes,user_id,post_tag,post_photo) VALUES (%s, CURDATE(),0,0,%s,%s,%s)", ( post_text,user_id,post_tag,encoded_img))
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Post (post_text, post_Time,upvotes,downvotes,user_id,post_tag) VALUES (%s, CURDATE(),0,0,%s,%s)", ( post_text,user_id,post_tag))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cursor = conn.cursor()
    username = session['username']
    cursor.execute(" SELECT * FROM User WHERE username = %s",(username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('add_post.html',user = user)

@app.route('/logout')
def logout():
    # session.clear()'
    if 'username' in session:
        username = session['username']
        # username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        username = session['username']
        cursor.execute(" SELECT * FROM User WHERE username = %s",(username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('logout.html',user=user)
    else:
        return redirect(url_for('index'))

@app.route('/logout1')
def logout1():
    session.clear()
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()    
        user_id = user['user_id']
        cursor.execute('SELECT Post.post_Time,Post.post_text,Post.post_id,Post.upvotes,Post.downvotes,Post.post_photo, User.user_photo as user_photo,User.username AS user_username FROM Post INNER JOIN User ON Post.user_id=User.user_id WHERE Post.user_id=%s  ORDER BY Post.post_Time DESC',(user_id,))
        posts = cursor.fetchall()
        cursor.execute('SELECT * FROM Following_list WHERE user_id=%s',(user_id,))
        following = len(cursor.fetchall())
        cursor.execute('SELECT * FROM Follower_list WHERE user_id=%s',(user_id,))
        follower= len(cursor.fetchall())
        cursor.close()
        conn.close()
        return render_template('profile.html', user=user,posts=posts,following=following,follower=follower)
    else:
        return redirect(url_for('index'))
    
@app.route('/other_profile/<string:username>')
def other_profile(username):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()    
        user_id = user['user_id']
        cursor.execute('SELECT Post.post_Time,Post.post_text,Post.post_id,Post.upvotes,Post.downvotes,Post.post_photo, User.user_photo as user_photo,User.username AS user_username FROM Post INNER JOIN User ON Post.user_id=User.user_id WHERE Post.user_id=%s  ORDER BY Post.post_Time DESC',(user_id,))
        posts = cursor.fetchall()
        cursor.execute('SELECT * FROM Following_list WHERE user_id=%s',(user_id,))
        following = len(cursor.fetchall())
        cursor.execute('SELECT * FROM Follower_list WHERE user_id=%s',(user_id,))
        follower= len(cursor.fetchall())
        cursor.close()
        conn.close()
        main_username = session['username']
        if main_username==username:
            return redirect(url_for('profile'))
        return render_template('other_profile.html', user=user,posts=posts,following=following,follower=follower)
    else:
        return redirect(url_for('index'))
@app.route('/other_profile_follower/<string:username>',methods = ['GET','POST'])
def other_profile_follower(username):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()    
        user_id = user['user_id']
        cursor.execute('SELECT Follower_list.username,Follower_list.email,Follower_list.follower_photo ,Follower_list.follower_id FROM Follower_list INNER JOIN User ON Follower_list.user_id = User.user_id WHERE Follower_list.user_id = %s', (user_id,))
        posts = cursor.fetchall()
        for i in range(len(posts)):
            cursor.execute('SELECT biodata From User WHERE user_id = %s',(posts[i]['follower_id'],))
            follow = cursor.fetchone()
            posts[i]['biodata'] = follow['biodata']
        cursor.execute('SELECT * FROM Following_list WHERE user_id=%s',(user_id,))
        following = len(cursor.fetchall())
        cursor.execute('SELECT * FROM Follower_list WHERE user_id=%s',(user_id,))
        follower= len(cursor.fetchall())
        cursor.close()
        conn.close()
        main_username = session['username']
        if main_username==username:
            return redirect(url_for('profile_follower'))
        return render_template('other_profile_follower.html', user=user,posts=posts,following=following,follower=follower)
    else:
        return redirect(url_for('index'))

@app.route('/other_profile_following/<string:username>',methods = ['GET','POST'])
def other_profile_following(username):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()    
        user_id = user['user_id']
        cursor.execute('SELECT Following_list.username,Following_list.email,Following_list.following_photo,Following_list.following_id FROM Following_list INNER JOIN User ON Following_list.user_id = User.user_id WHERE Following_list.user_id = %s', (user_id,))
        posts = cursor.fetchall() 
        for i in range(len(posts)):
            cursor.execute('SELECT biodata From User WHERE user_id = %s',(posts[i]['following_id'],))
            follow = cursor.fetchone()
            posts[i]['biodata'] = follow['biodata']
        cursor.execute('SELECT * FROM Following_list WHERE user_id=%s',(user_id,))
        following = len(cursor.fetchall())
        cursor.execute('SELECT * FROM Follower_list WHERE user_id=%s',(user_id,))
        follower= len(cursor.fetchall())
        cursor.close()
        conn.close()
        main_username = session['username']
        if main_username==username:
            return redirect(url_for('profile_following'))
        return render_template('other_profile_following.html', user=user,posts=posts,following=following,follower=follower)
    else:
        return redirect(url_for('index'))

@app.route('/change_password', methods=['POST'])
def change_password():
    if request.method =='POST':
        if 'username' in session:
            username = session['username']
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
            data = cursor.fetchone()
            db_password = data[4]

            if current_password != db_password:
                return render_template('profile.html', error='Invalid password. Please try again.')

            if new_password != confirm_password:
                return render_template('profile.html', error='New password and confirm password do not match. Please try again.')

            cursor = conn.cursor()
            cursor.execute('UPDATE User SET password = %s WHERE username = %s', (new_password, username))
            conn.commit()
            cursor.close()
            conn.close()
            return render_template('change_password.html', success='Password updated successfully.')
        else:
            return redirect(url_for('index'))


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if request.method == 'POST':
        if 'username' in session:
            username = session['username']

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM User WHERE username = %s",(username,))
            user = cursor.fetchone()
            print(user)
            if request.form['email']:
                new_email = request.form['email']
                if len(new_email)>0:
                    cursor.execute('UPDATE User SET email = %s WHERE username = %s', (new_email,username))
            if  request.form['biodata']:
                new_biodata = request.form['biodata']
                if len(new_biodata)>0:
                    cursor.execute('UPDATE User SET biodata = %s WHERE username = %s', (new_biodata,username))
            if request.form['password']:
                new_password = request.form['password']
                if len(new_password)>0:
                    pasw = new_password.encode()
                    passw1 = hashlib.sha256(pasw).hexdigest()
                    cursor.execute('UPDATE User SET password = %s WHERE username = %s', (passw1,username))
            if request.files['image'] : 
                image = request.files['image']
                img = Image.open(image)
                img_io = BytesIO()
                img.save(img_io, "JPEG")
                img_io.seek(0)
                encoded_img = base64.b64encode(img_io.getvalue())
                cursor.execute("UPDATE User SET user_photo=%s WHERE username = %s", (encoded_img,username))
                cursor.execute("UPDATE Follower_list SET follower_photo =%s WHERE follower_id =%s",(encoded_img,user[0]))
                cursor.execute("UPDATE Following_list SET following_photo =%s WHERE following_id =%s",(encoded_img,user[0]))
            if  request.form['username']:
                new_username = request.form['username']
                if len(new_username)>0:
                    if len(new_username) < 3:
                        return redirect(url_for('settings', error='Username should be at least 3 characters long.'))
                    cursor.execute('UPDATE User SET username = %s WHERE username = %s', (new_username,username))
            conn.commit()
            cursor.close()
            conn.close()
            if  request.form['username']:
                new_username = request.form['username']
                if len(new_username)>0:
                    session['username'] = new_username
            return redirect(url_for('profile'))
        else:
            return redirect(url_for('index'))
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'username' not in session:
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    username = session['username']
    cursor.execute(" SELECT * FROM User WHERE username = %s",(username,))
    user = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return render_template('settings.html',user = user)

@app.route('/about', methods=['GET', 'POST'])
def about():
    if 'username' not in session:
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    username = session['username']
    cursor.execute(" SELECT * FROM User WHERE username = %s",(username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('about.html',user = user)

@app.route('/delete_account')
def delete_account():
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()
        user_id  = user[0]
        cursor.execute('DELETE FROM Follower_list WHERE user_id = %s', (user_id,))
        cursor.execute('DELETE FROM Follower_list WHERE follower_id = %s', (user_id,))
        cursor.execute('DELETE FROM Following_list WHERE user_id = %s', (user_id,))
        cursor.execute('DELETE FROM Following_list WHERE following_id = %s', (user_id,))
        cursor.execute('SELECT * FROM Post WHERE user_id = %s', (user_id,))
        posts = cursor.fetchall()
        print(user_id)
        for post in posts:
            post_id = post[0]
            print(post_id)
            cursor.execute('DELETE FROM Comment WHERE user_id = %s OR post_id=%s', (user_id,post_id))
            cursor.execute('DELETE FROM Upvote WHERE user_id =  %s OR post_id=%s', (user_id,post_id))
            cursor.execute('DELETE FROM Downvote WHERE user_id = %s OR post_id =%s', (user_id,post_id))
            cursor.execute('DELETE FROM Saved WHERE user_id = %s OR post_id = %s', (user_id,post_id))
        cursor.execute('DELETE FROM Post WHERE user_id = %s', (user_id,))
        cursor.execute('DELETE FROM User WHERE user_id = %s', (user_id,))
        conn.commit()
        cursor.close()
        conn.close()
        session.clear()
        return render_template('login.html')
    else:
        return redirect(url_for('index'))

@app.route('/saved/<int:user_id>',methods = ['GET','POST'])
def saved(user_id):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM User WHERE user_id =%s',(user_id,))
        user = cursor.fetchone()
        username = user[3]
        cursor.execute('SELECT * FROM Saved WHERE user_id= %s', (user_id,))
        posts = cursor.fetchall()
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('saved.html',user=user,posts = posts)
    else:
        return redirect(url_for('index'))
    
@app.route('/saved_post/<int:post_id>',methods = ['GET','POST'])
def saved_post(post_id):
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()
        user_id = user[0]
        cursor.execute('SELECT * FROM Post WHERE post_id = %s', (post_id,))
        post = cursor.fetchone()
        text = post[2]
        other_user = post[6]
        cursor.execute('SELECT * FROM User WHERE user_id = %s', (other_user,))
        other = cursor.fetchone()
        other_username = other[3]
        other_email = other[1]
        cursor.execute ('SELECT * FROM Saved WHERE user_id = %s AND post_id=%s',(user_id,post_id))
        data=cursor.fetchall()
        if len(data)==0:
            cursor.execute('INSERT INTO Saved (user_id,post_id,username,email,saved_photo,saved_user_photo,text) VALUES (%s,%s,%s,%s,%s,%s,%s)',(user_id,post_id,other_username,other_email,post[7],user[4],text))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(request.referrer)
    else:
        return redirect(url_for('index'))
        
@app.route('/profile_follower',methods = ['GET','POST'])
def profile_follower():
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()    
        user_id = user['user_id']
        cursor.execute('SELECT Follower_list.username,Follower_list.email,Follower_list.follower_photo,Follower_list.follower_id FROM Follower_list INNER JOIN User ON Follower_list.user_id = User.user_id WHERE Follower_list.user_id = %s', (user_id,))
        posts = cursor.fetchall() 
        for i in range(len(posts)):
            cursor.execute('SELECT biodata From User WHERE user_id = %s',(posts[i]['follower_id'],))
            follow = cursor.fetchone()
            posts[i]['biodata'] = follow['biodata']
        cursor.execute('SELECT * FROM Following_list WHERE user_id=%s',(user_id,))
        following = len(cursor.fetchall())
        cursor.execute('SELECT * FROM Follower_list WHERE user_id=%s',(user_id,))
        follower= len(cursor.fetchall())
        cursor.close()
        conn.close()
        return render_template('profile_follower.html', user=user,posts=posts,following=following,follower=follower)
    else:
        return redirect(url_for('index'))

@app.route('/profile_following',methods = ['GET','POST'])
def profile_following():
    if 'username' in session:
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
        user = cursor.fetchone()    
        user_id = user['user_id']
        cursor.execute('SELECT Following_list.username,Following_list.email,Following_list.following_photo,Following_list.following_id FROM Following_list INNER JOIN User ON Following_list.user_id = User.user_id WHERE Following_list.user_id = %s', (user_id,))
        posts = cursor.fetchall()
        for i in range(len(posts)):
            cursor.execute('SELECT biodata From User WHERE user_id = %s',(posts[i]['following_id'],))
            follow = cursor.fetchone()
            posts[i]['biodata'] = follow['biodata']
        cursor.execute('SELECT * FROM Following_list WHERE user_id=%s',(user_id,))
        following = len(cursor.fetchall())
        cursor.execute('SELECT * FROM Follower_list WHERE user_id=%s',(user_id,))
        follower= len(cursor.fetchall())
        cursor.close()
        conn.close()
        return render_template('profile_following.html', user=user,posts=posts,following=following,follower=follower)
    else:
        return redirect(url_for('index'))

    
@app.route('/following/<int:post_id>',methods = ['GET','POST'])
def following(post_id):
    if 'username' in session:
            conn = get_db_connection()
            cursor = conn.cursor() 
            main_username = session['username']
            cursor.execute('SELECT * FROM User WHERE username = %s', (main_username,))
            main_user = cursor.fetchone()
            main_user_id =  main_user[0]
            cursor.execute('SELECT * FROM Post WHERE post_id = %s', (post_id,)) 
            post= cursor.fetchone()
            cursor.execute('SELECT * FROM User WHERE user_id = %s', (post[6],)) 
            user= cursor.fetchone()
            user_id = user[0]
            name_of_user = user[3]
            email = user[1]
            username_user = main_user[3]
            email_user = main_user[1]
            cursor.execute('SELECT * FROM Following_list WHERE following_id=%s AND user_id = %s',(user_id,main_user_id))
            data = cursor.fetchall()
            
            if len(data)==0 and main_user_id!=user_id:
                    cursor.execute('INSERT INTO Following_list (user_id,following_id,username,email,following_photo) VALUES (%s,%s,%s,%s,%s)',(main_user_id,user_id,name_of_user,email,user[4]))
                    cursor.execute('INSERT INTO Follower_list (user_id,follower_id,username,email,follower_photo) VALUES (%s,%s,%s,%s,%s)',(user_id,main_user_id,username_user,email_user,main_user[4]))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(request.referrer)
    else:
        return redirect(url_for('index'))


@app.route('/following_other/<int:user_id>',methods = ['GET','POST'])
def following_other(user_id):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor() 
        main_username = session['username']
        cursor.execute('SELECT * FROM User WHERE username = %s', (main_username,))
        main_user = cursor.fetchone()
        main_user_id =  main_user[0]
        cursor.execute('SELECT * FROM User WHERE user_id = %s', (user_id,)) 
        user= cursor.fetchone()
        name_of_user = user[3]
        email = user[1]
        username_user = main_user[3]
        email_user = main_user[1]
        cursor.execute('SELECT * FROM Following_list WHERE following_id=%s AND user_id = %s',(user_id,main_user_id))
        data = cursor.fetchall()
        if len(data)==0 and main_user_id!=user_id:
            cursor.execute('INSERT INTO Following_list (user_id,following_id,username,email,following_photo) VALUES (%s,%s,%s,%s,%s)',(main_user_id,user_id,name_of_user,email,user[4]))
            cursor.execute('INSERT INTO Follower_list (user_id,follower_id,username,email,follower_photo) VALUES (%s,%s,%s,%s,%s)',(user_id,main_user_id,username_user,email_user,main_user[4]))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(request.referrer)
    else:
        return redirect(url_for('index'))
    
@app.route('/explore/<int:post_tag>',methods = ['POST','GET'])
def explore_tag(post_tag):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT Post.post_Time,Post.post_text,Post.post_id,Post.upvotes,Post.downvotes,Post.post_photo,User.user_photo AS user_photo, User.username AS user_username,Post.translate FROM Post INNER JOIN User ON Post.user_id=User.user_id WHERE Post.post_tag = %s ORDER BY Post.post_Time ASC',(post_tag,))
        posts = cursor.fetchall()
        for i  in range(len(posts)):
            posts[i] = list(posts[i])
            if posts[i][8]==1:
                posts[i][1]=translating(posts[i][1])
            posts[i]=tuple(posts[i])
        posts.reverse()
        cursor.execute('SELECT * FROM User WHERE username =%s',(session['username'],))
        user=cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return(render_template('explore_tag.html',posts = posts,user=user,post_tag = post_tag))
    else:
        return redirect(url_for('login'))

@app.route('/explore',methods = ['POST','GET'])
def explore():
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT Post.post_Time,Post.post_text,Post.post_id,Post.upvotes,Post.downvotes,Post.post_photo,User.user_photo AS user_photo, User.username AS user_username,Post.translate FROM Post INNER JOIN User ON Post.user_id=User.user_id ORDER BY Post.post_Time ASC')
        posts = cursor.fetchall()
        for i  in range(len(posts)):
            posts[i] = list(posts[i])
            if posts[i][8]==1:
                posts[i][1]=translating(posts[i][1])
            posts[i]=tuple(posts[i])
        posts.reverse()
        cursor.execute('SELECT * FROM User WHERE username =%s',(session['username'],))
        user=cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return(render_template('explore.html',posts = posts,user=user))
    else:
        return redirect(url_for('login'))
    
@app.route('/comment/<int:post_id>',methods = ['POST','GET'])
def view_comments(post_id):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT Comment.comment_id, Comment.comment_text, Comment.comment_Time, User.username AS username,User.user_photo AS user_photo FROM Comment INNER JOIN User ON Comment.user_id=User.user_id WHERE post_id = %s ORDER BY comment_Time DESC', (post_id,))
        comments = cursor.fetchall()
        username=session['username']
        cursor.execute('SELECT * From Post WHERE post_id = %s',(post_id,))
        post = cursor.fetchone()
        cursor.execute('SELECT * FROM User WHERE username = %s', (username,)) 
        user = cursor.fetchone()   
        cursor.execute('SELECT * FROM User WHERE user_id = %s', (post['user_id'],)) 
        other_user = cursor.fetchone()           
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('comment.html', comments=comments,post_id = post_id,post=post,user=user,other_user=other_user)
    else:
        return redirect(url_for('index'))

@app.route('/post/<int:post_id>/comments/add', methods=['POST'])
def add_comment(post_id):
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        comment_text = request.form['comment_text']
        username = session['username']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM User where username = %s',(username,))
        user = cursor.fetchone()
        user_id = user[0]
        cursor.execute("INSERT INTO Comment (comment_text, comment_Time, user_id, post_id) VALUES (%s, NOW(), %s, %s)", (comment_text, user_id, post_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('view_comments', post_id=post_id))

@app.route('/comment/<int:post_id>',methods = ['GET','POST'])
def comment(post_id):
    if 'username' in session:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM User where username = %s',(session['username'],))
        user = cursor.fetchone()
        cursor.execute('SELECT * FROM Post where post_id = %s',(post_id,))
        post = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('comment.html',post = post,user=user)
    else:
        return redirect(url_for('index'))


@app.route('/upvote_post/<int:post_id>',methods = ['POST','GET'])
def upvote_post(post_id):
    if request.method=='POST':
        if 'username' in session:
            username = session['username']
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT user_id FROM User WHERE username = %s', (username,))
            user = cursor.fetchone()
            user_id = user['user_id']
            cursor.execute('SELECT * FROM Upvote WHERE post_id = %s AND user_id = %s',(post_id,user_id))
            data1 = cursor.fetchall() 
            cursor.execute('SELECT * FROM Downvote WHERE post_id = %s AND user_id = %s',(post_id,user_id))
            data2 = cursor.fetchall() 
            if(len(data1)==0 and len(data2)==0):
                cursor.execute('INSERT INTO Upvote (post_id, user_id) VALUES (%s, %s)', (post_id, user_id))            
                cursor.execute('UPDATE Post SET upvotes = upvotes+1 WHERE post_id = %s', (post_id,))
                conn.commit()
                cursor.close()
                conn.close()    
            elif(len(data2)==0):
                conn.commit()
                cursor.close()
                conn.close()  
            else:  
                cursor.execute('INSERT INTO Upvote (post_id, user_id) VALUES (%s, %s)', (post_id, user_id))            
                cursor.execute('UPDATE Post SET upvotes = upvotes+1 WHERE post_id = %s', (post_id,))
                cursor.execute('DELETE FROM Downvote WHERE post_id = %s AND user_id = %s',(post_id,user_id))
                cursor.execute('UPDATE Post SET downvotes = downvotes-1 WHERE post_id = %s', (post_id,))
                conn.commit()
                cursor.close()
                conn.close()    
            return redirect(request.referrer)
                
        else:
            return redirect(url_for('index'))

@app.route('/downvote_post/<int:post_id>',methods = ['POST','GET'])
def downvote_post(post_id):
    if request.method=='POST':
        if 'username' in session:
            username = session['username']
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute('SELECT user_id FROM User WHERE username = %s', (username,))
            user = cursor.fetchone()
            user_id = user['user_id']
            cursor.execute('SELECT * FROM Upvote WHERE post_id = %s AND user_id = %s',(post_id,user_id))
            data1 = cursor.fetchall() 
            cursor.execute('SELECT * FROM Downvote WHERE post_id = %s AND user_id = %s',(post_id,user_id))
            data2 = cursor.fetchall() 
            if(len(data1)==0 and len(data2)==0):
                cursor.execute('INSERT INTO Downvote (post_id, user_id) VALUES (%s, %s)', (post_id, user_id))            
                cursor.execute('UPDATE Post SET downvotes = downvotes+1 WHERE post_id = %s', (post_id,))
                conn.commit()
                cursor.close()
                conn.close()    
            elif(len(data1)==0):
                conn.commit()
                cursor.close()
                conn.close()  
            else:  
                cursor.execute('INSERT INTO Downvote (post_id, user_id) VALUES (%s, %s)', (post_id, user_id))            
                cursor.execute('UPDATE Post SET downvotes = downvotes+1 WHERE post_id = %s', (post_id,))
                cursor.execute('DELETE FROM Upvote WHERE post_id = %s AND user_id = %s',(post_id,user_id))
                cursor.execute('UPDATE Post SET upvotes = upvotes-1 WHERE post_id = %s', (post_id,))
                conn.commit()
                cursor.close()
                conn.close()    
            return redirect(request.referrer)
                
        else:
            return redirect(url_for('index'))
@app.route('/messages')
def messages():
    if 'username' in session:
        return render_template('messages.html')
    else:
        return redirect(url_for('index'))
    
@app.route('/search', methods=['POST','GET'])
def search_user():
    if request.method=='POST':
        search_user = request.form['sea']
        if not search_user:
            return redirect(url_for('dashboard'))
        conn = get_db_connection()
        cursor = conn.cursor()
        username = session['username']
        cursor.execute("SELECT * FROM User WHERE username LIKE CONCAT('%', %s, '%')",(search_user,) )
        posts= cursor.fetchall()
        cursor.execute("SELECT * FROM User WHERE email LIKE CONCAT('%', %s, '%')",(search_user,) )
        posts=posts+cursor.fetchall()
        cursor.execute('SELECT * FROM User WHERE username = %s',(username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('search.html',posts =posts,user=user)
    else:
        return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)