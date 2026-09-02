import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore

app = Flask(__name__)
app.secret_key = "sameh_sanitary_secure_key"

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
    categories = [doc.to_dict() | {'id': doc.id} for doc in db.collection('categories').stream()]
    products = [doc.to_dict() | {'id': doc.id} for doc in db.collection('products').stream()]
    invoices = [doc.to_dict() | {'id': doc.id} for doc in db.collection('invoices').order_by('created_at', direction=firestore.Query.DESCENDING).stream()]
    expenses = [doc.to_dict() | {'id': doc.id} for doc in db.collection('expenses').stream()]
    suppliers = [doc.to_dict() | {'id': doc.id} for doc in db.collection('suppliers').stream()]
    customers = [doc.to_dict() | {'id': doc.id} for doc in db.collection('customers').stream()]
    returns = [doc.to_dict() | {'id': doc.id} for doc in db.collection('returns').stream()]
    wastes = [doc.to_dict() | {'id': doc.id} for doc in db.collection('wastes').stream()]

    total_revenue = sum(float(inv.get('total_amount', 0)) for inv in invoices)
    total_expenses = sum(float(exp.get('amount', 0)) for exp in expenses)
    total_cost = sum(float(item.get('quantity', 0)) * float(item.get('cost_price', 0)) for inv in invoices for item in inv.get('items', []))
    net_profit = total_revenue - total_cost - total_expenses

    return render_template(
        'index.html', 
        categories=categories, products=products, invoices=invoices,
        expenses=expenses, suppliers=suppliers, customers=customers,
        returns=returns, wastes=wastes, net_profit=net_profit,
        is_admin=session.get('is_admin', False)
    )

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('username') == "akram" and request.form.get('password') == "301020":
        session['is_admin'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "الرقم السري غير صحيح"})

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))

@app.route('/api/products', methods=['POST'])
def add_product():
    if not session.get('is_admin'): return redirect(url_for('home'))
    image_path = "/static/uploads/default.png"
    if 'image' in request.files:
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_path = f"/static/uploads/{filename}"

    db.collection('products').add({
        'name': request.form.get('name'),
        'category_id': request.form.get('category_id'),
        'cost_price': float(request.form.get('cost_price', 0)),
        'selling_price': float(request.form.get('selling_price', 0)),
        'stock': int(request.form.get('stock', 0)),
        'image_url': image_path
    })
    return redirect(url_for('home'))

@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    data = request.json
    items = data.get('items', [])
    processed_items = []
    
    for item in items:
        p_ref = db.collection('products').document(item['product_id'])
        p_doc = p_ref.get()
        if p_doc.exists:
            p_data = p_doc.to_dict()
            new_stock = max(0, int(p_data.get('stock', 0)) - int(item['quantity']))
            p_ref.update({'stock': new_stock})
            processed_items.append({
                'product_id': item['product_id'],
                'product_name': p_data.get('name'),
                'quantity': item['quantity'],
                'price': item['price'],
                'cost_price': p_data.get('cost_price', 0)
            })

    _, inv_ref = db.collection('invoices').add({
        'customer_name': data.get('customer_name'),
        'customer_phone': data.get('customer_phone'),
        'total_amount': data.get('total_amount', 0),
        'items': processed_items,
        'created_at': datetime.utcnow().isoformat()
    })
    return jsonify({"success": True, "invoice_id": inv_ref.id})

@app.route('/api/delete_item', methods=['POST'])
def delete_item():
    data = request.json
    if data.get('pin') != "301020":
        return jsonify({"success": False, "message": "الرقم السري للحذف خاطئ"})
    
    col_name = data.get('collection')
    item_id = data.get('id')
    db.collection(col_name).document(item_id).delete()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)