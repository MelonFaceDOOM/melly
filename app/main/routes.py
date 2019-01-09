from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import current_user, login_required
from app import db
from app.main.forms import EditProfileForm, PostForm, CreateCategoryForm, CreateThreadForm, SearchForm
from app.models import User, Post, Thread, Category, User_Thread_Position
from app.main import bp


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
def create_thread(category_id):  # todo - update to include an initial post?
    category = Category.query.filter_by(id=category_id).first()
    if category is None:
        flash('category {} not found.'.format(category_id))
        return redirect(url_for('main.index'))

    form = CreateThreadForm(category.title)
    if form.validate_on_submit():
        thread = Thread(title=form.title.data, author=current_user, category=category)
        db.session.add(thread)
        db.session.commit()
        flash('Your thread {} has been created! Make a first post!'.format(form.title.data))
        return redirect(url_for('main.thread', thread_id=thread.id))
    return render_template('create_thread.html', title='Create a new thread',
                           category_id=category_id, form=form)


@bp.route('/edit_thread/<thread_id>', methods=['GET', 'POST'])
@login_required
def edit_thread(thread_id):
    # todo - add ability to move category to the form
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
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')

        return redirect(
            url_for('main.thread', thread_id=thread_id, page=thread.last_page()))  # todo add new-post anchor

    # if page is not specified, find the user's last post and redirect to it.
    page = request.args.get('page', None, type=int)
    if page:
        pass
    else:
        last_page_viewed, last_post_id = current_user.current_thread_position(thread_id=thread_id)
        page = last_page_viewed if last_page_viewed else 1
        anchor = 'p' + str(last_post_id) if last_post_id else None
        return redirect(
            url_for('main.thread', thread_id=thread_id, page=page, _anchor=anchor))

    page = request.args.get('page', 1, type=int)
    posts = thread.posts.order_by(Post.timestamp.asc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.thread', thread_id=thread_id,
                       page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.thread', thread_id=thread_id,
                       page=posts.prev_num) \
        if posts.has_prev else None

    current_user.view_increment(thread_id=thread_id)
    last_post_viewed_id = posts.items[-1].id if posts.items else None
    current_user.update_last_post_viewed(thread_id=thread_id,last_post_viewed_id=last_post_viewed_id)

    return render_template('thread.html', title=thread.title, form=form,
                           posts=posts, next_url=next_url, thread=thread,
                           prev_url=prev_url)

@bp.route('/quote/<post_id>', methods=['GET', 'POST'])
@login_required
def quote_post(post_id):  # todo - change to a dedicated post page and just put the quote text in.
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
        return redirect(
            url_for('main.thread', thread_id=thread.id, page=thread.last_page()))
    elif request.method == 'GET':
        body = '[{}, {}: {}]'.format(post.author.username, post.timestamp, post.body)
        form.post.data = body
    return render_template('make_post.html', title='Quote Post', form=form, thread=thread)

@bp.route('/edit_post/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if post is None:
        flash('post {} not found.'.format(post_id))
        return redirect(url_for('main.index'))
        
    if post.author.username is not current_user.username:
        flash('You are not the author of post {}.'.format(post_id))
        return redirect(url_for('main.thread', thread_id=post.thread.id,
                                page=current_user.last_page_viewed(post.thread.id)))

    form = PostForm()
    if form.validate_on_submit():
        post.body = form.post.data
        db.session.commit()
        flash('Your post has been edited')
        return redirect(
            url_for('main.thread', thread_id=post.thread.id, page=post.thread.last_page())) # todo - jump to post instead of last page
    elif request.method == 'GET':
        form.post.data = post.body
    return render_template('make_post.html', title='Edit Your Post', form=form, thread=post.thread)
    
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