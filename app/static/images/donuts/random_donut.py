import os
import random

def random_donut():
    # TODO: test with folder empty or not existent

    rel_folder_path = os.path.relpath(os.path.dirname(__file__), os.getcwd())
    rel_folder_path = os.path.join(rel_folder_path, "svg")
    random_donut = os.path.join(rel_folder_path, random.choice(os.listdir(rel_folder_path)))
    print(random_donut)
    # return relative paths starting from the static folder
    # these will later be called using "url_for('static', path_to_avatar)"
    rel_static_path = os.path.relpath(os.path.abspath(random_donut), os.path.join(os.getcwd(), "app", "static"))
    rel_static_path = rel_static_path.replace("\\", "/")

    print(rel_static_path)
    return rel_static_path


# TODO: fix following:
#  - "010-doughnut.svg" white centre
#  - "089-donut-75.svg" purple centre
#  - "083-donut-69.svg" white centre
#  - "096-donut-79.svg" purple centre