from pyscript import window, document
from pyodide.ffi import create_proxy
import json
from datetime import datetime

products = []
orders = []
deleted_products = []

current_modal_index = -1
current_modal_action = ""

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

def format_currency(value):
    return "{:,.0f} đ".format(value).replace(",", ".")

def handle_search_product(event):
    render_tables()

def handle_search_order(event):
    render_orders_table()

def render_tables():
    tbody_web = document.getElementById("product-tbody")
    tbody_inv = document.getElementById("inventory-tbody")
    if not tbody_web or not tbody_inv: return
        
    tbody_web.innerHTML = ""
    tbody_inv.innerHTML = ""
    search_input = document.getElementById("search-input")
    query = search_input.value.strip().lower() if search_input else ""
    
    total_count = 0
    total_value = 0
    
    for i, p in enumerate(products):
        if query and query not in p['name'].lower(): continue
        subtotal = float(p['price']) * int(p['quantity'])
        total_count += int(p['quantity'])
        total_value += subtotal
        
        # BẢNG 2: MẶT HÀNG WEB
        tr_web = document.createElement("tr")
        tr_web.innerHTML = f"<td>{i+1}</td><td class='fw-semibold'>{p['name']}</td><td class='text-blue fw-bold'>{format_currency(float(p['price']))}</td>"
        
        td_status = document.createElement("td")
        td_status.innerHTML = f"<span class='badge {'bg-success' if p['quantity'] > 0 else 'bg-danger'}'>{'Đang bày bán' if p['quantity'] > 0 else 'Hết hàng'}</span>"
        tr_web.appendChild(td_status)
        
        td_act = document.createElement("td")
        div_act = document.createElement("div")
        div_act.className = "action-buttons-row"
        
        btn_sell = document.createElement("button")
        btn_sell.innerHTML = "<i class='fa-solid fa-cart-plus'></i> Đặt"
        btn_sell.className = "btn-gcp-serve"
        if p['quantity'] <= 0: btn_sell.disabled = True
        
        def make_sell_closure(idx):
            return create_proxy(lambda e: show_quantity_modal(idx, "sell"))
        btn_sell.addEventListener("click", make_sell_closure(i))
        
        btn_del = document.createElement("button")
        btn_del.innerHTML = "<i class='fa-solid fa-trash-can'></i> Hủy"
        btn_del.className = "btn-gcp-cancel"
        
        def make_del_closure(idx):
            return create_proxy(lambda e: show_quantity_modal(idx, "delete"))
        btn_del.addEventListener("click", make_del_closure(i))
        
        div_act.appendChild(btn_sell)
        div_act.appendChild(btn_del)
        td_act.appendChild(div_act)
        tr_web.appendChild(td_act)
        tbody_web.appendChild(tr_web)
        
        # BẢNG 3: TỒN KHO THỰC TẾ
        tr_inv = document.createElement("tr")
        tr_inv.innerHTML = f"<td>{i+1}</td><td>{p['name']}</td><td class='fw-bold' style='color:{'#ef4444' if p['quantity']<=3 else 'inherit'}'>{p['quantity']} cái</td><td class='text-purple'>{format_currency(subtotal)}</td>"
        
        td_inv_check = document.createElement("td")
        div_inv_act = document.createElement("div")
        div_inv_act.className = "action-buttons-row"
        
        btn_check = document.createElement("button")
        btn_check.innerHTML = "<i class='fa-solid fa-clipboard-check'></i> Kiểm kê"
        btn_check.className = "btn-gcp-pay"
        btn_check.addEventListener("click", create_proxy(lambda e, idx=i: edit_inventory_product(idx)))
        
        btn_inv_del = document.createElement("button")
        btn_inv_del.innerHTML = "<i class='fa-solid fa-trash-can'></i> Hủy kho"
        btn_inv_del.className = "btn-gcp-cancel"
        btn_inv_del.addEventListener("click", make_del_closure(i))
        
        div_inv_act.appendChild(btn_check)
        div_inv_act.appendChild(btn_inv_del)
        td_inv_check.appendChild(div_inv_act)
        tr_inv.appendChild(td_inv_check)
        tbody_inv.appendChild(tr_inv)
        
    document.getElementById("total-count").textContent = str(total_count)
    document.getElementById("total-value").textContent = format_currency(total_value)
    
    # Tính doanh thu thực tế (Trừ đi những đơn đã bị Hoàn trả)
    total_revenue = sum(float(o['total']) for o in orders if o['id'].startswith('DH') and o.get('status') != 'refunded')
    if document.getElementById("total-revenue"):
        document.getElementById("total-revenue").textContent = format_currency(total_revenue)

