import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    #mail variables won't be set unless they are set in the environemnt.
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['lemmyelon@gmail']
    
    # MAIL_SERVER = "smtp.googlemail.com"
    # MAIL_PORT = 587
    # MAIL_USE_TLS = 1
    # MAIL_USERNAME = "lemmyelon@gmail.com"
    # MAIL_PASSWORD = "unfamiliardessertspoon"
    # ADMINS = ['lemmyelon@gmail.com']
    
    POSTS_PER_PAGE = 25