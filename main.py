from pyscript import window, document
from pyodide.ffi import create_proxy
import json
from datetime import datetime
import random # Thêm random để tạo ID không trùng lặp

products = []
orders = []
deleted_products = []

current_modal_index = -1
current_modal_action = ""
current_return_order_id = "" 

def load_data():
    global products, orders, deleted_products
    orders_data = window.localStorage.getItem('pyscript_orders_db')
    orders = json.loads(orders_data) if orders_data else []
    
    deleted_data = window.localStorage.getItem('pyscript_deleted_db')
    deleted_products = json.loads(deleted_data) if deleted_data else []
    
    data = window.localStorage.getItem('pyscript_products_db')
    if data:
        products = json.loads(data)
    else:
        # Dữ liệu mặc định nếu lần đầu chạy ứng dụng
        products = [
            {"name": "Điện thoại iPhone 15 Pro Max 256GB", "price": 29500000, "quantity": 14},
            {"name": "Máy tính bảng iPad Air 5 M1 Wifi", "price": 14200000, "quantity": 8},
            {"name": "Laptop ASUS ROG Strix G16 Gaming", "price": 34800000, "quantity": 5}
        ]
        save_data()

def save_data():
    window.localStorage.setItem('pyscript_products_db', json.dumps(products))
    window.localStorage.setItem('pyscript_orders_db', json.dumps(orders))
    window.localStorage.setItem('pyscript_deleted_db', json.dumps(deleted_products))

def format_currency(v):
    return f"{int(v):,}".replace(",", ".") + " đ"

def render_tables():
    tbody = document.getElementById("product-tbody")
    if not tbody: return
    tbody.innerHTML = ""
    search_val = document.getElementById("search-input").value.strip().lower() if document.getElementById("search-input") else ""
    
    total_qty = 0
    total_val = 0
    
    for idx, p in enumerate(products):
        if search_val and search_val not in p['name'].lower(): continue
        total_qty += int(p['quantity'])
        total_val += float(p['price']) * int(p['quantity'])
        
        tr = document.createElement("tr")
        tr.innerHTML = f"""
            <td class='fw-semibold'>{p['name']}</td>
            <td class='text-blue fw-bold'>{format_currency(p['price'])}</td>
            <td><span class='badge bg-success'>{p['quantity']} cái</span></td>
            <td>
                <div class="action-buttons-row">
                    <button class="btn-gcp-serve" onclick="window.openQuantityModal({idx}, 'import')"><i class='fa-solid fa-square-plus'></i> Nhập</button>
                    <button class="btn-gcp-pay" onclick="window.openQuantityModal({idx}, 'export')"><i class='fa-solid fa-cart-shopping'></i> Xuất Bán</button>
                    <button class="btn-gcp-cancel" onclick="window.deleteProduct({idx})"><i class='fa-solid fa-trash-can'></i> Xóa</button>
                </div>
            </td>
        """
        tbody.appendChild(tr)
        
    if document.getElementById("total-products-count"):
        document.getElementById("total-products-count").innerText = f"{len(products)} dòng"
    if document.getElementById("total-products-qty"):
        document.getElementById("total-products-qty").innerText = f"{total_qty} cái"
    
    real_revenue = sum(float(o.get('val', 0)) for o in orders if o.get('type') == "Xuất kho" and o.get('status') != 'refunded')
    if document.getElementById("total-products-value"):
        document.getElementById("total-products-value").innerText = format_currency(real_revenue)

def open_quantity_modal(index, action):
    global current_modal_index, current_modal_action
    current_modal_index = int(index)
    current_modal_action = action
    
    p = products[current_modal_index]
    title_text = f"Nhập Thêm Hàng - {p['name']}" if action == "import" else f"Xuất Kho Bán Lẻ - {p['name']}"
    
    document.getElementById("modal-title").innerText = title_text
    document.getElementById("modal-qty-input").value = ""
    
    btn = document.getElementById("modal-confirm-btn")
    btn.style.backgroundColor = "#10b981" if action == "import" else "#f59e0b"
    
    modal = document.getElementById("quantity-modal")
    if modal: modal.classList.add("open")