def edit_inventory_product(index):
    p = products[index]
    old_qty = p['quantity']
    new_qty_str = window.prompt(f"Nhập số lượng thực tế tại kho của '{p['name']}':", str(old_qty))
    if new_qty_str is not None:
        try:
            new_qty = int(new_qty_str.strip())
            if new_qty < 0: return
            diff = new_qty - old_qty
            if diff != 0:
                p['quantity'] = new_qty
                orders.append({
                    "id": f"KK{len(orders)+1:03d}", "name": f"{'[Kiểm dư]' if diff > 0 else '[Kiểm thiếu]'} {p['name']}",
                    "quantity": abs(diff), "price": 0, "total": 0, "time": datetime.now().strftime("%H:%M %d/%m/%y"), "status": "done"
                })
                save_data(); render_tables(); render_orders_table()
        except ValueError: pass

def show_quantity_modal(index, action):
    global current_modal_index, current_modal_action
    current_modal_index = index; current_modal_action = action
    p = products[index]
    document.getElementById("modal-title").textContent = "🛒 Khách Đặt Hàng" if action == "sell" else "🗑 Xóa Sản Phẩm"
    document.getElementById("modal-confirm-btn").style.backgroundColor = "#10b981" if action == "sell" else "#ef4444"
    document.getElementById("modal-p-name").textContent = p['name']
    document.getElementById("modal-p-stock").textContent = f"{p['quantity']} cái"
    document.getElementById("modal-quantity-input").value = "1" if action == "sell" else str(p['quantity'])
    document.getElementById("modal-confirm-btn").onclick = create_proxy(handle_modal_confirm)
    document.getElementById("quantity-modal").classList.add("open")

def handle_modal_confirm(event):
    global current_modal_index, current_modal_action
    if current_modal_index == -1: return
    p = products[current_modal_index]
    try:
        qty = int(document.getElementById("modal-quantity-input").value.strip())
        if qty <= 0: return
    except ValueError: return

    time_str = datetime.now().strftime("%H:%M %d/%m/%y")
    if current_modal_action == "sell":
        if qty > p['quantity']: return
        # Đơn hàng mới mặc định có trạng thái 'paid' (Đã thanh toán)
        orders.append({"id": f"DH{len(orders)+1:03d}", "name": p['name'], "quantity": qty, "price": float(p['price']), "total": qty * float(p['price']), "time": time_str, "status": "paid"})
        p['quantity'] -= qty
    elif current_modal_action == "delete":
        if qty >= p['quantity']:
            deleted_products.append({"name": p["name"], "price": p["price"], "quantity": p["quantity"]})
            products.pop(current_modal_index)
        else:
            deleted_products.append({"name": p["name"], "price": p["price"], "quantity": qty})
            p["quantity"] -= qty

    save_data(); document.getElementById("quantity-modal").classList.remove("open")
    render_tables(); render_orders_table(); render_deleted_table()

def trigger_return_request(order_id):
    """Khách hàng đổi ý, gửi yêu cầu hoàn hàng"""
    global orders
    for o in orders:
        if o['id'] == order_id:
            if window.confirm(f"Bạn muốn gửi yêu cầu Trả hàng / Hoàn tiền cho đơn {order_id}?"):
                o['status'] = 'return_pending'
                save_data(); render_tables(); render_orders_table()
            break

def approve_return_request(order_id):
    """Nhân viên duyệt yêu cầu hoàn trả đơn hàng -> Hàng trả lại về Kho thực tế"""
    global orders, products
    order_to_refund = next((o for o in orders if o['id'] == order_id), None)
    if order_to_refund and order_to_refund.get('status') == 'return_pending':
        if window.confirm(f"Xác nhận duyệt HOÀN TIỀN & NHẬP TRẢ LẠI KHO cho đơn {order_id}?"):
            order_to_refund['status'] = 'refunded'
            # Cộng trả lại số lượng vật lý vào kho
            for p in products:
                if p['name'] == order_to_refund['name']:
                    p['quantity'] += order_to_refund['quantity']
                    break
            save_data(); render_tables(); render_orders_table()

def delete_order(order_id):
    global orders, products
    order_to_delete = next((o for o in orders if o['id'] == order_id), None)
    if order_to_delete:
        orders.remove(order_to_delete)
        save_data(); render_tables(); render_orders_table()

