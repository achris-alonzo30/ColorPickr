from flask import Flask, render_template, redirect, request, url_for, flash, send_from_directory
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField, FileField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import os
import cv2
import random
import re  # Import the re module

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
csrf = CSRFProtect(app)


def is_hex_color(color):
    # Check if the color is in HEX format (#RRGGBB or #RGB)
    return bool(re.match(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$', color))


def is_rgb_color(color):
    # Check if the color is in RGB format (rgb(R, G, B) or rgba(R, G, B, A))
    return bool(re.match(r'^(rgb|rgba)\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*(,\s*\d*\s*)?\)$', color))


class ImageColorExtractForm(FlaskForm):
    number_options = [(4, '4'),
                      (5, '5'),
                      (6, '6'),
                      (7, '7'),
                      (8, '8'),
                      (9, '9'),
                      (10, '10'), ]
    colors = SelectField('Number of colors',
                         choices=number_options)
    color_code = SelectField('Color code', choices=['RGB Code', 'HEX Code'])
    image = FileField('Upload Image', validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/main', methods=['POST', 'GET'])
def main():
    form = ImageColorExtractForm()
    if form.validate_on_submit():
        number_of_colors = form.colors.data
        color_code = form.color_code.data

        if 'image' in request.files:
            image = request.files['image']
            if image:
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'])

                # Define the image_path after ensuring the folder exists
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

                try:
                    image.save(image_path)
                    flash('Image uploaded successfully', 'success')

                    # Pass the filename as a query parameter when redirecting
                    return redirect(url_for('image_extract', number_of_colors=number_of_colors, color_code=color_code,
                                            filename=filename))
                except Exception as e:
                    flash(f'Error saving the image: {str(e)}', 'danger')
            else:
                flash('No image uploaded', 'warning')
        else:
            flash('No image uploaded', 'warning')

    return render_template('main.html', form=form)


@app.route('/image_extract/<number_of_colors>/<color_code>', methods=['POST', 'GET'])
def image_extract(number_of_colors, color_code):
    filename = request.args.get('filename')

    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        # Open the image using Pillow
        with Image.open(image_path) as img:
            img.thumbnail((300, 300))
            img.save(image_path)  # Overwrite the original image with the resized one

        # Use OpenCV to analyze the image and extract color information
        image = cv2.imread(image_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # Convert image to RGB

        # Resize the image for faster processing if needed
        # image = cv2.resize(image, (300, 300))

        # Extract color information
        if color_code == 'RGB Code':
            pixels = np.reshape(image, (-1, 3))  # Reshape to (N, 3)
        elif color_code == 'HEX Code':
            # Convert the RGB values to HEX
            hex_pixels = ['#{:02x}{:02x}{:02x}'.format(r, g, b) for r, g, b in image.reshape(-1, 3)]
        else:
            flash('Invalid color code', 'danger')
            return redirect(url_for('main'))

        if color_code == 'RGB Code':
            unique_colors = np.unique(pixels, axis=0)  # Find unique colors
            unique_colors = unique_colors.tolist()
        else:
            unique_colors = list(set(hex_pixels))

        print(unique_colors)
        random.shuffle(unique_colors)

        # Extract the specified number of unique colors
        if len(unique_colors) < int(number_of_colors):
            flash('Not enough unique colors found', 'warning')
        else:
            unique_colors = unique_colors[:int(number_of_colors)]  # Take the top N unique colors

        # Define image_url within the try block
        image_url = url_for('uploaded_file', filename=filename)

        # Display the extracted color information on the image_extract.html template
        return render_template('image_extract.html', number_of_colors=number_of_colors, color_code=color_code,
                               image_url=image_url, unique_colors=unique_colors)

    except Exception as e:
        flash(f'Error processing the image: {str(e)}', 'danger')
        return redirect(url_for('main'))


# Add a route to serve the uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)
