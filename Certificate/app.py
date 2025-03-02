from flask import Flask, render_template, request, send_file, redirect, url_for
from flask_wtf import FlaskForm
from datetime import datetime  # Import datetime for default issue date
from wtforms import StringField, DateField, FileField, SubmitField
from wtforms.validators import DataRequired
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.graphics.shapes import Drawing, Circle, String
from PIL import Image, ImageDraw
from reportlab.lib import colors
import random
import barcode
from barcode.writer import ImageWriter
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Form for user input


def generate_barcode(code, output_folder):
    """
    Generate a barcode for the given code and save it as an image.
    """
    # Create a Code39 barcode
    barcode_class = barcode.get_barcode_class('code39')
    barcode_image = barcode_class(code, writer=ImageWriter())

    # Save the barcode as an image
    barcode_path = os.path.join(output_folder, 'barcode')
    barcode_image.save(barcode_path)

    return f"{barcode_path}.png"

class CertificateForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired()])
    date_of_birth = DateField('Date of Birth', format='%Y-%m-%d', validators=[DataRequired()])
    title = StringField('Title Assigned', validators=[DataRequired()])
    issue_date = DateField('Issue Date', format='%Y-%m-%d', default=datetime.now, validators=[DataRequired()])
    issued_by_name = StringField('Issued By Name', validators=[DataRequired()])
    issued_by_position = StringField('Issued By Position', validators=[DataRequired()])
    background_image = FileField('Upload Background Image', validators=[DataRequired()])
    photo = FileField('Upload Photo', validators=[DataRequired()])
    signature = FileField('Upload Signature', validators=[DataRequired()])  # New field
    submit = SubmitField('Generate Certificate')

# Home page with form
@app.route('/', methods=['GET', 'POST'])
def index():
    form = CertificateForm()
    if form.validate_on_submit():
        # Save uploaded files
        background_image = form.background_image.data
        photo = form.photo.data
        signature = form.signature.data  # New: Save signature
        background_path = os.path.join(app.config['UPLOAD_FOLDER'], 'background.jpg')
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photo.jpg')
        signature_path = os.path.join(app.config['UPLOAD_FOLDER'], 'signature.png')  # New: Signature path
        background_image.save(background_path)
        photo.save(photo_path)
        signature.save(signature_path)  # New: Save signature

        # Redirect to certificate preview
        return redirect(url_for('preview_certificate',
                                full_name=form.full_name.data,
                                date_of_birth=form.date_of_birth.data.strftime('%d-%m-%Y'),
                                title=form.title.data,
                                issue_date=form.issue_date.data.strftime('%d-%m-%Y'),
                                issued_by_name=form.issued_by_name.data,
                                issued_by_position=form.issued_by_position.data))
    return render_template('index.html', form=form)

# Certificate preview
@app.route('/preview')
def preview_certificate():
    full_name = request.args.get('full_name')
    date_of_birth = request.args.get('date_of_birth')
    title = request.args.get('title')
    issue_date = request.args.get('issue_date')
    issued_by_name = request.args.get('issued_by_name')
    issued_by_position = request.args.get('issued_by_position')
    return render_template('certificate.html',
                           full_name=full_name,
                           date_of_birth=date_of_birth,
                           title=title,
                           issue_date=issue_date,
                           issued_by_name=issued_by_name,
                           issued_by_position=issued_by_position)
    
    
def create_circular_mask(image_path, output_path, size):
    """
    Create a circular mask for the photo and save it as a new image.
    """
    # Open the image
    image = Image.open(image_path).convert("RGBA")
    image = image.resize((size, size), Image.Resampling.LANCZOS)  # Updated here

    # Create a circular mask
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    # Apply the mask to the image
    result = Image.new("RGBA", (size, size))
    result.paste(image, (0, 0), mask=mask)

    # Save the result
    result.save(output_path)
    
# Generate and download PDF
@app.route('/download')
def download_certificate():
    full_name = request.args.get('full_name')
    date_of_birth = request.args.get('date_of_birth')
    title = request.args.get('title')
    issue_date = request.args.get('issue_date')
    issued_by_name = request.args.get('issued_by_name')
    issued_by_position = request.args.get('issued_by_position')

    # Create PDF
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], 'certificate.pdf')
    c = canvas.Canvas(pdf_path, pagesize=A4)
    width, height = A4

    # Add background image
    background_path = os.path.join(app.config['UPLOAD_FOLDER'], 'background.jpg')
    c.drawImage(background_path, 0, 0, width=width, height=height)

    # Generate a random 6-digit code starting with "KDO-BMG"
    random_code = f"KDO-BMG-{random.randint(100000, 999999)}"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Generate barcode
    barcode_path = generate_barcode(random_code, app.config['UPLOAD_FOLDER'])

    # Add code, barcode, and timestamp to the top-right corner
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 50, height - 50, f"Code: {random_code}")
    c.drawRightString(width - 50, height - 70, f"Generated: {timestamp}")

    # Add barcode
    c.drawImage(barcode_path, width - 150, height - 120, width=100, height=50)

    # Add photo with circular mask and white border
    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photo.jpg')
    circular_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'circular_photo.png')

    # Calculate position for the photo
    photo_width = 150  # Width of the photo
    photo_height = 150  # Height of the photo
    photo_x = (width - photo_width) / 2  # Center horizontally
    photo_y = height * 0.7 - photo_height / 2  # Move up by 30% of A4 height

    # Create a circular mask for the photo
    create_circular_mask(photo_path, circular_photo_path, size=150)

    # Draw the circular photo with a white border
    c.drawImage(circular_photo_path, photo_x, photo_y, width=photo_width, height=photo_height, mask='auto')

    # Draw a white circle around the photo
    c.setStrokeColor(colors.white)
    c.setLineWidth(2)
    c.circle(photo_x + photo_width / 2, photo_y + photo_height / 2, photo_width / 2, stroke=1, fill=0)

    # Add certificate title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 400, "Certificate of Assignment")

    # Add user details
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 500, f"This certifies that")
    
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 530, f"{full_name}")
    
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 560, f"born on {date_of_birth}")
    c.drawCentredString(width / 2, height - 590, f"has been assigned as")
    
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 620, f"{title}")
    
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 640, f"Issued on: {issue_date}")

    # Add issued by details
    c.setFont("Helvetica", 14)
    c.drawString(400, 150, f"Issued By: {issued_by_name}")
    c.drawString(400, 130, f"Position: {issued_by_position}")

    # Add signature
    signature_path = os.path.join(app.config['UPLOAD_FOLDER'], 'signature.png')
    c.drawImage(signature_path, 400, 60, width=100, height=50)

    # Add footer
    c.setFont("Helvetica", 12)
    c.drawString(50, 50, "KHMER DEMOCRACY ORGANIZATION(KDO) INC.")
    c.drawString(50, 30, "6 Temple CT, Noble Park, Vic 3174")
    c.drawString(50, 20, "Email: hq@kdo.org.au | Phone: (+61)0395444950")
    c.drawString(50, 5, "Website: kdo.org.au")

    c.save()

    return send_file(pdf_path, as_attachment=True)