from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length
from app.models import User, Thread, Category, Emoji
from flask import request
from flask_wtf.file import FileField, FileRequired
import os


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    about_me = TextAreaField('About me',
                             validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')


class PostForm(FlaskForm):
    post = TextAreaField('Say something', validators=[DataRequired()])
    submit = SubmitField('Submit')


class CreateCategoryForm(FlaskForm):
    title = StringField('Category title', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_title(self, category_title):  # todo - test removing category_title from this (same for thread & emoji)
        category = Category.query.filter_by(title=self.title.data).first()
        if category is not None:
            raise ValidationError('Please use a different category name.')


class CreateThreadForm(FlaskForm):
    title = StringField('Thread title', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, category_title, *args, **kwargs):
        super(CreateThreadForm, self).__init__(*args, **kwargs)
        self.category_title = category_title

    def validate_title(self, thread_title):
        thread = Thread.query.join(Category).filter(Category.title == self.category_title,
                                                    Thread.title == self.title.data).first()
        if thread is not None:
            raise ValidationError('Please use a different thread name.')


class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)


class MessageForm(FlaskForm):
    message = TextAreaField('Message', validators=[
        DataRequired(), Length(min=0, max=140)])
    submit = SubmitField('Submit')


class UploadEmojiForm(FlaskForm):
    emoji_name = TextAreaField('emoji name', validators=[
        DataRequired(), Length(min=0, max=140)])
    file = FileField(validators=[FileRequired()])
    submit = SubmitField('Submit')

    def validate_emoji_name(self, emoji_name):
        emoji = Emoji.query.filter_by(name=self.emoji_name.data).first()
        if emoji is not None:
            raise ValidationError('This emoji name is already in use.')

        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], self.file.data.filename)
        if os.path.isfile(filepath):
            raise ValidationError('This filename already exists. Please rename your file.')