def confirm_quantity_modal(event=None):
    global current_modal_index, current_modal_action
    # CHẶN RELOAD TRANG KHI SUBMIT MODAL KHO
    if event:
        event.preventDefault()
        
    input_element = document.getElementById("modal-qty-input")
    if not input_element or current_modal_index == -1: return
    
    val_str = input_element.value.strip()
    if not val_str: return
    try:
        qty_change = int(val_str)
        if qty_change <= 0: return
    except ValueError: return
    
    p = products[current_modal_index]
    now_str = datetime.now().strftime("%H:%M %d/%m/%y")
    
    rand_id = f"{datetime.now().strftime('%M%S')}{random.randint(10, 99)}"
    
    if current_modal_action == "import":
        p['quantity'] = int(p['quantity']) + qty_change
        orders.append({
            "time": now_str, "id": f"KK{rand_id}",
            "type": "Nhập kho", "name": p['name'], "qty": qty_change, "val": 0, "status": "done"
        })
    elif current_modal_action == "export":
        if int(p['quantity']) < qty_change:
            window.alert("Số lượng sản phẩm trong kho không đủ cung ứng!")
            return
        p['quantity'] = int(p['quantity']) - qty_change
        orders.append({
            "time": now_str, "id": f"DH{rand_id}", "type": "Xuất kho",
            "name": p['name'], "qty": qty_change, "val": float(p['price']) * qty_change,
            "status": "paid", "return_qty": qty_change, "p_name": p['name']
        })
        
    if p['quantity'] <= 0:
        products.pop(current_modal_index)
        
    document.getElementById("quantity-modal").classList.remove("open")
    current_modal_index = -1
    save_data()
    render_tables()
    render_orders_table()

def delete_product(index):
    idx = int(index)
    p = products.pop(idx)
    deleted_products.append({"name": p['name'], "price": p['price'], "quantity": p['quantity']})
    
    rand_id = f"{datetime.now().strftime('%M%S')}{random.randint(10, 99)}"
    orders.append({
        "time": datetime.now().strftime("%H:%M %d/%m/%y"), "id": f"KK{rand_id}",
        "type": "Xóa danh mục", "name": p['name'], "qty": p['quantity'], "val": 0, "status": "done"
    })
    save_data(); render_tables(); render_orders_table(); render_deleted_table()

def trigger_cancel_modal(order_id):
    global current_return_order_id
    current_return_order_id = order_id
    document.getElementById("cancel-modal-oid").textContent = order_id
    document.getElementById("cancel-reason-text").value = ""
    document.getElementById("modal-cancel-refund").classList.add("open")

def submit_cancel_request(event):
    global current_return_order_id, orders
    # CHẶN RELOAD TRANG KHI SUBMIT YÊU CẦU HỦY ĐƠN
    if event:
        event.preventDefault()
        
    if not current_return_order_id: return
    reason_raw = document.getElementById("cancel-reason-text").value.strip()
    reason_display = reason_raw if reason_raw else "Đổi ý không mua nữa"
    
    for o in orders:
        if o.get('id') == current_return_order_id:
            o['status'] = 'return_pending'
            o['return_reason'] = f"Hủy hoàn tiền: {reason_display}"
            break
            
    document.getElementById("modal-cancel-refund").classList.remove("open")
    current_return_order_id = "" 
    save_data(); render_orders_table()

def trigger_exchange_modal(order_id):
    global current_return_order_id
    current_return_order_id = order_id
    document.getElementById("exchange-modal-oid").textContent = order_id
    document.getElementById("exchange-reason-text").value = ""
    document.getElementById("modal-exchange-product").classList.add("open")

def submit_exchange_request(event):
    global current_return_order_id, orders
    # CHẶN RELOAD TRANG KHI SUBMIT YÊU CẦU ĐỔI HÀNG
    if event:
        event.preventDefault()
        
    if not current_return_order_id: return
    reason_raw = document.getElementById("exchange-reason-text").value.strip()
    reason_display = reason_raw if reason_raw else "Sản phẩm lỗi/Sai thông số"
    
    for o in orders:
        if o.get('id') == current_return_order_id:
            o['status'] = 'exchange_pending'
            o['return_reason'] = f"Yêu cầu đổi hàng: {reason_display}"
            break
            
    document.getElementById("modal-exchange-product").classList.remove("open")
    current_return_order_id = "" 
    save_data(); render_orders_table()

