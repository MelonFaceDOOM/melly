from app import create_app, db
from app.models import User, Post, Thread, Category, UserThreadMetadata, Message, Notification, PostReaction, Emoji

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 'User': User, 'Post': Post, 'Thread': Thread, 'Category': Category,
        'UserThreadMetadata': UserThreadMetadata, 'Message': Message, 'Notification': Notification,
        'PostReactions': PostReaction, 'Emoji': Emoji
    }
