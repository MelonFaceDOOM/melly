from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, current_app, jsonify
from flask_login import current_user, login_required
from app import db
from app.main.forms import (EditProfileForm, PostForm, CreateCategoryForm, CreateThreadForm, SearchForm, MessageForm)
from app.models import User, Post, Thread, Category, Message, PostReaction, Emoji
from app.main import bp
import os
import re
from sqlalchemy import func
from werkzeug.utils import secure_filename
from sqlalchemy.exc import IntegrityError


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    categories = Category.query.order_by(Category.timestamp.asc()).paginate(
        page, current_app.config['CATEGORIES_PER_PAGE'], False)

    next_url = url_for('main.index', page=categories.next_num) \
        if categories.has_next else None
    prev_url = url_for('main.index', page=categories.prev_num) \
        if categories.has_prev else None
    return render_template('index.html', title='Home',
                           categories=categories.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@bp.route('/create_category', methods=['GET', 'POST'])
@login_required
def create_category():
    form = CreateCategoryForm()
    if form.validate_on_submit():
        category = Category(title=form.title.data, author=current_user)
        db.session.add(category)
        db.session.commit()
        flash('Your category, {} has been created! Make a first thread!'.format(form.title.data))
        return redirect(url_for('main.category', category_id=category.id))
    return render_template('create_category.html', title='Create a new category',
                           form=form)


@bp.route('/edit_category/<category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    # intentionally allow anyone to edit category titles
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        flash('category {} not found.'.format(category_id))
        return redirect(url_for('main.index'))

    form = CreateCategoryForm()
    if form.validate_on_submit():
        category.title = form.title.data
        db.session.commit()
        flash('The category has been edited')
        return redirect(url_for('main.index'))
    elif request.method == 'GET':
        form.title.data = category.title
    return render_template('create_category.html', title='Edit Category Title', form=form)


@bp.route('/cat/<category_id>')
@login_required
def category(category_id):
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        flash('category {} not found.'.format(category_id))
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    threads = category.threads.order_by(Thread.timestamp.asc()).paginate(
        page, current_app.config['THREADS_PER_PAGE'], False)
    next_url = url_for('main.category', page=threads.next_num, category_id=category_id) \
        if threads.has_next else None
    prev_url = url_for('main.category', page=threads.prev_num, category_id=category_id) \
        if threads.has_prev else None
    return render_template('category.html', title=category.title, category=category, threads=threads.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/cat/<category_id>/create_thread', methods=['GET', 'POST'])
@login_required
def create_thread(category_id):
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        flash('category {} not found.'.format(category_id))
        return redirect(url_for('main.index'))

    form = CreateThreadForm(category.title)
    if form.validate_on_submit():
        thread = Thread(title=form.title.data, author=current_user, category=category)
        db.session.add(thread)
        db.session.commit()
        post = Post(body=form.post.data, author=current_user, thread=thread)
        db.session.add(post)
        db.session.commit()
        flash('Your thread {} has been created! Make a first post!'.format(form.title.data))
        return redirect(url_for('main.thread', thread_id=thread.id))
    return render_template('create_thread.html', title='Create a new thread',
                           category_id=category_id, form=form)


@bp.route('/edit_thread/<thread_id>', methods=['GET', 'POST'])
@login_required
def edit_thread(thread_id):
    # todo - add ability to move the thread to a different category in the form
    thread = Thread.query.filter_by(id=thread_id).first()
    if thread is None:
        flash('thread {} not found.'.format(thread_id))
        return redirect(url_for('main.index'))

    if thread.author.username is not current_user.username:
        flash('You are not the author of thread {}.'.format(thread_id))
        return redirect(url_for('main.category', category_id=thread.category.id))

    form = CreateThreadForm(thread.category.title)
    if form.validate_on_submit():
        thread.title = form.title.data
        db.session.commit()
        flash('The thread has been edited')
        return redirect(url_for('main.category', category_id=thread.category.id))
    elif request.method == 'GET':
        form.title.data = thread.title
    return render_template('create_thread.html', title='Edit thread Title', form=form)


@bp.route('/thread/<thread_id>', methods=['GET', 'POST'])
@login_required
def thread(thread_id):
    thread = Thread.query.filter_by(id=thread_id).first()
    # If thread is not found, return to index
    if thread is None:
        flash('thread "{}" not found'.format(thread_id))
        return redirect(url_for('main.index'))

    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user, thread=thread)
        if not post.is_duplicate():
            post.format()
            db.session.add(post)
            db.session.commit()
            flash('Your post is now live!')
        else:
            flash('Please wait three seconds before spamming your garbage, {}'.format(current_user.username) )

        anchor = 'p' + str(post.id)
        return redirect(
            url_for('main.thread', thread_id=thread_id, page=thread.last_page(), _anchor=anchor))

    # if page is not specified, find the user's last post and redirect to it.
    page = request.args.get('page', None, type=int)

    '''This is a weird work-around to anchor to a specific post-id
    Basically, if no page is provided, it will find a page & anchor
    value, and re-route to itself. Since page will have a value this
    time, it will skip over this section of the code'''
    if not page:
        last_page_viewed, last_post_id = current_user.get_user_thread_position(thread=thread)
        page = last_page_viewed if last_page_viewed else 1
        anchor = 'p' + str(last_post_id) if last_post_id else None
        return redirect(
            url_for('main.thread', thread_id=thread_id, page=page, _anchor=anchor))

    page = request.args.get('page', 1, type=int)
    posts = thread.posts.order_by(Post.timestamp.asc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)

    pinned_post = thread.pinned_post

    next_url = url_for('main.thread', thread_id=thread_id,
                       page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.thread', thread_id=thread_id,
                       page=posts.prev_num) \
        if posts.has_prev else None


    # add 1 view to the user's view count for this thread
    current_user.view_thread(thread=thread)

    # if the thread is not empty, update the user's last_viewed_timestamp
    if posts.items:
        last_viewed_timestamp = posts.items[-1].timestamp
        current_user.set_last_viewed_timestamp(
            thread=thread,
            last_viewed_timestamp=last_viewed_timestamp)

    return render_template('thread.html', title=thread.title, form=form,
                           posts=posts, pinned_post=pinned_post, next_url=next_url,
                           thread=thread, prev_url=prev_url)


@bp.route('/reaction_menu', methods=['GET'])
@login_required
def reaction_menu():
    page = request.args.get('page', 1, type=int)
    post_id = request.args.get('post_id', 0, type=int)
    emojis = Emoji.query.filter(Emoji.id > 0).order_by(Emoji.id.asc()).paginate(
        page, 20, False)

    next_emoji_url = url_for('main.reaction_menu', page=emojis.next_num, post_id=post_id) \
        if emojis.has_next else None
    prev_emoji_url = url_for('main.reaction_menu', page=emojis.prev_num, post_id=post_id) \
        if emojis.has_prev else None

    return render_template("_reaction_menu.html", emojis=emojis.items, pages=emojis.iter_pages(), starting_page=page,
                           post_id=post_id, next_emoji_url=next_emoji_url, prev_emoji_url=prev_emoji_url)


@bp.route('/search_emojis', methods=['GET'])
@login_required
def search_emojis():
    # TODO: currently, when searching for emoji, it returns the entire reaction_menu
    #   the problem with this is reaction_menu includes the user search bar
    #   this means that whenever a search is registered, the bar is emptied
    #   You need to separate out the emoji_grid into a different html and create a route that only generates it
    search_string = request.args.get('search_string', "", type=str)

    post_id = request.args.get('post_id', 0, type=int)
    emojis = Emoji.query.all()
    result = [e for e in emojis if e.name.startswith(search_string)]
    result.sort(key=lambda x: x.name)
    result = result[:20]
    return render_template("_emoji_grid.html", emojis=result, starting_page=None, post_id=post_id,
                           next_emoji_url=None, prev_emoji_url=None)


@bp.route('/quote/<post_id>', methods=['GET', 'POST'])
@login_required
def quote_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        flash('post {} not found.'.format(post_id))
        return redirect(url_for('main.index'))

    thread = Post.query.filter_by(
        id=post_id).first().thread  # todo - user should be able to quote a post into any thread, not just the same
    # thread as the original post
    if thread is None:
        flash('thread for post {} not found.'.format(post_id))
        return redirect(url_for('main.index'))

    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user, thread=thread)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        anchor = 'p' + str(post.id)
        return redirect(
            url_for('main.thread', thread_id=thread.id, page=thread.last_page(), _anchor=anchor))
    elif request.method == 'GET':
        body = '[quote,name={},time={},post_id={}]{}[/quote]'.format(post.author.username, post.timestamp,
                                                                     post.id, post.body)
        form.post.data = body
    return render_template('make_post.html', title='Quote Post', form=form, thread=thread)


@bp.route('/edit_post/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        flash('post {} not found.'.format(post_id))
        return redirect(url_for('main.index'))

    if post.author.username is not current_user.username and current_user.mod_level < 2:
        flash('You are not the author of post {}.'.format(post_id))
        last_page_viewed, last_post_id = current_user.get_user_thread_position(thread=post.thread)
        return redirect(url_for('main.thread', thread_id=post.thread.id,
                                page=last_page_viewed))
    # TODO: add cancel button to PostForm
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.post.data
        post.format()  # updates post.body_formatted
        db.session.commit()
        flash('Your post has been edited')
        anchor = 'p' + str(post.id)
        return redirect(
            url_for('main.thread', thread_id=post.thread.id,
                    page=post.page(), _anchor=anchor))
    elif request.method == 'GET':
        form.post.data = post.body
    return render_template('make_post.html', title='Edit Your Post', form=form, thread=post.thread)


@bp.route('/delete_post/<post_id>')
@login_required
def delete_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        flash('post {} not found.'.format(post_id))
        return redirect(url_for('main.index'))

    if post.author.username is not current_user.username:
        flash('You are not the author of post {}.'.format(post_id))
        last_page_viewed, last_post_id = current_user.get_user_thread_position(thread=post.thread)
        return redirect(url_for('main.thread', thread_id=post.thread.id,
                                page=last_page_viewed))

    # info for redirect
    thread_id = post.thread.id
    try:
        previous_post = post.thread.posts.filter(Post.timestamp < post.timestamp)[-1]
        anchor = 'p' + str(previous_post.id)
    except IndexError:
        # exception occurs when there is no previous post
        anchor = ''

    db.session.delete(post)
    db.session.commit()

    return redirect(
        url_for('main.thread', thread_id=thread_id,
                page=post.page(), _anchor=anchor))


@bp.route('/post/<post_id>')
@login_required
def post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        flash('post {} not found.'.format(post_id))
        return '', 204
    anchor = 'p' + str(post.id)
    return redirect(url_for("main.thread", thread_id=post.thread.id,
                            page=post.page(), _anchor=anchor))


@bp.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title='Search', posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        db.session.commit()
        flash('Your message has been sent.')
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title='Send Message',
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages,
                           next_url=next_url, prev_url=prev_url)


def valid_extension(filepath):
    allowed_extensions = ("gif", "png", "jpg", "jpeg", "ico", "bmp", "svg", "tif", "tiff")
    pattern = ".+[.](.+)"
    try:
        extension = re.match(pattern, filepath).groups()[0]
    except AttributeError:
        return False
    if extension not in allowed_extensions:
        return False
    return True


@bp.route('/emojis', methods=['GET', 'POST'])
@login_required
def emojis():
    if request.method == 'POST':
        images = request.files.getlist("images")
        for image in images:

            if len(Emoji.query.all()) > current_app.config['MAX_NUMBER_OF_EMOJIS']:
                return "Max emoji limit reached", 400

            filename = secure_filename(image.filename)

            if not valid_extension(filename):
                continue  # TODO: communicate back to client that image was skipped over

            # Save as unique filename
            retries = 0
            while retries < 999:
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], "emojis", filename)
                if not os.path.exists(filepath):
                    image.save(filepath)
                    break
                else:
                    pattern = r'(.+?)' + '({})*'.format(retries-1) + r'(\.[^.\\/:*?"<>|\r\n]+$)'
                    match = re.match(pattern, filename)
                    filename = match.groups()[0] + str(retries) + match.groups()[2]
                    retries += 1

            if os.stat(filepath).st_size > current_app.config['MAX_EMOJI_SIZE']:
                os.remove(filepath)
                continue  # TODO: communicate back to client that image was skipped over

            # rel_path is like "app/static/images/emoji/filename.jpg"
            # rel_static_path is like "images/emoji/filename.jpg"
            # the first is needed for file-saving. The second is needed for rendering on the webpage
            rel_path = os.path.relpath(filepath, os.getcwd())
            rel_static_path = os.path.relpath(filepath, os.path.join(os.getcwd(), "app", "static"))
            rel_static_path = rel_static_path.replace("\\", "/")

            # find a first name to based on id
            try:
                total_emojis = len(Emoji.query.all())
            except:
                total_emojis = 0
            if total_emojis > 0:
                emoji_id = db.session.query(func.max(Emoji.id)).first()[0] + 1
            else:
                emoji_id = 1

            retries = 0
            while retries < current_app.config['MAX_NUMBER_OF_EMOJIS']:
                emoji_name = "emoji_" + str(emoji_id)
                emoji = Emoji(name=emoji_name, file_path=rel_static_path)
                try:
                    db.session.add(emoji)
                    db.session.commit()
                    break
                except IntegrityError:
                    db.session.rollback() #  db.session will remain broken after a failed commit() unless this is called
                    emoji_id += 1
                    retries += 1
        return redirect(url_for("main.emojis"))

    emojis = Emoji.query.all()
    return render_template("emojis.html", emojis=emojis, max_emoji_size=current_app.config['MAX_EMOJI_SIZE'])


