from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()

# Redirect unauthorized users to the login page
login_manager.login_view = "login"

login_manager.login_message = "Please log in to access the billing dashboard."
login_manager.login_message_category = "warning"

# Strong session protection
login_manager.session_protection = "strong"