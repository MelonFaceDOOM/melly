from datetime import datetime
from hashlib import md5
from time import time
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from app import db, login
from sqlalchemy.ext.hybrid import hybrid_property
from app.search import add_to_index, remove_from_index, query_index


followers = db.Table(
    'followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    threads = db.relationship('Thread', backref='author', lazy='dynamic')
    categories = db.relationship('Category', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    threads_viewed = db.relationship('User_Thread_Position', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
                followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())

    #todo - add views(thread_id)

    def last_page_viewed(self, thread_id):
        utp = User_Thread_Position.query.filter_by(user_id=self.id,thread_id=thread_id).first()
        if utp is None:
            page_num = None
        else:
            last_post_viewed = utp.last_post_viewed
            if last_post_viewed is None:
                page_num = 1
            else:
                page_num = 1 + int((last_post_viewed-1) / current_app.config['POSTS_PER_PAGE']) # doing this allows for last_page to still be found if POSTS_PER_PAGE changes.
        return page_num
        
    def view_increment(self, thread_id):
        utp = User_Thread_Position.query.filter_by(user_id=self.id,thread_id=thread_id).first()
        if utp is None:
            utp = User_Thread_Position(user_id=self.id, thread_id=thread_id,
                                       last_post_viewed=1, user_views=1)
            db.session.add(utp)
        else:
            if utp.user_views is None:
                utp.user_views = 1
            else:
                utp.user_views += 1
        db.session.commit()
        
    def update_last_post_viewed(self, thread_id, last_post_viewed):
        utp = User_Thread_Position.query.filter_by(user_id=self.id, thread_id=thread_id).first()
        if utp is None:
            utp = User_Thread_Position(user_id=self.id, thread_id=thread_id,
                                       last_post_viewed=1, user_views=1)
        elif utp.last_post_viewed is None:
            utp.last_post_viewed = 1
        elif utp.last_post_viewed >= last_post_viewed:
            return None
        else:
            utp.last_post_viewed = last_post_viewed
        db.session.commit()

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'],
            algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))
        
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), index=True, unique=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    threads = db.relationship('Thread', backref='category', lazy='dynamic')

    def __repr__(self):
        return '<Category {}>'.format(self.title)
        
    def post_count(self):
        count = sum([t.posts.count() for t in self.threads])
        return count
        
    def last_post(self):
        #Post where Post.thread_id == (Thread where Thread.category_id == self.id).id
        last_post_in_category = Post.query.join(Thread,Thread.id==Post.thread_id).filter(
            Thread.category_id == self.id).order_by(
            Post.timestamp.desc()).first()
        return last_post_in_category

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    posts = db.relationship('Post', backref='thread', lazy='dynamic')
    users_visited = db.relationship('User_Thread_Position', backref='thread', lazy='dynamic')

    def __repr__(self):
        return '<Thread {}>'.format(self.title)
    
    def post_count(self):
        count = self.posts.count()
        return count
    
    def last_post(self):
        last_post_in_thread = Post.query.filter_by(thread_id=self.id).order_by(Post.timestamp.desc()).first()
        return last_post_in_thread
        
    def last_page(self):
        last_page = int((self.posts.count()-1)/current_app.config['POSTS_PER_PAGE']+1)
        return last_page
        
class User_Thread_Position(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    last_post_viewed = db.Column(db.Integer)
    user_views = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint('user_id', 'thread_id', name='_user_thread_position'),
                     )
    def __repr__(self):
        return '<User_Thread_Position for {} in {}>'.format(self.user_id, self.thread_id)
    
        
class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)

db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

class Post(SearchableMixin, db.Model):
    __searchable__ = ['body']
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)