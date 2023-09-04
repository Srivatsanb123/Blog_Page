from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from pymongo import MongoClient,TEXT
from datetime import datetime
from bson import ObjectId
from os import environ

app = Flask(__name__)
bcrypt = Bcrypt(app)

app.secret_key = '1234'

username = environ.get('mongouser')
password = environ.get('mongopass')
conn_string = 'mongodb+srv://'+username+':'+password+'@cluster0.2viq6cu.mongodb.net/'
client = MongoClient(conn_string)
db = client.flask_db
posts = db.posts
users = db.users
comments = db.comments
posts.create_index([("title", TEXT), ("content", TEXT)], default_language='english')

@app.route('/')
def index():
    all_posts = posts.find()
    return render_template('index.html', posts=all_posts)

@app.route('/create', methods=['GET', 'POST'])
def create():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        new_post = {
            'title': title,
            'content': content,
            'timestamp': datetime.now()
        }
        posts.insert_one(new_post)
        return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        if password == confirm_password:
            user = users.find_one({'username': username})
            if user:
                flash('Your username is already registered! Please login to continue.', category='success')
                return redirect(url_for('login'))
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            users.insert_one({'username': username, 'password': hashed_password})
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match! Please try again.', category='error')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users.find_one({'username': username})
        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            return redirect(url_for('index'))
        else:
            flash('Invalid Username or Password! Please try again...', category='error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/comment/<post_id>', methods=['POST'])
def comment(post_id):
    if 'user_id' in session:
        user_id = session['user_id']
        user = users.find_one({'_id': ObjectId(user_id)})
        comment_text = request.form.get('comment_text')
        comment = {
            'user': user['username'],
            'post_id': post_id,
            'text': comment_text,
            'timestamp': datetime.now()
        }
        comments.insert_one(comment)
    return redirect(url_for('show_post', post_id=post_id))

@app.route('/post/<post_id>')
def show_post(post_id):
    if 'user_id' not in session:
        flash('Login to view the blog', category='error')
        return redirect(url_for('login'))
    post = posts.find_one({"_id": ObjectId(post_id)})
    post_comments = comments.find({"post_id": post_id})
    return render_template('post.html', post=post, comments=post_comments)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search_query')
        search_results = posts.find({
            "$or": [
                {"title": {"$regex": search_query, "$options": "i"}},
                {"content": {"$regex": search_query, "$options": "i"}}
            ]
        })
        return render_template('search_results.html', results=search_results, query=search_query)

@app.errorhandler(Exception)
def handle_error(error):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
