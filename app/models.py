from datetime import datetime
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
from app.static.images.donuts.random_donut import random_donut
from sqlalchemy.orm import validates


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(300), index=True, unique=True)
    join_timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    password_hash = db.Column(db.String(140))
    mod_level = db.Column(db.Integer, index=True, default=1)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    threads = db.relationship('Thread', backref='author', lazy='dynamic')
    categories = db.relationship('Category', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    threads_visited = db.relationship('UserThreadMetadata', backref='user', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    avatar_path = db.Column(db.String(300))
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    reactions_given = db.relationship('PostReaction', backref='user', lazy='dynamic')
    edits = db.relationship('EditHistory', backref='editor', lazy='dynamic')
    # TODO: change from editor to original author


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
    body = db.Column(db.String(5000))
    body_formatted = db.Column(db.String(10000))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('thread.id'))
    reactions = db.relationship('PostReaction', backref='post', lazy='dynamic')
    edits = db.relationship('EditHistory', backref='original_post', lazy='dynamic')

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

    def edit(self, new_body, editor=None):
        #TODO: check if editor is a valid user
        history = EditHistory(
            body=self.body,
            body_formatted=self.body_formatted,
            original_post=self,
            editor=editor
        )
        db.session.add(history)
        db.session.commit()
        self.body = new_body
        self.format()
        db.session.commit()

    def last_edited(self):
        latest_edit = self.edits.order_by(EditHistory.timestamp.desc()).first()
        if latest_edit:
            return latest_edit.timestamp
        else:
            return None


@listens_for(Post, 'before_insert')
def post_defaults(mapper, configuration, target):
    target.body_formatted = melon_markup.parse(target.body)


# make edit
# new EditHistory
# copy body, body_formatted, timestamp, post_id
# change body of original post. Update body_formatted. Update timestamp


class EditHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(5000))  # holds the pre-edit body, while the Post object gets updated with the new body
    body_formatted = db.Column(db.String(10000))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    original_post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    edited_by = db.Column(db.Integer, db.ForeignKey('user.id'))


class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    pinned_post_id = db.Column(db.Integer, db.ForeignKey('post.id'))

    # I can't remember why posts and pinned_post are like this, but there was something conflicting about having two
    # different things being related to post in the normal way, and this solved it.
    posts = db.relationship('Post', backref='thread', primaryjoin=id==Post.thread_id, lazy='dynamic')
    pinned_post = db.relationship('Post', primaryjoin=pinned_post_id==Post.id)
    users_visited = db.relationship('UserThreadMetadata', backref='thread', lazy='dynamic')

    @validates('title')
    def validate_title(self, key, title):
        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if regex.search(title) == None:
            return title
        else:
            raise ValueError("Thread title can't contain special characters")

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

    def info_icons(self, user):
        info_icons = []

        # return dount if there is an unread post for the user
        page_num, user_last_viewed_post_id = user.get_user_thread_position(self)
        newest_post = self.last_post()
        if not user_last_viewed_post_id:
            donut = random_donut()
            info_icons.append(donut)
        elif newest_post and user_last_viewed_post_id:
            if newest_post.id > user_last_viewed_post_id:
                donut = random_donut()
                info_icons.append(donut)

        return info_icons


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), index=True, unique=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    threads = db.relationship('Thread', backref='category', lazy='dynamic')

    @validates('title')
    def validate_title(self, key, title):
        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if regex.search(title) == None:
            return title
        else:
            raise ValueError("Category title can't contain special characters")

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
    name = db.Column(db.String(15), unique=True)
    file_path = db.Column(db.String(300))
    small_path = db.Column(db.String(300))
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

    if img.size[0] > max_dimension and (img.size[0] >= img.size[1]):
        percent = (max_dimension / float(img.size[0]))
        height = int((float(img.size[1]) * float(percent)))
        img = img.resize((max_dimension, height), Image.ANTIALIAS)

    if img.size[1] > max_dimension and img.size[1] > img.size[0]:
        percent = (max_dimension / float(img.size[1]))
        width = int((float(img.size[0]) * float(percent)))
        img = img.resize((width, max_dimension), Image.ANTIALIAS)

    img.save(save_path)
    return save_path


@listens_for(Emoji, 'before_insert')
def emoji_defaults(mapper, configuration, target):
    """upon adding an emoji, automatically resize to 80x80 and store a second file"""
    source_path = os.path.join("app", "static", target.file_path)
    pattern = r"(.+)[.](.+?$)"
    match = re.match(pattern, source_path)
    if match is None:
        target.small_path = "filepath not recognized"
        return None

    path_and_name = match.groups()[0]
    extension = match.groups()[1]

    # don't bother resizing gif at the moment, since by default only one frame is resized and the animation is lost
    # TODO: implement a way to resize gifs and replace this code
    if extension == "gif":
        target.small_path = target.file_path
        return None

    # find an _s name that isn't already taken
    i = 0
    while True:
        save_path = path_and_name + "_s" + (str(i) if i > 0 else "") + "." + extension
        if not os.path.exists(save_path):
            break
        i += 1

    save_path = resize_image(source_path, max_dimension=35, save_path=save_path)
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