def approve_return_request(order_id):
    global orders, products
    for o in orders:
        if o.get('id') == order_id and o.get('status') in ['return_pending', 'exchange_pending']:
            o['status'] = 'refunded'
            found_prod = False
            for p in products:
                if p['name'] == o.get('p_name', ''):
                    p['quantity'] = int(p['quantity']) + int(o.get('return_qty', 0))
                    found_prod = True
                    break
            if not found_prod and o.get('p_name'):
                products.append({
                    "name": o['p_name'],
                    "price": o['val'] / o['return_qty'] if int(o.get('return_qty', 0)) > 0 else 0,
                    "quantity": o['return_qty']
                })
            break
            
    save_data(); render_tables(); render_orders_table()

def render_orders_table():
    tbody = document.getElementById("orders-tbody")
    if not tbody: return
    tbody.innerHTML = ""
    search_val = document.getElementById("search-order").value.strip().lower() if document.getElementById("search-order") else ""
    
    for o in reversed(orders):
        # Sử dụng .get() để tránh lỗi KeyError an toàn tuyệt đối
        order_id = o.get('id', '')
        order_name = o.get('name', '')
        order_time = o.get('time', 'Không rõ')
        order_type = o.get('type', 'Chưa phân loại')
        order_qty = o.get('qty', 0)
        
        if search_val and search_val not in order_id.lower() and search_val not in order_name.lower(): continue
        tr = document.createElement("tr")
        current_status = o.get('status', 'done')
        
        td_time = document.createElement("td")
        td_time.innerHTML = f"<span class='text-muted' style='font-size:0.85rem;'>{order_time}</span>"
        tr.appendChild(td_time)
        
        td_id = document.createElement("td")
        td_id.innerHTML = f"<strong class='text-blue'>{order_id}</strong>"
        tr.appendChild(td_id)
        
        td_name = document.createElement("td")
        td_name.className = "fw-semibold"
        td_name.textContent = f"[{order_type}] {order_name} (SL: {order_qty})"
        tr.appendChild(td_name)
        
        td_val = document.createElement("td")
        td_val.className = "fw-bold text-green"
        
        td_status = document.createElement("td")
        td_act = document.createElement("td")
        
        if order_id.startswith('KK'):
            td_status.innerHTML = "<span class='badge bg-danger'>Kiểm kho</span>"
            td_val.textContent = "Kiểm toán"
            td_act.innerHTML = "<span class='text-muted' style='font-size:0.85rem;'>-</span>"
        else:
            if current_status == 'paid':
                td_status.innerHTML = "<span class='badge bg-success'>Đã thanh toán</span>"
                td_val.textContent = format_currency(o.get('val', 0))
                
                div_btns = document.createElement("div")
                div_btns.style.display = "flex"
                div_btns.style.gap = "4px"
                
                btn_cancel_call = document.createElement("button")
                btn_cancel_call.innerHTML = "<i class='fa-solid fa-circle-xmark'></i> Chọn Hủy"
                btn_cancel_call.className = "btn-gcp-cancel"
                btn_cancel_call.style.fontSize = "0.7rem"; btn_cancel_call.style.padding = "4px 6px"
                btn_cancel_call.addEventListener("click", create_proxy(lambda e, oid=order_id: trigger_cancel_modal(oid)))
                
                btn_exchange_call = document.createElement("button")
                btn_exchange_call.innerHTML = "<i class='fa-solid fa-arrows-rotate'></i> Hoàn Đổi"
                btn_exchange_call.className = "btn-gcp-pay"
                btn_exchange_call.style.fontSize = "0.7rem"; btn_exchange_call.style.padding = "4px 6px"; btn_exchange_call.style.backgroundColor = "#3b82f6"
                btn_exchange_call.addEventListener("click", create_proxy(lambda e, oid=order_id: trigger_exchange_modal(oid)))
                
                div_btns.appendChild(btn_cancel_call)
                div_btns.appendChild(btn_exchange_call)
                td_act.appendChild(div_btns)
                
            elif current_status == 'return_pending':
                title_reason = o.get('return_reason', 'Yêu cầu hủy')
                td_status.innerHTML = f"<span class='badge bg-warning text-dark' title='{title_reason}' style='cursor:pointer;'><i class='fa-solid fa-clock-rotate-left'></i> Chờ duyệt hoàn tiền</span>"
                td_val.textContent = format_currency(o.get('val', 0))
                
                btn_app = document.createElement("button")
                btn_app.innerHTML = "<i class='fa-solid fa-circle-check'></i> Duyệt Hoàn Tiền"
                btn_app.className = "btn-gcp-serve"
                btn_app.style.fontSize = "0.75rem"; btn_app.style.padding = "4px 8px"
                btn_app.addEventListener("click", create_proxy(lambda e, oid=order_id: approve_return_request(oid)))
                td_act.appendChild(btn_app)
                
            elif current_status == 'exchange_pending':
                title_reason = o.get('return_reason', 'Yêu cầu đổi')
                td_status.innerHTML = f"<span class='badge' style='background-color:#06b6d4 !important; color:#fff; cursor:pointer;' title='{title_reason}'><i class='fa-solid fa-arrows-rotate'></i> Chờ duyệt đổi hàng</span>"
                td_val.textContent = format_currency(o.get('val', 0))
                
                btn_app = document.createElement("button")
                btn_app.innerHTML = "<i class='fa-solid fa-circle-check'></i> Duyệt Đổi Hàng"
                btn_app.className = "btn-gcp-serve"
                btn_app.style.fontSize = "0.75rem"; btn_app.style.padding = "4px 8px"; btn_app.style.backgroundColor = "#06b6d4"
                btn_app.addEventListener("click", create_proxy(lambda e, oid=order_id: approve_return_request(oid)))
                td_act.appendChild(btn_app)
                
            elif current_status == 'refunded':
                td_status.innerHTML = "<span class='badge bg-secondary' style='background-color:#64748b !important;'><i class='fa-solid fa-arrow-rotate-left'></i> Đã hoàn trả kho</span>"
                td_val.innerHTML = f"<del style='color:#94a3b8;'>{format_currency(o.get('val', 0))}</del>"
                td_act.innerHTML = "<span class='text-muted' style='font-size:0.85rem; color:#94a3b8; font-weight:500;'>Hoàn tất</span>"
                
        tr.appendChild(td_val)
        tr.appendChild(td_status)
        tr.appendChild(td_act)
        tbody.appendChild(tr)
