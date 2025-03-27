from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from functools import wraps
import os
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key

# Configure upload folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Temporary storage for products (replace with database in production)
products = {
    'pending': [],
    'approved': []
}

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/reg')
def reg_view():
    return render_template("reg.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('n')
        password = request.form.get('c')
        
        if password == "admin":
            session['user'] = username
            if username == "seller":
                return redirect(url_for('seller'))
            elif username == "buyer":
                return redirect(url_for('buyer'))
            elif username == "manager":
                return redirect(url_for('manager'))
        return render_template("log.html")            
    return render_template('log.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/seller')
def seller():
    return render_template('seller.html', products=products)

@app.route('/buyer')
def buyer():
    return render_template('buyer.html', products=products['approved'])

@app.route('/product/<int:product_id>')
def product_details(product_id):
    # Search in all product lists
    for product in products['pending']:
        if product['id'] == product_id:
            return render_template('product_details.html', product=product, products=products)
    
    for product in products['approved']:
        if product['id'] == product_id:
            return render_template('product_details.html', product=product, products=products)
    
    for product in products.get('rejected', []):
        if product['id'] == product_id:
            return render_template('product_details.html', product=product, products=products)
    
    return redirect(url_for('buyer'))

@app.route('/add_product', methods=['POST'])
def add_product():
    try:
        # Handle image upload
        image = request.files.get('image')
        image_path = None
        
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            # Add timestamp to filename to make it unique
            filename = f"{int(time.time())}_{filename}"
            # Save the file
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # Store the relative path for the template
            image_path = f"uploads/{filename}"

        # Get other product data
        data = request.form
        new_product = {
            'id': len(products['pending']) + 1,
            'name': data.get('name'),
            'price': data.get('price'),
            'description': data.get('description'),
            'image': image_path
        }
        products['pending'].append(new_product)
        return jsonify({'success': True, 'product': new_product})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        # Get the source of the delete request
        source = request.args.get('source', '')
        
        if source == 'rejected':
            # Only search in rejected products
            for product in products.get('rejected', []):
                if product['id'] == product_id:
                    # Delete the image file if it exists
                    if product.get('image'):
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'].split('/')[-1])
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    products['rejected'].remove(product)
                    return jsonify({'success': True})
        else:
            # Search in pending and approved products
            for product in products['pending']:
                if product['id'] == product_id:
                    if product.get('image'):
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'].split('/')[-1])
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    products['pending'].remove(product)
                    return jsonify({'success': True})
            
            for product in products['approved']:
                if product['id'] == product_id:
                    if product.get('image'):
                        image_path = os.path.join(app.config['UPLOAD_FOLDER'], product['image'].split('/')[-1])
                        if os.path.exists(image_path):
                            os.remove(image_path)
                    products['approved'].remove(product)
                    return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Product not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/manager')
def manager():
    return render_template('manager.html', products=products)

@app.route('/approve_product/<int:product_id>', methods=['POST'])
def approve_product(product_id):
    try:
        # Get grade from request
        data = request.get_json()
        grade = data.get('grade')
        
        if not grade:
            return jsonify({'success': False, 'error': 'Grade is required'})
            
        # Find the product in pending products
        for product in products['pending']:
            if product['id'] == product_id:
                # Add grade to product
                product['grade'] = grade
                # Move to approved products
                products['approved'].append(product)
                products['pending'].remove(product)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reject_product/<int:product_id>', methods=['POST'])
def reject_product(product_id):
    try:
        # Find the product in pending products
        for product in products['pending']:
            if product['id'] == product_id:
                # Move to rejected products
                if 'rejected' not in products:
                    products['rejected'] = []
                products['rejected'].append(product)
                products['pending'].remove(product)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reapply_product/<int:product_id>', methods=['POST'])
def reapply_product(product_id):
    try:
        # Find the product in rejected products
        for product in products.get('rejected', []):
            if product['id'] == product_id:
                # Move to pending products
                products['pending'].append(product)
                products['rejected'].remove(product)
                return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Product not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5500)
