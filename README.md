# Linux Server Configuration

  This project takes a baseline installation of a Linux server on Amazon Lightsail and preparing it to host a web application.

### CREATED THE SERVER FROM [AMAZON LIGHTSAIL](https://signin.aws.amazon.com/signin?redirect_uri=https%3A%2F%2Flightsail.aws.amazon.com%2Fls%2Fwebapp%3Fstate%3DhashArgs%2523%26isauthcode%3Dtrue&client_id=arn%3Aaws%3Aiam%3A%3A015428540659%3Auser%2Fparksidewebapp&forceMobileApp=0):

  * Created an AWS account
  * Created an OS Only, Ubuntu instance (VM) named **silly-willy-lucy**
  * Converted public IP address into a static IP address -- **18.217.253.59**
  * Which gave my URL as [http://ec2-18-217-253-59.us-east-2.compute.amazonaws.com](http://ec2-18-217-253-59.us-east-2.compute.amazonaws.com)
  * Logged in via the Amazon Lightsail website's "Connect using SSH" button

### SECURED THE SERVER:
  * Checked for available package lists:
    * **`cat /etc/apt/sources.list`**
  * Updated available package lists
    * **`sudo apt-get update`**
  * Upgraded installed packages
    * **`sudo apt-get upgrade`**
  * Removed packges no longer required
    * **`sudo apt-get autoremove`**
  * Installed package named finger
    * **`sudo apt-get install finger`**
  * Configured firewall ports
    * **`sudo ufw status`**
        _Status: inactive_
    * **`sudo ufw default deny incoming`**
    * **`sudo ufw default allow outgoing`**
    * **`sudo ufw allow ssh`**
    * **`sudo ufw allow 2200/tcp`**
    * **`sudo ufw allow www`**
    * **`sudo ufw allow ntp`**
    * **`sudo ufw allow 123/udp`**
    * **`sudo ufw allow out 123/udp`**
    * **`sudo ufw delete allow 22`**
    * **`sudo ufw enable`**
  * Changed the SSH port from 22 to 2200
    * **`sudo nano  /etc/ssh/sshd_config`**
    * _changed line entry from 22 to 2200_
    * **`sudo service sshd restart`**
  * On Lightsail website, added Custom TCP 2200 port on the firewall table
  * Timezone was already set for UTC
    * **`cat /etc/timezone`**
    * result shows _Etc/UTC_
  * But if not it could be set with command
    * **`sudo timedatectl set-timezone Etc/UTC`**
  * Disabled ssh login for root user and forced key-based authentication
    * **`sudo nano /etc/ssh/sshd_config`**
    * Find the _PermitRootLogin_ line and edit to _no_.
    * Find the _PasswordAuthentication_ line and edit to _no_.
    * **`sudo service ssh restart`**

### CONFIGURED NEW USER NAMED “GRADER”:
  * Created a new user
    * **`sudo adduser grader`**
  * Gave user grader sudo access
    * **`sudo nano /etc/sudoers.d/grader`**
    *  which created the file named grader and then put this line in the file  
    _grader ALL=(ALL) NOPASSWD:ALL_
  * Generated a key pair on my local machine using **ssh-keygen** and saved the key pair files in my local /.ssh directory with filename graderkey and graderkey.pub
  * Uploaded grader’s public key onto the server
    * **`su to grader`**
    * **`grader@ip-172-26-8-226:~$ mkdir .ssh`**
    * **`grader@ip-172-26-8-226:~$ touch .ssh/authorized_keys`**
    * **`grader@ip-172-26-8-226:~$ nano .ssh/authorized_keys`**
    * and pasted in the contents of the graderkey.pub file onto a single line
    * **`grader@ip-172-26-8-226:~$ chmod 700 .ssh`**
    * **`grader@ip-172-26-8-226:~$ chmod 644 .ssh/authorized_keys`**
    * The public key for ubuntu was already built on the server by default. So the steps above were only for uploading the grader public key onto the server.
  * Built Putty sessions for both users (ubuntu and grader) using their respective private
    keys. (Ubuntu’s private key can be found on the Amazon Lightsail website.) [Build a Putty session](https://lightsail.aws.amazon.com/ls/docs/how-to/article/lightsail-how-to-set-up-putty-to-connect-using-ssh).
    Remember the port is no longer default port 22 but changed to port 2200!

### INSTALLED AND CONFIGURED THE WEBSERVER:
  * Installed Apache2 web server
    * **`sudo apt-get install apache2`**
    * Tested it by entering my VM staticIP into the url of a web browser and the Apache2 Ubuntu Default Page appeared
  * Configured Apache2 to serve a Python mod_wsgi application
    * **`sudo apt-get install python`**
    * **`sudo apt-get install libapache2-mod-wsgi`**
    * **`sudo nano /etc/apache2/sites-enabled/000-default.conf`**
    * inserted _WSGIScriptAlias / /var/www/html/myapp.wsgi_ right before **< /VirtualHost >** tag
  * Created the myapp.wsgi file to test the wsgi Apache configuration
      * **`sudo nano /var/www/html/myapp.wsgi`**
      * copied this into the file:
       ```
       def application(environ, start_response):
        status = '200 OK'
        output = 'Hello Udacity!'

        response_headers = [('Content-type', 'text/plain'), ('Content-Length', str(len(output)))]
        start_response(status, response_headers)

        return [output]
        ```
  * Restarted Apache
    * **`sudo apache2ctl restart`**
  * Refreshed my browser page and the _Apache2 Ubuntu Default Page_ was replaced with _Hello Udacity!_ which proved the webserver was serving the python wsgi module

### INSTALLED AND CONFIGURED THE DATABASE SERVER:
  * Installed PostgreSQL
    * **`sudo apt-get install postgresql`**
  * Logged into PostgreSQL
    * **`sudo -u postgres psql`**
  * Created new database user
    * **`postgres=# CREATE USER catalog;`**
  * Ensured no remote connections are allowed by not having any **host** connection types except those with localhost addresses
    * **`sudo nano /etc/postgresql/9.5/main/pg_hba.conf`**
  * Created a test db to check communication between webserver and dbserver
    * **`postgres=# CREATE DATABASE test;`**
    * **`postgres=# GRANT ALL PRIVILEGES ON DATABASE test TO catalog;`**
    * **`postgres=# \c test;`**
    * **`test=# CREATE TABLE message (id serial PRIMARY KEY, data varchar (50) NOT NULL);`**
    * **`test=# GRANT ALL PRIVILEGES ON TABLE message TO catalog;`**
    * **`test=# INSERT INTO message VALUES (1, 'Test Message');`**
    * **`test=# SELECT * FROM message;`**
    * **`postgres=# ALTER USER catalog WITH PASSWORD 'catalog';`**
  * Restarted Apache2 and Postgresql
    * **`sudo /etc/init.d/apache2 restart`**
    * **`sudo /etc/init.d/postgresql reload`**
  * Installed pip
    * **`sudo apt-get install python-pip`**
  * Installed psycopg2
    * **`pip install psycopg2`**
    * **`sudo apt-get install python-psycopg2`**
  * Changed the myapp.wsgi file as follows to test the communication between
    the webserver and the dbserver
    ```
    #!/usr/bin/env python
    import psycopg2

    def application(environ, start_response):
           status = '200 OK'
    #       output = 'Hello Udacity!'

           db = psycopg2.connect("dbname='test' user='catalog' password='catalog'")
           c = db.cursor()
           c.execute("SELECT * FROM message")
           output = c.fetchall()
           output = output[0][1]

          response_headers = [('Content-type', 'text/plain'), ('Content-Length', str($
          start_response(status, response_headers)

         return [output]
    ```
  * Refreshed my browser page and the _Hello Udacity!_ was replaced with _Test Message_ which proved the webserver was communicating with the database server.

### INSTALLED SOFTWARE NEEDED TO RUN THE CATALOG APP: (see note 1)
  * Installed git
    * **`sudo apt-get install git-core`**
  * Installed Jinja2
    * **`sudo easy_install Jinja2`**
  * Installed SQLAlchemy
    * **`sudo apt-get install python-sqlalchemy`**
  * Installed Flask
    * **`sudo apt-get install python-flask`**
  * Installed Oauth2client
    * **`sudo apt-get install python-oauth2client`**
  * Installed Requests
    * **`sudo apt-get install python-requests`**
  * Tried to install httplib2 but it said it was already the newest version
    * **`sudo apt-get install python-httplib2`**

**Note 1** – I learned later the only software needed globally was git, pip, and virtualenv. Its best to install the app dependency software within the virtual environment for the app.

### INSTALLED AND CONFIGURED THE CATALOG APP:
  * Created a directory structure to house the Catalog app
    * **`grader@ip-172-26-8-226:/var/www$ mkdir Catalog`**
    * **`grader@ip-172-26-8-226:/var/www$ cd Catalog`**
    * **`grader@ip-172-26-8-226:/var/www$ mkdir catalog`**
    * **`grader@ip-172-26-8-226:/var/www$ cd catalog`**
  * Cloned my Catalog project from GitHub into that directory structure
    * **`ubuntu@ip-172-26-8-226:/var/www/ Catalog/catalog$ sudo git clone https://github.com/bm8839/Catalog.git`**
  * Created an empty `__init__.py` file
    * **`grader@ip-172-26-8-226:/var/www/Catalog/catalog$ sudo nano __init__.py`**
  * Set up a virtual environment
    * **`grader@ip-172-26-8-226:/var/www/Catalog/catalog$ sudo pip install virtualenv`**
    * **`grader@ip-172-26-8-226:/var/www/Catalog/catalog$ sudo virtualenv venv`**
    * **`grader@ip-172-26-8-226:/var/www/Catalog/catalog$ source venv/bin/activate`**
    * **`(venv) grader@ip-172-26-8-226:/var/www/Catalog/catalog$ sudo pip install Flask`**
  * Configured a new virtual host file
    * **`(venv) grader@ip-172-26-8-226:/var/www/Catalog/catalog$ sudo nano /etc/apache2/sites-available/catalog.conf`**

The file looks like this:
```
<VirtualHost *:80>
		# ServerName mywebsite.com
		# ServerAdmin admin@mywebsite.com
		WSGIScriptAlias / /var/www/Catalog/catalog.wsgi
		<Directory /var/www/Catalog/catalog/>
			Order allow,deny
			Allow from all
		</Directory>
		Alias /static /var/www/Catalog/catalog/static
		<Directory /var/www/Catalig/catalog/static/>
			Order allow,deny
			Allow from all
		</Directory>
		ErrorLog ${APACHE_LOG_DIR}/error.log
		LogLevel warn
		CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```
  * Enabled virtual host file
    * **`(venv) grader@ip-172-26-8-226:/var/www/Catalog/catalog$ sudo a2ensite catalog`**
  * Disabled the default configuration virtual host file
    * **`grader@ip-172-26-8-226:/etc/apache2/sites-available$ sudo a2dissite 000-default`**
  * Created .wsgi file
    * **`(venv) grader@ip-172-26-8-226:/var/www/Catalog$ sudo nano
    catalog.wsgi`**

The file looks like this:
```
#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/Catalog/")

from catalog.application import app as application
application.secret_key = 'super_secret_key'
```
  * On the Google Cloud Console, added my server’s IP address and URL to the Credentials Oauth 2.0 Authorized Javascript origins
  * Also added my server’s IP address and URL to the *client_secrets.json* file
  * On Facebook Developers website for my Catalog app under Settings >Basic I changed the Site URL from localhost:5000 to my server’s URL and then under Facebook Login>Settings I entered my server’s URL in Valid OAuth redirect URIs
  * Changed the database connection in the *application.py*, *catalogdb_setup.py*, and *fillcatalogdb.py* files to:
    * **`engine = create_engine(‘postgresql: //catalog:catalog@localhost/catalog’)`**`
  * Added **unique=True** constraint to the table “category” name definition in the *catalogdb_setup.py* file
    * **`name = Column(String(250), unique=True, nullable=False)`**
  * In the *application.py* file, added the complete path to the various places referencing *client_secrets.json* and *fb_client_secrets.json* files
    * **`json.loads(open('/var/www/Catalog/catalog/client_secrets.json', 'r')`**
    * **`json.loads(open('/var/www/Catalog/catalog/fb_client_secrets.json', 'r')`**
  * Gave database user “catalog” permission to create database
    * **`postgres=# ALTER USER catalog CREATEDB;`**
  * Created database named catalog and made it owned by the “catalog” user
    * **`postgres=# CREATE DATABASE catalog WITH OWNER catalog;`**
  * Loaded tables into the catalog database
    * **`ubuntu@ip-172-26-8-226:/var/www/Catalog/catalog$ python catalogdb_setup.py`**
  * Filled the database with some data
    * **`ubuntu@ip-172-26-8-226:/var/www/Catalog/catalog$ python fillcatalogdb.py`**
  * Created .gitignore file to exclude my venv directory from being pushed to GitHub
    * **`ubuntu@ip-172-26-8-226:/var/www/Catalog/catalog$ sudo nano .gitignore`**
    * then inserted one small line into the file:
    `venv/`
  * Hid/blocked the .git folder so it cannot be accessed via a browser
    * **`sudo nano /etc/apache2/sites-enabled/catalog.conf`**
    * Added the following line of code: **`RedirectMatch 404 /\.git`**

### Resources
  * [Udacity](https://discussions.udacity.com/t/lightsail-project-internal-server-error/502337/17)
  * [Amazon Web Services](https://signin.aws.amazon.com/signin?redirect_uri=https%3A%2F%2Flightsail.aws.amazon.com%2Fls%2Fwebapp%3Fstate%3DhashArgs%2523%26isauthcode%3Dtrue&client_id=arn%3Aaws%3Aiam%3A%3A015428540659%3Auser%2Fparksidewebapp&forceMobileApp=0)
  * [DigitalOcean](https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps#step-four-%E2%80%93-configure-and-enable-a-new-virtual-host)
  * [dabapps](https://www.dabapps.com/blog/introduction-to-pip-and-virtualenv-python/)
  * [Atlassian](https://www.atlassian.com/git/tutorials/using-branches)
  * [GitHub](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet#emphasis)
  * [PostgreSQL](https://www.postgresql.org/docs/9.5/static/sql-createuser.html)
  * [Ubuntu](https://askubuntu.com/questions/3375/how-to-change-time-zone-settings-from-the-command-line)
  * [Apache](http://httpd.apache.org/docs/2.4/)
  * Special Thanks to **iliketomatoes** for a very helpful [README](https://github.com/iliketomatoes/linux_server_configuration)

### Usage
How to access the Catalog App:

Open any browser and enter IP Address 18.217.253.59

Or in any browser enter the URL [http://ec2-18-217-253-59.us-east-2.compute.amazonaws.com](http://ec2-18-217-253-59.us-east-2.compute.amazonaws.com)

### License
Catalog App is released under the [MIT License](https://github.com/bm8839/Catalog/blob/master/License.txt)

