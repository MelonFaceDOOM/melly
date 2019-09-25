from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer


@parametrized
def require_mod_level(func, minimum):
    @wraps(func)
    def aux(*xs, **kws):
        if current_user.mod_level < minimum:
            flash("Your mod level is too low ({})".format(current_user.mod_level))
            return redirect(url_for("main.index"))
        return func(*xs, **kws)
    return aux


