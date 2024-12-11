from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient(
    "mongodb+srv://deepakmuvvala:F2qCPJBBGk3l9McI@cluster.0uf8v.mongodb.net/?retryWrites=true&w=majority&appName=Cluster")
db = client["crud_db"]
users_collection = db["users"]
items_collection = db["items"]
user_filters_collection = db["user_filters"]  # Collection for storing filter settings

# Middleware to prevent caching of pages
@app.after_request
def add_cache_control_headers(response):
    # Prevent caching for sensitive pages (CRUD, update, admin)
    if request.endpoint in ['crud', 'update', 'admin']:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Redirect root URL to login
@app.route('/')
def home():
    return redirect(url_for('login'))

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if the user is already logged in
    if 'username' in session:
        return redirect(url_for('crud'))  # Redirect to CRUD page if logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the user exists and the password matches
        user = users_collection.find_one({'username': username, 'password': password})

        if user:
            session['username'] = username  # Store the username in the session
            # Load the saved filter settings
            saved_filter = user_filters_collection.find_one({'username': username})
            if saved_filter:
                session['filter_name'] = saved_filter.get('filter_name', '')
                session['filter_value'] = saved_filter.get('filter_value', '')
            return redirect(url_for('crud'))  # Redirect to CRUD page if logged in
        else:
            return render_template('login.html', error='Invalid credentials')  # Show error if invalid credentials

    return render_template('login.html')

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        if users_collection.find_one({'username': username}):
            return render_template('register.html', error='Username already taken')

        # Insert the new user into the database
        users_collection.insert_one({'username': username, 'password': password})
        return redirect(url_for('login'))  # Redirect to login page after registration

    return render_template('register.html')

# CRUD page route
@app.route('/crud', methods=['GET', 'POST'])
def crud():
    if 'username' in session:  # Check if user is logged in
        user = session['username']

        # If the user is admin, display all users
        if user == "admin":
            all_users = users_collection.find()  # Get all users from the database
            return render_template('admin.html', users=all_users)

        # Initialize filter variables
        filter_name = session.get('filter_name', '')
        filter_value = session.get('filter_value', '')

        # Check if filter form is submitted
        if request.method == 'POST':
            filter_name = request.form.get('filter_name', '')
            filter_value = request.form.get('filter_value', '')

            # Only save filter settings when 'Save Filter' button is clicked
            if 'save_filter' in request.form:
                # Save the filter settings to the database
                user_filters_collection.update_one(
                    {'username': user},
                    {'$set': {'filter_name': filter_name, 'filter_value': filter_value}},
                    upsert=True
                )

                # Update session with the new filter
                session['filter_name'] = filter_name
                session['filter_value'] = filter_value

            # Apply the filter, but do not save it
            # Build the filter query
            query = {'username': user}
            if filter_name:
                query['name'] = {'$regex': filter_name, '$options': 'i'}  # Case-insensitive search
            if filter_value:
                query['value'] = {'$regex': filter_value, '$options': 'i'}

            # Fetch items based on the filter query
            items = items_collection.find(query)

            return render_template('index.html', items=items, filter_name=filter_name, filter_value=filter_value)

        # If it's a GET request, just fetch the items using the saved filter
        query = {'username': user}
        if filter_name:
            query['name'] = {'$regex': filter_name, '$options': 'i'}  # Case-insensitive search
        if filter_value:
            query['value'] = {'$regex': filter_value, '$options': 'i'}

        items = items_collection.find(query)

        return render_template('index.html', items=items, filter_name=filter_name, filter_value=filter_value)

    else:
        return redirect(url_for('login'))  # Redirect to login page if not logged in

# Route to add a new item
@app.route('/add', methods=['POST'])
def add_item():
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    name = request.form['name']
    value = request.form['value']
    username = session['username']  # Associate the item with the logged-in user
    items_collection.insert_one({'name': name, 'value': value, 'username': username})
    return redirect(url_for('crud'))

# Route to update an existing item
@app.route('/update/<name>', methods=['GET', 'POST'])
def update_item(name):
    if 'username' not in session:  # Check if the user is logged in
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    username = session['username']
    item = items_collection.find_one({'name': name, 'username': username})

    if not item:
        return redirect(url_for('crud'))  # Redirect if the item does not belong to the user

    if request.method == 'POST':
        new_value = request.form['value']
        items_collection.update_one({'name': name, 'username': username}, {'$set': {'value': new_value}})
        return redirect(url_for('crud'))

    return render_template('update.html', item=item)

# Route to delete an item
@app.route('/delete/<name>')
def delete_item(name):
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login page if not logged in

    username = session['username']
    items_collection.delete_one({'name': name, 'username': username})
    return redirect(url_for('crud'))

# Route to delete a user (admin only)
@app.route('/delete_user/<username>')
def delete_user(username):
    if 'username' not in session or session['username'] != "admin":
        return redirect(url_for('login'))  # Only allow admin to delete users

    # Remove the user from the database
    users_collection.delete_one({'username': username})
    return redirect(url_for('crud'))  # Redirect back to the admin page

# Route to logout
@app.route('/logout')
def logout():
    session.pop('username', None)  # Removes the username from the session
    return redirect(url_for('login'))  # Redirect to login page

# Prevent back button cache issue after logout
@app.before_request
def before_request():
    if 'username' not in session:
        # If the user is not logged in, clear any previous session data
        session.clear()

    # If a user tries to access a page they shouldn't (crud, update, admin) after logout, redirect them to login
    if request.endpoint in ['crud', 'update', 'admin'] and 'username' not in session:
        return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
