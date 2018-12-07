from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import current_user, login_required
from app import db
from app.main.forms import EditProfileForm, PostForm, CreateCategoryForm, CreateThreadForm
from app.models import User, Post, Thread, Category
from app.main import bp


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    categories = Category.query.order_by(Category.timestamp.desc()).paginate(
        page, current_app.config['CATEGORIES_PER_PAGE'], False)
    next_url = url_for('main.index', page=categories.next_num) \
        if categories.has_next else None
    prev_url = url_for('main.index', page=categories.prev_num) \
        if categories.has_prev else None
    return render_template('index.html', title='Home',
                           categories=categories.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('explore.html', title='Explore',
                           posts=posts.items, next_url=next_url,
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


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('main.user', username=username))
    
    
@bp.route('/create_category', methods=['GET', 'POST'])
@login_required
def create_category():
    form = CreateCategoryForm()
    if form.validate_on_submit():
        category = Category(title=form.title.data, author=current_user)
        db.session.add(category)
        db.session.commit()
        flash('Your category, {} has been created! Make a first thread!'.format(form.title.data))
        return redirect(url_for('main.category',category_title=form.title.data)) #update with url for new category?
    return render_template('create_category.html', title='Create Category',
                           form=form)

@bp.route('/<category_title>')
@login_required
def category(category_title):
    category = Category.query.filter_by(title=category_title).first()
    if category is None:
        flash('category {} not found.'.format(category_title))
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    threads = Thread.query.join(Category).filter(Category.title == category_title).paginate(
        page, current_app.config['THREADS_PER_PAGE'], False)
    next_url = url_for('main.category', page=threads.next_num, category_title=category_title) \
        if threads.has_next else None
    prev_url = url_for('main.category', page=threads.prev_num, category_title=category_title) \
        if threads.has_prev else None
    return render_template('category.html', title=category_title, category_title=category_title, threads=threads.items,
                           next_url=next_url, prev_url=prev_url)

@bp.route('/<category_title>/create_thread', methods=['GET', 'POST'])
@login_required                           
def create_thread(category_title):#todo - update to include an initial post?
    category = Category.query.filter_by(title=category_title).first()
    if category is None:
        flash('category {} not found.'.format(category_title))
        return redirect(url_for('main.index'))

    form = CreateThreadForm(category_title)
    if form.validate_on_submit():
        thread = Thread(title=form.title.data, author=current_user,category=category)
        db.session.add(thread)
        db.session.commit()
        flash('Your thread {} has been created! Make a first post!'.format(form.title.data))
        return redirect(url_for('main.thread',category_title=category_title,thread_title=form.title.data))
    return render_template('create_thread.html', title='Create thread',
                           category_title=category_title, form=form)

@bp.route('/<category_title>/<thread_title>', methods=['GET', 'POST'])
@login_required 
def thread(category_title,thread_title):

    thread = Thread.query.join(Category).filter(Category.title==category_title,
                                                Thread.title==thread_title).first()
    if thread is None:
        flash('thread "{}" not found in {}.'.format(thread_title,category_title))
        return redirect(url_for('main.index'))
        
    category = Category.query.filter_by(title=category_title).first()
    if category is None:
        flash('category {} not found.'.format(category_title))
        return redirect(url_for('main.index'))
        
    form = PostForm()
    page = request.args.get('page', 1, type=int)
    posts = thread.posts.paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.thread', category_title=category_title, thread_title=thread_title,
                       page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.thread', category_title=category_title, thread_title=thread_title,
                       page=posts.prev_num) \
        if posts.has_prev else None

    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user,thread=thread)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        
        last_page = int(posts.total/current_app.config['POSTS_PER_PAGE']+1)
        return redirect(url_for('main.thread',category_title=category_title,thread_title=thread_title,page=last_page))
        
    return render_template('thread.html', title=thread_title, form=form,
                           posts=posts.items, next_url=next_url, category=category,
                           prev_url=prev_url)
    