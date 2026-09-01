import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
app.secret_key = "sameh_pipe_factory_secure_key"

# تهيئة اتصال Firebase باستخدام ملف الاعتمادات
cred = credentials.Certificate("firebase_key.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    # جلب الأقسام من Firestore
    categories_ref = db.collection('categories').stream()
    categories = []
    for doc in categories_ref:
        c_data = doc.to_dict()
        c_data['id'] = doc.id
        categories.append(c_data)

    # جلب المنتجات من Firestore
    products_ref = db.collection('products').stream()
    products = []
    for doc in products_ref:
        p_data = doc.to_dict()
        p_data['id'] = doc.id
        products.append(p_data)

    # جلب الفواتير وترتيبها
    invoices_ref = db.collection('invoices').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    invoices = []
    total_revenue = 0
    for doc in invoices_ref:
        inv_data = doc.to_dict()
        inv_data['id'] = doc.id
        if isinstance(inv_data.get('created_at'), str):
            try:
                inv_data['created_at'] = datetime.fromisoformat(inv_data['created_at'])
            except:
                inv_data['created_at'] = datetime.utcnow()
        invoices.append(inv_data)
        total_revenue += float(inv_data.get('total_amount', 0))

    # جلب المصروفات
    expenses_ref = db.collection('expenses').stream()
    expenses = []
    total_expenses = 0
    for doc in expenses_ref:
        exp_data = doc.to_dict()
        exp_data['id'] = doc.id
        expenses.append(exp_data)
        total_expenses += float(exp_data.get('amount', 0))

    # جلب الموردين
    suppliers_ref = db.collection('suppliers').stream()
    suppliers = []
    for doc in suppliers_ref:
        s_data = doc.to_dict()
        s_data['id'] = doc.id
        suppliers.append(s_data)

    total_cost = 0
    for inv in invoices:
        for item in inv.get('items', []):
            total_cost += float(item.get('quantity', 0)) * float(item.get('cost_price', 0))

    net_profit = total_revenue - total_cost - total_expenses

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
        doc_ref = db.collection('categories').document()
        doc_ref.set({'name': name})
        return jsonify({"success": True, "id": doc_ref.id, "name": name})
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

    product_data = {
        'name': name,
        'category_id': category_id,
        'cost_price': cost_price,
        'selling_price': selling_price,
        'stock': stock,
        'image_url': image_path
    }
    
    db.collection('products').add(product_data)
    return redirect(url_for('home'))

@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    data = request.json
    customer_name = data.get('customer_name')
    customer_phone = data.get('customer_phone')
    items = data.get('items', [])
    total_amount = data.get('total_amount', 0)

    processed_items = []
    for item in items:
        p_ref = db.collection('products').document(item['product_id'])
        p_doc = p_ref.get()
        if p_doc.exists:
            p_data = p_doc.to_dict()
            current_stock = int(p_data.get('stock', 0))
            new_stock = max(0, current_stock - int(item['quantity']))
            p_ref.update({'stock': new_stock})
            
            processed_items.append({
                'product_id': item['product_id'],
                'product_name': p_data.get('name'),
                'quantity': item['quantity'],
                'price': item['price'],
                'cost_price': p_data.get('cost_price', 0)
            })

    invoice_data = {
        'customer_name': customer_name,
        'customer_phone': customer_phone,
        'total_amount': total_amount,
        'items': processed_items,
        'created_at': datetime.utcnow().isoformat()
    }

    _, inv_ref = db.collection('invoices').add(invoice_data)
    return jsonify({"success": True, "invoice_id": inv_ref.id})

if __name__ == '__main__':
    app.run(debug=True, port=5000)