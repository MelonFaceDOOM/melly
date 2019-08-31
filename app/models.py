from datetime import datetime
from hashlib import md5
from time import time
from operator import itemgetter
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import json
import re
from app import db, login
from app.search import add_to_index, remove_from_index, query_index
import os
import contextlib
from app.static.markup import melon_markup
from sqlalchemy.event import listens_for
from PIL import Image
from app.static.avatars.random_avatar import random_avatar


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(140), index=True, unique=True)
    password_hash = db.Column(db.String(140))
    mod_level = db.Column(db.Integer, index=True)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    threads = db.relationship('Thread', backref='author', lazy='dynamic')
    categories = db.relationship('Category', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    threads_visited = db.relationship('UserThreadMetadata', backref='user', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    avatar_path = db.Column(db.String(140))
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    reactions_given = db.relationship('PostReaction', backref='user', lazy='dynamic')


    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    def react(self, post, reaction):
        reaction = PostReaction(user=self, post=post, reaction_type=reaction)
        db.session.add(reaction)
        db.session.commit()

    def remove_reaction(self, post, reaction):
        reaction = PostReaction.query.filter_by(user=self, post=post, reaction_type=reaction)
        reaction.delete()
        db.session.commit()

    def is_thread_viewed(self, thread):
        return UserThreadMetadata.query.filter_by(user=self, thread=thread).count() > 0

    def view_thread(self, thread):
        # First time viewing thread
        if not self.is_thread_viewed(thread):
            utm = UserThreadMetadata(user=self, thread=thread)
            db.session.add(utm)
            db.session.commit()
        # Re-visiting thread; increment view value
        else:
            utm = UserThreadMetadata.query.filter_by(user=self, thread=thread).first()
            utm.user_thread_views += 1
            db.session.commit()

    def set_last_viewed_timestamp(self, thread, last_viewed_timestamp):
        if not self.is_thread_viewed(thread):
            utm = UserThreadMetadata(
                user=self, thread=thread,
                last_viewed_timestamp=last_viewed_timestamp).first()
            db.session.add(utm)
            db.session.commit()
        else:
            # check if the provided timestamp is more recent than the existing one
            utm = UserThreadMetadata.query.filter_by(user=self, thread=thread).first()

            # this is needed incase a UserThreadMetadata entry has been made,
            # but there is no registered last_viewed_timestamp
            if not utm.last_viewed_timestamp:
                utm.last_viewed_timestamp = last_viewed_timestamp
                db.session.commit()
            # this is a more typical scenario.
            elif utm.last_viewed_timestamp < last_viewed_timestamp:
                utm.last_viewed_timestamp = last_viewed_timestamp
                db.session.commit()

    def get_user_thread_position(self, thread):
        """return page and post_id based on user's last_viewed_timestamp"""

        if not self.is_thread_viewed(thread):
            return None, None
        utm = UserThreadMetadata.query.filter_by(user=self, thread=thread).first()
        if not utm.last_viewed_timestamp:
            return None, None
        posts = thread.posts.order_by(Post.timestamp.asc()).filter(Post.timestamp <= utm.last_viewed_timestamp).all()
        if posts:
            pos = len(posts)  # the number of posts in thread that are older than the user's last-read post timestamp
            page_num = 1 + int((pos - 1) / current_app.config['POSTS_PER_PAGE'])  # pagenumber
            post_id = posts[-1].id  # id of the post closest to the user's last-read post timestamp
            return page_num, post_id
        else:
            return None, None

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


@listens_for(User, 'before_insert')
def user_defaults(mapper, configuration, target):
    target.avatar_path = random_avatar()


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


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
    body_formatted = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    reactions = db.relationship('PostReaction', backref='post', lazy='dynamic')

    def __repr__(self):
        return '<Post {}>'.format(self.body)

    def page(self):
        if self.thread_id:
            post_position = len(Post.query.filter_by(thread_id=self.thread_id).filter(Post.id <= self.id).all())
            page = int((post_position - 1) / current_app.config['POSTS_PER_PAGE'] + 1)
            return page

    def format(self):
        self.body_formatted = melon_markup.parse(self.body)

    def is_duplicate(self):
        # check the last post by this user in this  thread. If it is <3 s behind and the same text, it is deemed a duplicate
        posts = Post.query.filter_by(thread=self.thread, author=self.author).all()[:-1]
        if len(posts) == 0:
            return False
        if (datetime.utcnow() - posts[-1].timestamp).total_seconds() > 3:  # calculate time since self won't have a
            # timestamp until it is actually entered in the db
            return False
        if posts[-1].body != self.body:
            return False
        return True


@listens_for(Post, 'before_insert')
def post_defaults(mapper, configuration, target):
    target.body_formatted = melon_markup.parse(target.body)


class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))

    pinned_post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    posts = db.relationship('Post', backref='thread', primaryjoin=id==Post.thread_id, lazy='dynamic')
    pinned_post = db.relationship('Post', primaryjoin=pinned_post_id==Post.id)
    users_visited = db.relationship('UserThreadMetadata', backref='thread', lazy='dynamic')

    def __repr__(self):
        return '<Thread {}>'.format(self.title)

    def post_count(self):
        count = self.posts.count()
        return count

    def last_post(self):
        last_post_in_thread = Post.query.filter_by(thread_id=self.id).order_by(Post.timestamp.desc()).first()
        return last_post_in_thread

    def last_page(self):
        last_page = int((self.posts.count() - 1) / current_app.config['POSTS_PER_PAGE'] + 1)
        return last_page


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
        last_post_in_category = Post.query.join(Thread, Thread.id == Post.thread_id).filter(
            Thread.category_id == self.id).order_by(
            Post.timestamp.desc()).first()
        return last_post_in_category

    def active_threads(self, number_of_threads):
        thread_last_post_times = []
        for t in self.threads:
            p = t.last_post()
            if p is None:
                thread_last_post_times.append((t, t.timestamp))
            else:
                thread_last_post_times.append((t, p.timestamp))
        sorted_threads = sorted(thread_last_post_times, key=itemgetter(1), reverse=True)
        sorted_threads = [thread[0] for thread in sorted_threads]
        return sorted_threads[:number_of_threads]