def render_orders_table():
    tbody = document.getElementById("order-tbody")
    if not tbody: return
    tbody.innerHTML = ""
    query = document.getElementById("search-order").value.strip().lower() if document.getElementById("search-order") else ""
    
    for o in reversed(orders):
        if query and (query not in o['id'].lower() and query not in o['name'].lower()): continue
        tr = document.createElement("tr")
        
        don_gia_goc = float(o.get('price', 0))
        current_status = o.get('status', 'paid')
        
        # Thiết lập badge trạng thái động giống Shopee
        if o['id'].startswith('KK'):
            status_badge = "<span class='badge bg-danger'>Kiểm kho</span>"
            hien_thi_tien = "Kiểm kho"
        else:
            if current_status == 'paid':
                status_badge = "<span class='badge bg-success'>Đã thanh toán</span>"
                hien_thi_tien = format_currency(don_gia_goc) if don_gia_goc > 0 else "0 đ"
            elif current_status == 'return_pending':
                status_badge = "<span class='badge bg-warning text-dark'><i class='fa-solid fa-clock-rotate-left'></i> Chờ duyệt hoàn</span>"
                hien_thi_tien = format_currency(don_gia_goc)
            elif current_status == 'refunded':
                status_badge = "<span class='badge bg-secondary' style='background-color:#64748b !important;'><i class='fa-solid fa-arrow-rotate-left'></i> Đã hoàn trả kho</span>"
                hien_thi_tien = f"<del style='color:#94a3b8;'>{format_currency(don_gia_goc)}</del>"

        tr.innerHTML = f"""
            <td>{o.get('time', '15:00 14/06/26')}</td>
            <td class='fw-semibold'><span style='color:#3b82f6;'>{o['id']}</span> - {o['name']}</td>
            <td>{o['quantity']}</td>
            <td class='fw-bold text-green'>{hien_thi_tien}</td>
            <td>{status_badge}</td>
        """
        
        td_cancel = document.createElement("td")
        
        # XỬ LÝ NÚT THAO TÁC THEO TRẠNG THÁI
        if o['id'].startswith('DH'):
            if current_status == 'paid':
                # Nút cho phép Khách hàng đổi ý gửi yêu cầu trả hàng
                btn_return = document.createElement("button")
                btn_return.innerHTML = "<i class='fa-solid fa-arrow-turn-down'></i> Đổi ý hoàn đơn"
                btn_return.className = "btn-gcp-pay"  # Sử dụng màu xanh dương để làm nổi bật thao tác hợp lệ
                btn_return.style.padding = "4px 8px"
                btn_return.style.fontSize = "0.8rem"
                btn_return.style.backgroundColor = "#f59e0b"  # Màu cam hổ phách
                btn_return.addEventListener("click", create_proxy(lambda e, oid=o['id']: trigger_return_request(oid)))
                td_cancel.appendChild(btn_return)
                
            elif current_status == 'return_pending':
                # Nút dành cho Admin duyệt lệnh đồng ý trả tiền, nhập lại kho
                btn_approve = document.createElement("button")
                btn_approve.innerHTML = "<i class='fa-solid fa-circle-check'></i> Duyệt Hoàn Kho"
                btn_approve.className = "btn-gcp-serve"
                btn_approve.style.padding = "4px 8px"
                btn_approve.style.fontSize = "0.8rem"
                btn_approve.addEventListener("click", create_proxy(lambda e, oid=o['id']: approve_return_request(oid)))
                td_cancel.appendChild(btn_approve)
                
            elif current_status == 'refunded':
                # Đã giải quyết xong xuôi
                td_cancel.innerHTML = "<span class='text-muted' style='font-size:0.85rem; color:#94a3b8; font-weight:500;'>Hoàn tất</span>"
        else:
            # Đối với biên bản kiểm kê kho (KK) thì vẫn giữ nút hủy biên bản như cũ
            btn_cancel = document.createElement("button")
            btn_cancel.innerHTML = "<i class='fa-solid fa-rectangle-xmark'></i> Hủy"
            btn_cancel.className = "btn-gcp-cancel"
            btn_cancel.addEventListener("click", create_proxy(lambda e, oid=o['id']: delete_order(oid) if window.confirm(f"Hủy đơn {oid}?") else None))
            td_cancel.appendChild(btn_cancel)
            
        tr.appendChild(td_cancel)
        tbody.appendChild(tr)

def add_product(event):
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
    save_data(); render_tables()

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

main()