@bp.route('/delete_emoji/<emoji_id>')
@login_required
def delete_emoji(emoji_id):
    emoji = Emoji.query.filter_by(id=emoji_id).first()
    if emoji:
        db.session.delete(emoji)
        db.session.commit()
    return redirect(url_for('main.emojis'))


@bp.route('/rename_emoji', methods=["POST"])
@login_required
def rename_emoji():
    emoji_id = request.form['emoji_id']
    new_name = request.form['new_name']
    emoji = Emoji.query.filter_by(id=emoji_id).first()
    if emoji:
        emoji.name = new_name
        db.session.commit()
    return "", 204


# TODO: does this really need both get and post?
@bp.route('/reactions', methods=['GET', 'POST'])
@login_required
def reactions():
    post = Post.query.filter_by(id=request.form['post_id']).first()
    emoji = Emoji.query.filter_by(name=request.form['reaction_type']).first()
    if post and emoji:
        if not PostReaction.query.filter_by(post=post, emoji=emoji, user=current_user).first():
            reaction = PostReaction(post=post, emoji=emoji, user=current_user)
            db.session.add(reaction)
            db.session.commit()

    reactions = []
    if post:
        # [reactions.append(r.emoji.name) for r in post.reactions]
        reactions = post.reactions
    return render_template('_reactions.html', reactions=reactions)