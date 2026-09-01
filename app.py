import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "sameh_pipe_factory_secure_key"

# رابط Supabase وكلمة السر المدمجة
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:samehm300%40yahoo.com@db.zcieombnpgsoisidnnmg.supabase.co:5432/postgres"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    cost_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(300), default='/static/uploads/default.png')

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    total_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True)

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    notes = db.Column(db.Text)

with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    categories = Category.query.all()
    products = Product.query.all()
    invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
    expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    suppliers = Supplier.query.all()
    
    total_revenue = sum(inv.total_amount for inv in invoices)
    total_cost = sum(sum(item.quantity * item.product.cost_price for item in inv.items if item.product) for inv in invoices)
    net_profit = total_revenue - total_cost - sum(exp.amount for exp in expenses)

    return render_template(
        'index.html', 
        categories=categories, 
        products=products, 
        invoices=invoices,
        expenses=expenses,
        suppliers=suppliers,
        net_profit=net_profit,
        is_admin=session.get('is_admin', False)
    )

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username == "akram" and password == "301020":
        session['is_admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "اسم المستخدم أو كلمة المرور غير صحيحة"})

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))

@app.route('/api/categories', methods=['POST'])
def add_category():
    name = request.json.get('name')
    if name:
        cat = Category(name=name)
        db.session.add(cat)
        db.session.commit()
        return jsonify({"success": True, "id": cat.id, "name": cat.name})
    return jsonify({"success": False})

@app.route('/api/products', methods=['POST'])
def add_product():
    name = request.form.get('name')
    category_id = request.form.get('category_id')
    cost_price = float(request.form.get('cost_price', 0))
    selling_price = float(request.form.get('selling_price', 0))
    stock = int(request.form.get('stock', 0))
    
    image_path = "/static/uploads/default.png"
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"/static/uploads/{filename}"

    product = Product(
        name=name, 
        category_id=category_id, 
        cost_price=cost_price, 
        selling_price=selling_price, 
        stock=stock, 
        image_url=image_path
    )
    db.session.add(product)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    data = request.json
    customer_name = data.get('customer_name')
    customer_phone = data.get('customer_phone')
    items = data.get('items', [])
    total_amount = data.get('total_amount', 0)

    invoice = Invoice(customer_name=customer_name, customer_phone=customer_phone, total_amount=total_amount)
    db.session.add(invoice)
    db.session.commit()

    for item in items:
        product = Product.query.get(item['product_id'])
        if product:
            product.stock = max(0, product.stock - item['quantity'])
            inv_item = InvoiceItem(
                invoice_id=invoice.id, 
                product_id=product.id, 
                quantity=item['quantity'], 
                price=item['price']
            )
            db.session.add(inv_item)

    db.session.commit()
    return jsonify({"success": True, "invoice_id": invoice.id})

if __name__ == '__main__':
    app.run(debug=True, port=5000)