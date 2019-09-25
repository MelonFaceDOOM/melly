from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Length
from app.models import User, Thread, Category
from flask import request
import re


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
        if len(username.data) > 64:
            raise ValidationError('Username cannot exceed 64 characters')


class PostForm(FlaskForm):
    post = TextAreaField(label="Make a post", validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_post(self, post):
        if len(post.data) > 5000:
            raise ValidationError('post body cannot exceed 5000 characters')


class CreateCategoryForm(FlaskForm):
    title = StringField('Category title', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_title(self, category_title):
        category = Category.query.filter_by(title=self.title.data).first()
        if category is not None:
            raise ValidationError('Please use a different category name.')
        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if regex.search(self.title.data):
            raise ValidationError("Category title can't contain special characters")


class CreateThreadForm(FlaskForm):
    title = StringField('Thread title', validators=[DataRequired()])
    post = TextAreaField('Make a post', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def __init__(self, category_title, *args, **kwargs):
        super(CreateThreadForm, self).__init__(*args, **kwargs)
        self.category_title = category_title

    def validate_title(self, thread_title):
        thread = Thread.query.join(Category).filter(Category.title == self.category_title,
                                                    Thread.title == self.title.data).first()
        if thread is not None:
            raise ValidationError('Thread name is already in use in this category.')

        regex = re.compile('[@_!#$%^&*()<>?/\|}{~:]')
        if regex.search(self.title.data):
            raise ValueError("Thread title can't contain special characters")

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