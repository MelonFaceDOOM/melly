from app import create_app, db
from app.models import User, Post, Thread, Category, User_Thread_Position

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post, 'Thread': Thread, 'Category': Category, 'User_Thread_Position': User_Thread_Position}