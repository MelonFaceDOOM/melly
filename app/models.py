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
    threads_viewed = db.relationship('User_Thread_Position', backref='user', lazy='dynamic') #todo - test this

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

    def view_increment(self, thread_id):
        utp = User_Thread_Position.query.filter_by(user_id=self.id,thread_id=thread_id).first()
        if utp is None:
            utp = User_Thread_Position(user_id=self.id, thread_id=thread_id, user_views=1)
            db.session.add(utp)
        else:
            utp.user_views += 1
        db.session.commit()

    def current_thread_position(self, thread_id):
        # given a thread, returns the page number and post_id of the user's last viewed post in that thread.
        utp = User_Thread_Position.query.filter_by(user_id=self.id, thread_id=thread_id).first()
        if utp is None:
            return None, None
        else:
            post_id = utp.last_post_viewed_id
            if post_id is None:
                return None, None

            thread = Thread.query.filter_by(id=thread_id).first()
            pos = thread.posts.order_by(Post.id.asc()).filter(Post.id<=post_id).count()
            page_num = 1 + int((pos-1) / current_app.config['POSTS_PER_PAGE'])
            return page_num, post_id

    def update_last_post_viewed(self, thread_id, last_post_viewed_id):
        # todo - clean up/simplify
        utp = User_Thread_Position.query.filter_by(user_id=self.id, thread_id=thread_id).first()
        if utp is None:
            try:
                first_post_id = Thread.query.filter_by(id=thread_id).first().posts[0].id
            except IndexError:
                first_post_id = None

            utp = User_Thread_Position(user_id=self.id, thread_id=thread_id,
                                       last_post_viewed_id=first_post_id,
                                       user_views=1)
            db.sessions.add(utp)
            db.session.commit()
            return None
        elif utp.last_post_viewed_id is None:
            if last_post_viewed_id:
                utp.last_post_viewed_id = last_post_viewed_id
        elif last_post_viewed_id and utp.last_post_viewed_id >= last_post_viewed_id:
            return None
        elif last_post_viewed_id and utp.last_post_viewed_id < last_post_viewed_id:
            utp.last_post_viewed_id = last_post_viewed_id
            db.session.commit()
            return None
        else:
            return None


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
        # Post where Post.thread_id == (Thread where Thread.category_id == self.id).id
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
    users_visited = db.relationship('User_Thread_Position', backref='thread', lazy='dynamic') #todo - test this

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
    last_post_viewed_id = db.Column(db.Integer, db.ForeignKey('post.id'))
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
    users_viewed = db.relationship('User_Thread_Position', backref='last_post_viewed', lazy='dynamic') #todo - test this
    def __repr__(self):
        return '<Post {}>'.format(self.body)

    #todo - add a function to return the page/id of a post so that its position can be easily anchored