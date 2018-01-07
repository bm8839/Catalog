from flask import (Flask,
                   render_template,
                   request,
                   redirect,
                   jsonify,
                   url_for,
                   flash)
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from catalogdb_setup import Base, User, Category, Item
from flask import make_response
from flask import session as login_session
from functools import wraps
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import random
import string
import requests

app = Flask(__name__)


CLIENT_ID = json.loads(open('/var/www/Catalog/catalog/client_secrets.json', 'r').
                       read())['web']['client_id']
APPLICATION_NAME = "Catalog App"


# Connect to Database and create database session.
engine = create_engine('postgresql://catalog:catalog@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
    """Creates a state token to prevent request forgery. Stores it in the
    session for later validation. Then sends the state token to the sign-in
    functions on the login.html page for either Google or Facebook to use.
    """
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# User helper functions
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Login using Facebook
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    """If user chose to use their Facebook login credentials, this function
    logs the user into the application.
    """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    app_id = json.loads(open('/var/www/Catalog/catalog/fb_client_secrets.json', 'r').read())[
             'web']['app_id']
    app_secret = json.loads(
        open('/var/www/Catalog/catalog/fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?' + \
          'grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.10/me"
    '''Due to the formatting for the result from the server token exchange we
    have to split the token first on commas and select the first index which
    gives us the key : value for the server access token then we split it on
    colons to pull out the actual token value and replace the remaining quotes
    with nothing so that it can be used directly in the graph api calls.
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.10/me?' + \
          'access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.10/me/picture?' + \
          'access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists and if not then create the user
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;' + \
              'border-radius: 150px;-webkit-border-radius: 150px;' + \
              '-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


# Login using Google
@app.route('/gconnect', methods=['POST'])
def gconnect():
    """If user chose to use their Google login credentials, this function
    logs the user into the application.
    """
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        # Upgrade the authorization code to a credentials object.
        oauth_flow = flow_from_clientsecrets('/var/www/Catalog/catalog/client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)

    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the' +
                                            ' authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token

    # Added next line so gdisconnect would work
    login_session['access_token'] = access_token

    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?' +
           'access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(json.dumps("Token's user ID doesn't" +
                                            " match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(json.dumps("Token's client ID" +
                                            " doesn't match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check to see if user is already logged in.
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps("Current user is" +
                                            " already connected."), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info.
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data["picture"]
    login_session['email'] = data["email"]
    login_session['provider'] = 'google'

    # See if user exists and if not create a new user
    # and store user_id in the login session
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;' + \
              'border-radius: 150px;-webkit-border-radius: 150px;' + \
              '-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output


# Logout
@app.route('/disconnect')
def disconnect():
    """Checks to see if user logged in with Google or Facebook and then uses
    the appropriate section of code to disconnect user from the application. It
    returns the logged out user to the public home page via the showCategories
    function.
    """
    if login_session['provider'] == 'google':
        access_token = login_session['access_token']
        if access_token is None:
            response = make_response(json.dumps('Current user not' +
                                                ' connected.'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        url = 'https://accounts.google.com/o/oauth2/revoke?' + \
              'token=%s' % login_session['access_token']
        h = httplib2.Http()
        result = h.request(url, 'GET')[0]
        if result['status'] == '200':
            del login_session['access_token']
            del login_session['gplus_id']
            del login_session['username']
            del login_session['email']
            del login_session['picture']
            flash("Successfully disconnected.")
            return redirect(url_for('showCategories'))
        else:
            flash("Failed to revoke token for given user.")
            return redirect(url_for('showCategories'))
    else:
        facebook_id = login_session['facebook_id']
        # The access token must me included to successfully logout
        access_token = login_session['access_token']
        url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
              % (facebook_id, access_token)
        h = httplib2.Http()
        result = h.request(url, 'DELETE')[1]
        del login_session['username']
        flash("You have been successfully logged out.")
        return redirect(url_for('showCategories'))


# JSON APIs to view Catalog information
@app.route('/catalog/<string:category_name>/items/JSON')
def categoryItemsJSON(category_name):
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_name=category_name).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/catalog/<string:category_name>/item/<string:item_name>/JSON')
def itemJSON(category_name, item_name):
    item = session.query(Item). \
           filter_by(category_name=category_name, name=item_name). \
           one()
    return jsonify(item=item.serialize)


@app.route('/catalog/JSON')
def categoriesJSON():
    categories = session.query(Category).all()
    return jsonify(categories=[c.serialize for c in categories])


@app.route('/catalog/items/JSON')
def itemsJSON():
    items = session.query(Item).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/')
@app.route('/catalog')
def showCategories():
    """Pulls all Categories and the last 10 Items entered into the
    database and displays them on a public page if the user is not logged in
    or on the home page with add/edit/delete privileges if the user is
    logged in.
    """
    categories = session.query(Category).order_by(asc(Category.name))
    items = session.query(Item).order_by(Item.id.desc()).limit(10)
    if 'username' not in login_session:
        return render_template('publichome.html', categories=categories,
                               items=items)
    else:
        return render_template('home.html', categories=categories, items=items)


@app.route('/catalog/pick', methods=['GET', 'POST'])
@login_required
def pickCategory():
    """If a GET request, all the Categories are pulled and sent to a page
    where the user can select which Category they want to edit or delete. If
    a POST request, we look to see if the edit button or delete button was
    pushed so we can redirect to the appropriate page.
    """
    if request.method == 'POST':
        if request.form['button'] == "edit":
            return redirect(url_for('editCategory',
                                    category_name=request.form['category']))
        if request.form['button'] == "delete":
            return redirect(url_for('deleteCategory',
                                    category_name=request.form['category']))
    else:
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template('pickcategory.html', categories=categories)


@app.route('/catalog/new', methods=['GET', 'POST'])
@login_required
def newCategory():
    """GET request pulls a page to create a new Category. POST request queries
    to see if that new Category name already exists to prevent duplicates. If
    it exists we reject it and flash a message, if it doesn't it is added to
    the database.
    """
    if request.method == 'POST':
        try:
            categoryExist = session.query(Category). \
                            filter_by(name=request.form['name']). \
                            one()
            if categoryExist:
                flash('Category %s Already Exists' % categoryExist.name)
                return render_template('newcategory.html')
        except:
            newCategory = Category(name=request.form['name'],
                                   user_id=login_session['user_id'])
            session.add(newCategory)
            session.commit()
            flash('New Category %s Successfully Created' % newCategory.name)
            return redirect(url_for('showCategories'))
    else:
        return render_template('newcategory.html')


@app.route('/catalog/<string:category_name>/edit', methods=['GET', 'POST'])
@login_required
def editCategory(category_name):
    """GET request queries for the Category selected during the pickCategory
    function. Checks to see if the user trying to edit the Category was
    actually the creator of that Category and pulls a page to allow the user
    to edit that Category. POST request checks to see if the newly edited
    Category already exists and if not it makes the change to the database.
    """
    editedCategory = session.query(Category). \
        filter_by(name=category_name). \
        one()
    creator = getUserInfo(editedCategory.user_id)
    if login_session['username'] != creator.name:
        return "<script>function myFunction() {alert('You are not' + \
            ' authorized to edit this category. You must be the creator' + \
            ' of this category in order to edit it.'); \
            window.location='/catalog';}</script> \
            <body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            try:
                categoryExist = session.query(Category). \
                    filter_by(name=request.form['name']). \
                    one()
                if categoryExist:
                    flash('Category %s Already Exists' % categoryExist.name)
                    return render_template('editcategory.html',
                                           category=editedCategory)
            except:
                editedCategory.name = request.form['name']
                session.add(editedCategory)
                session.commit()
                flash('Category %s Successfully Edited' % editedCategory.name)
                return redirect(url_for('showCategories'))
    else:
        return render_template('editcategory.html', category=editedCategory)


@app.route('/catalog/<string:category_name>/delete', methods=['GET', 'POST'])
@login_required
def deleteCategory(category_name):
    """GET request queries for the Category selected during the pickCategory
    function. Checks to see if the user trying to delete the Category was
    actually the creator of that Category and pulls a page to allow the user
    to delete that Category. POST request makes the change to the database.
    """
    deletedCategory = session.query(Category). \
        filter_by(name=category_name). \
        one()
    creator = getUserInfo(deletedCategory.user_id)
    if login_session['username'] != creator.name:
        return "<script>function myFunction() {alert('You are not' + \
            ' authorized to delete this category. You must be the creator' + \
            ' of this category in order to delete it.'); \
            window.location='/catalog';}</script> \
            <body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(deletedCategory)
        session.commit()
        flash('%s Successfully Deleted' % deletedCategory.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('deletecategory.html', category=deletedCategory)


# Show a category's items
@app.route('/catalog/<string:category_name>')
@app.route('/catalog/<string:category_name>/items')
def showItems(category_name):
    """Pulls all the Categories, the specific Category selected by the user
    from the home page, all the items within that specific Category, and
    then counts the number of items. All this information is displayed on the
    items.html page.
    """
    categories = session.query(Category).order_by(asc(Category.name))
    category = session.query(Category).filter_by(name=category_name).one()
    items = session.query(Item).filter_by(category_name=category_name).all()
    itemscount = session.query(Item). \
        filter_by(category_name=category_name). \
        count()
    return render_template('items.html', categories=categories, items=items,
                           category=category, itemscount=itemscount)


# Create a new item
@app.route('/catalog/item/new', methods=['GET', 'POST'])
@login_required
def newItem():
    """GET request pulls a page to create a new Item. POST request queries
    to see if that new Item name already exists to prevent duplicates. If
    it exists we reject it and flash a message, if it doesn't it is added to
    the database.
    """
    if request.method == 'POST':
        try:
            itemExist = session.query(Item). \
                filter_by(name=request.form['name'],
                          category_name=request.form['category']). \
                one()
            if itemExist:
                flash('Item %s Already Exists' % itemExist.name)
                categories = session.query(Category). \
                    order_by(asc(Category.name))
                return render_template('newitem.html', categories=categories)
        except:
            newItem = Item(name=request.form['name'],
                           description=request.form['description'],
                           category_name=request.form['category'],
                           user_id=login_session['user_id'])
            session.add(newItem)
            session.commit()
            flash('New Item %s Successfully Created' % newItem.name)
            return redirect(url_for('showCategories'))
    else:
        categories = session.query(Category).order_by(asc(Category.name))
        return render_template('newitem.html', categories=categories)


@app.route('/catalog/<string:category_name>/<string:item_name>')
def showDescription(category_name, item_name):
    """If the user clicks on an item from the home page or items page, this
    function queries that item and finds it's creator. If the user was the
    creator, they see the description of the item and are allowed to edit and
    delete it. If not the creator, they only see the description.
    """
    item = session.query(Item). \
        filter_by(name=item_name, category_name=category_name).one()
    creator = getUserInfo(item.user_id)
    if 'username' not in login_session:
        return render_template('publicdescription.html', item=item)
    if login_session['username'] == creator.name:
        return render_template('description.html', item=item)
    else:
        return render_template('publicdescription.html', item=item)


@app.route('/catalog/<string:category_name>/<string:item_name>/edit',
           methods=['GET', 'POST'])
@login_required
def editItem(category_name, item_name):
    """GET request queries for the Item selected for editing and finds it's
    creator. If the user was the creator, they get a page to edit the item
    name and/or the description. POST request checks to see if the item name
    was edited. If it was, it then checks to see if that item name already
    exists. If that item doesn't exists it writes the item name and
    description to the database.
    """
    editedItem = session.query(Item). \
        filter_by(name=item_name, category_name=category_name). \
        one()
    creator = getUserInfo(editedItem.user_id)
    if login_session['username'] != creator.name:
        return "<script>function myFunction() {alert('You are not' + \
            ' authorized to edit this item. You must be the creator' + \
            ' of this item in order to edit it.'); \
            window.location='/catalog';}</script> \
            <body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            if request.form['name'] != editedItem.name:
                try:
                    itemExist = session.query(Item). \
                                filter_by(name=request.form['name'],
                                          category_name=category_name). \
                                one()
                    if itemExist:
                        flash('Item %s Already Exists' % itemExist.name)
                        return render_template('edititem.html',
                                               item=editedItem)
                except:
                    editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        session.add(editedItem)
        session.commit()
        flash('Item %s Successfully Edited' % editedItem.name)
        return render_template('description.html', item=editedItem)
    else:
        return render_template('edititem.html', item=editedItem)


@app.route('/catalog/<string:category_name>/<string:item_name>/delete',
           methods=['GET', 'POST'])
@login_required
def deleteItem(category_name, item_name):
    """GET request queries for the Item selected for deletion. Checks to
    see if the user trying to delete the Item was actually the creator
    of that Item and if they are pulls a page to allow the user
    to delete that Item. POST request makes the change to the database.
    """
    deletedItem = session.query(Item). \
        filter_by(name=item_name, category_name=category_name). \
        one()
    creator = getUserInfo(deletedItem.user_id)
    if login_session['username'] != creator.name:
        return "<script>function myFunction() {alert('You are not' + \
            ' authorized to delete this item. You must be the creator' + \
            ' of this item in order to delete it.'); \
            window.location='/catalog';}</script> \
            <body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(deletedItem)
        session.commit()
        flash('%s Successfully Deleted' % deletedItem.name)
        return redirect(url_for('showCategories'))
    else:
        return render_template('deleteitem.html', item=deletedItem)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    #app.run(host='0.0.0.0', port=5000)
    app.run()