class UserThreadMetadata(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    last_viewed_timestamp = db.Column(db.DateTime, index=True)  # the timestamp of the last post they have read
    user_thread_views = db.Column(db.Integer, default=1)
    __table_args__ = (db.UniqueConstraint('user_id', 'thread_id', name='_user_thread_metadata'),
                      )

    def __repr__(self):
        return '<UserThreadMetadata for user {} in thread {}>'.format(self.user_id, self.thread_id)


class PostReaction(db.Model):
    # stores user reactions to posts
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    emoji_id = db.Column(db.Integer, db.ForeignKey('emoji.id'))
    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', 'emoji_id'),
                      )

    def __repr__(self):
        return '<PostReaction {}>'.format(self.id)


class Emoji(db.Model):
    # stores reaction images
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))
    file_path = db.Column(db.String(140))
    small_path = db.Column(db.String(140))
    posts = db.relationship('PostReaction', backref='emoji', lazy='dynamic')

    def __repr__(self):
        return '<Emoji {}>'.format(self.name)

    def delete(self):
        with contextlib.suppress(FileNotFoundError):
            os.remove(self.file_path)
        db.session.delete(self)
        db.session.commit()


def resize_image(filepath, max_dimension=128, save_path=None):
    img = Image.open(filepath)

    if save_path is None:
        save_path = filepath

    if img.size[0] > max_dimension and img.size[0] > img.size[1]:
        percent = (max_dimension / float(img.size[0]))
        height = int((float(img.size[1]) * float(percent)))
        img = img.resize((max_dimension, height), Image.ANTIALIAS)

    if img.size[1] > max_dimension and img.size[1] > img.size[0]:
        percent = (max_dimension / float(img.size[1]))
        width = int((float(img.size[0]) * float(percent)))
        img = img.resize((width, max_dimension), Image.ANTIALIAS)
    print(save_path)
    img.save(save_path)
    return save_path


@listens_for(Emoji, 'before_insert')
def emoji_defaults(mapper, configuration, target):

    source_path = os.path.join("app", "static", target.file_path)
    retries = 0
    while True:
        pattern = r"(.+)[.](.+?$)"
        match = re.match(pattern, source_path)
        if match is None:
            return None
        save_path = match.groups()[0] + "_s." + match.groups()[1]
        if not os.path.exists(save_path) or retries > 20:
            break
        retries += 1
    else:
        return None

    print(save_path)
    save_path = resize_image(source_path, max_dimension=80, save_path=save_path)
    save_path = os.path.relpath(save_path, os.path.join(os.getcwd(), "app", "static"))
    target.small_path = save_path.replace("\\", "/")


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def __repr__(self):
        return '<Notification {}>'.format(self.name)

    def get_data(self):
        return json.loads(str(self.payload_json))
