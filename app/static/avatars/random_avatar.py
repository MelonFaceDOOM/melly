from PIL import Image
from numpy.random import randint
import os

def random_avatar():
    images = []
    for i in range(1, 9):
        images.append(r"face"+str(i)+".jpg")

    rand_panel = randint(0, 7)
    rand_left = randint(0, 36)
    rand_top = randint(0, 7)

    filename = "{}, {}, {}.bmp".format(rand_panel+1, rand_left+1, rand_top+1)
    rel_folder_path = os.path.relpath(os.path.dirname(__file__), os.getcwd())
    rel_save_path = os.path.join(rel_folder_path, "user avatars", filename)

    if os.path.isfile(rel_save_path):
        return rel_save_path

    source_panel = Image.open(os.path.join(rel_folder_path, images[rand_panel]))
    width, height = source_panel.size
    square_height = height/8
    square_width = width/37

    left = square_width * rand_left
    top = square_height * rand_top
    right = left + square_width
    bottom = top + square_height

    cropped_image = source_panel.crop((left, top, right, bottom))
    cropped_image.save(rel_save_path)

    # return relative paths starting from the static folder
    # these will later be called using "url_for('static', path_to_avatar)"
    rel_static_path = os.path.relpath(os.path.abspath(rel_save_path), os.path.join(os.getcwd(), "app", "static"))
    rel_static_path = rel_static_path.replace("\\", "/")
    return rel_static_path