def handle_search_product(e):
    render_tables()

def handle_search_order(e):
    render_orders_table()

def add_product(event):
    # CHẶN RELOAD TRANG TUYỆT ĐỐI KHI BẤM THÊM SẢN PHẨM
    if event:
        event.preventDefault()
        
    name = document.getElementById("product-name").value.strip()
    price_str = document.getElementById("product-price").value.strip()
    qty_str = document.getElementById("product-quantity").value.strip()
    if not name or not price_str or not qty_str: return
    try:
        price_val, qty_val = float(price_str), int(qty_str)
        if price_val < 0 or qty_val < 0: return
    except ValueError: return
    products.append({"name": name, "price": price_val, "quantity": qty_val})
    document.getElementById("product-name").value = ""
    document.getElementById("product-price").value = ""
    document.getElementById("product-quantity").value = ""
    save_data()
    render_tables()

def render_deleted_table():
    tbody = document.getElementById("deleted-tbody")
    if not tbody: return
    tbody.innerHTML = ""
    for p in reversed(deleted_products):
        tr = document.createElement("tr")
        tr.innerHTML = f"<td>{p['name']}</td><td>{format_currency(float(p['price']))}</td><td>{p['quantity']} cái</td>"
        tbody.appendChild(tr)

def main():
    load_data(); render_tables(); render_orders_table(); render_deleted_table()
    if document.getElementById("add-btn"): document.getElementById("add-btn").addEventListener("click", create_proxy(add_product))
    if document.getElementById("search-input"): document.getElementById("search-input").addEventListener("input", create_proxy(handle_search_product))
    if document.getElementById("search-order"): document.getElementById("search-order").addEventListener("input", create_proxy(handle_search_order))
    if document.getElementById("modal-confirm-btn"): document.getElementById("modal-confirm-btn").addEventListener("click", create_proxy(confirm_quantity_modal))
    
    if document.getElementById("cancel-submit-btn"): document.getElementById("cancel-submit-btn").addEventListener("click", create_proxy(submit_cancel_request))
    if document.getElementById("exchange-submit-btn"): document.getElementById("exchange-submit-btn").addEventListener("click", create_proxy(submit_exchange_request))

    window.openQuantityModal = create_proxy(open_quantity_modal)
    window.deleteProduct = create_proxy(delete_product)

main()
