import tkinter as tk
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

DB_FILE = "billing_demo.db"

# --- Database Setup ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.init_db()

    def init_db(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS products(
            product_id TEXT PRIMARY KEY,
            name TEXT,
            price REAL,
            stock INTEGER
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS invoices(
            invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT,
            date TEXT,
            customer_name TEXT,
            customer_address TEXT,
            customer_phone TEXT,
            customer_email TEXT,
            payment_terms TEXT,
            subtotal REAL,
            tax REAL,
            discount REAL,
            grand_total REAL,
            amount_paid REAL,
            balance_due REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS invoice_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            product_id TEXT,
            name TEXT,
            qty INTEGER,
            price REAL,
            total REAL
        )''')
        self.conn.commit()

    def get_products(self):
        c = self.conn.cursor()
        c.execute('SELECT product_id, name, price, stock FROM products')
        return c.fetchall()

    def get_product(self, pid):
        c = self.conn.cursor()
        c.execute('SELECT product_id, name, price, stock FROM products WHERE product_id=?', (pid,))
        return c.fetchone()

    def update_stock(self, pid, qty):
        c = self.conn.cursor()
        c.execute('UPDATE products SET stock=stock-? WHERE product_id=?', (qty, pid))
        self.conn.commit()

    def save_invoice(self, invoice, items):
        c = self.conn.cursor()
        c.execute('''INSERT INTO invoices(invoice_no, date, customer_name, customer_address, customer_phone, customer_email, payment_terms, subtotal, tax, discount, grand_total, amount_paid, balance_due)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (invoice['invoice_no'], invoice['date'], invoice['customer_name'], invoice['customer_address'], invoice['customer_phone'], invoice['customer_email'], invoice['payment_terms'], invoice['subtotal'], invoice['tax'], invoice['discount'], invoice['grand_total'], invoice['amount_paid'], invoice['balance_due'])
        )
        invoice_id = c.lastrowid
        for item in items:
            c.execute('''INSERT INTO invoice_items(invoice_id, product_id, name, qty, price, total)
                VALUES (?,?,?,?,?,?)''',
                (invoice_id, item['product_id'], item['name'], item['qty'], item['price'], item['total'])
            )
            self.update_stock(item['product_id'], item['qty'])
        self.conn.commit()
        return invoice_id

# --- Billing GUI ---
class BillingApp:
    def __init__(self, root):
        self.root = root
        self.db = Database()
        self.root.title("Billing Software")
        self.create_billing_page()

    def create_billing_page(self):
        # --- Top: Customer & Invoice Details ---
        btn_frame = tk.Frame(right_frame, pady=10)
        btn_frame.pack(fill='x')
        def show_stock_update():
            for w in right_frame.winfo_children():
                if w != btn_frame:
                    w.destroy()
            update_frame = tk.Frame(right_frame, padx=10, pady=10)
            update_frame.pack(fill='both', expand=True)
            tk.Label(update_frame, text="Material Code Update Panel", font=("Arial", 14)).pack(pady=10)
            # Add your material code update logic here

        def show_stock_overview():
            for w in right_frame.winfo_children():
                if w != btn_frame:
                    w.destroy()
            overview_frame = tk.Frame(right_frame, padx=10, pady=10)
            overview_frame.pack(fill='both', expand=True)
            tk.Label(overview_frame, text="Material Code Overview Panel", font=("Arial", 14)).pack(pady=10)
            tv = ttk.Treeview(overview_frame, columns=["Code","Name","Material Code","Rate"], show="headings")
            for col in ["Code","Name","Material Code","Rate"]:
                tv.heading(col, text=col)
            for mat in materials:
                tv.insert("", "end", values=[mat["code"], mat["name"], mat["code"], mat["rate"]])
            tv.pack(fill='both', expand=True)

        def show_add_new_item():
            for w in right_frame.winfo_children():
                if w != btn_frame:
                    w.destroy()
            add_frame = tk.Frame(right_frame, padx=10, pady=10)
            add_frame.pack(fill='both', expand=True)
            tk.Label(add_frame, text="Add New Item Panel", font=("Arial", 14)).pack(pady=10)
            tk.Label(add_frame, text="Code").pack()
            code_entry = tk.Entry(add_frame)
            code_entry.pack()
            tk.Label(add_frame, text="Name").pack()
            name_entry = tk.Entry(add_frame)
            name_entry.pack()
            tk.Label(add_frame, text="Material Code").pack()
            material_code_entry = tk.Entry(add_frame)
            material_code_entry.pack()
            tk.Label(add_frame, text="Rate").pack()
            rate_entry = tk.Entry(add_frame)
            rate_entry.pack()
            def add_item():
                code = code_entry.get()
                name = name_entry.get()
                material_code = material_code_entry.get()
                try:
                    rate = float(rate_entry.get())
                except ValueError:
                    messagebox.showerror("Error", "Rate must be number.")
                    return
                materials.append({"code": code, "name": name, "material_code": material_code, "rate": rate})
                messagebox.showinfo("Added", f"Item {name} added.")
                refresh_tree()
            tk.Button(add_frame, text="Add Item", command=add_item).pack(pady=10)
            # ...existing code...

        # --- Buttons ---
        btn_frame = tk.Frame(entry_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        tk.Button(btn_frame, text="Add Item", command=self.add_item).grid(row=0, column=0, padx=2)
        tk.Button(btn_frame, text="Remove Item", command=self.remove_item).grid(row=0, column=1, padx=2)
        tk.Button(btn_frame, text="Save & Close", command=self.save_and_close).grid(row=0, column=2, padx=2)
        tk.Button(btn_frame, text="Print", command=self.print_invoice).grid(row=0, column=3, padx=2)
        tk.Button(btn_frame, text="Preview", command=self.preview_invoice).grid(row=0, column=4, padx=2)
        tk.Button(btn_frame, text="Make Payment", command=self.make_payment).grid(row=0, column=5, padx=2)

        # --- Summary Section ---
        sum_frame = tk.LabelFrame(self.root, text="Summary", padx=10, pady=5)
        sum_frame.pack(fill='x', padx=10, pady=5)
        self.subtotal_var = tk.StringVar(value="0.00")
        self.tax_var = tk.StringVar(value="0.00")
        self.discount_var = tk.StringVar(value="0.00")
        self.grand_total_var = tk.StringVar(value="0.00")
        self.amount_paid_var = tk.StringVar(value="0.00")
        self.balance_due_var = tk.StringVar(value="0.00")
        self.tax_entry = tk.Entry(sum_frame, width=8)
        self.tax_entry.insert(0, "18")
        self.discount_entry = tk.Entry(sum_frame, width=8)
        self.discount_entry.insert(0, "0")
        for i, (lbl, var, entry) in enumerate([
            ("Subtotal", self.subtotal_var, None),
            ("Tax (GST %)", self.tax_var, self.tax_entry),
            ("Discount", self.discount_var, self.discount_entry),
            ("Grand Total", self.grand_total_var, None),
            ("Amount Paid", self.amount_paid_var, None),
            ("Balance Due", self.balance_due_var, None)
        ]):
            tk.Label(sum_frame, text=lbl).grid(row=i, column=0, sticky='e')
            tk.Label(sum_frame, textvariable=var, width=12).grid(row=i, column=1)
            if entry:
                entry.grid(row=i, column=2, padx=5)

        self.items = []

    def fill_product_details(self, event=None):
        pid = self.prod_id_cb.get()
        prod = self.db.get_product(pid)
        if prod:
            self.prod_name_lbl.config(text=prod[1])
            self.price_lbl.config(text=f"{prod[2]:.2f}")
        else:
            self.prod_name_lbl.config(text="")
            self.price_lbl.config(text="")

    def add_item(self):
        pid = self.prod_id_cb.get()
        prod = self.db.get_product(pid)
        try:
            qty = int(self.qty_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a number.")
            return
        if not prod or qty <= 0 or qty > prod[3]:
            messagebox.showerror("Error", "Invalid product or insufficient stock.")
            return
        total = qty * prod[2]
        item = {
            "product_id": pid,
            "name": prod[1],
            "qty": qty,
            "price": prod[2],
            "total": total
        }
        self.items.append(item)
        self.tree.insert("", "end", values=(pid, prod[1], qty, f"{prod[2]:.2f}", f"{total:.2f}"))
        self.update_summary()

    def remove_item(self):
        selected = self.tree.selection()
        if not selected:
            return
        idx = self.tree.index(selected[0])
        self.tree.delete(selected[0])
        del self.items[idx]
        self.update_summary()

    def update_summary(self):
        subtotal = sum(item['total'] for item in self.items)
        try:
            tax_percent = float(self.tax_entry.get())
        except ValueError:
            tax_percent = 0
        try:
            discount = float(self.discount_entry.get())
        except ValueError:
            discount = 0
        tax = subtotal * tax_percent / 100
        grand_total = subtotal + tax - discount
        self.subtotal_var.set(f"{subtotal:.2f}")
        self.tax_var.set(f"{tax:.2f}")
        self.discount_var.set(f"{discount:.2f}")
        self.grand_total_var.set(f"{grand_total:.2f}")
        try:
            amount_paid = float(self.amount_paid_var.get())
        except ValueError:
            amount_paid = 0
        balance_due = grand_total - amount_paid
        self.balance_due_var.set(f"{balance_due:.2f}")

    def save_and_close(self):
        if not self.items:
            messagebox.showerror("Error", "Add at least one item.")
            return
        invoice = {
            "invoice_no": self.inv_no.get(),
            "date": self.inv_date.get(),
            "customer_name": self.cust_name.get(),
            "customer_address": self.cust_addr.get(),
            "customer_phone": self.cust_phone.get(),
            "customer_email": self.cust_email.get(),
            "payment_terms": self.inv_terms.get(),
            "subtotal": float(self.subtotal_var.get()),
            "tax": float(self.tax_var.get()),
            "discount": float(self.discount_var.get()),
            "grand_total": float(self.grand_total_var.get()),
            "amount_paid": float(self.amount_paid_var.get()),
            "balance_due": float(self.balance_due_var.get())
        }
        self.db.save_invoice(invoice, self.items)
        messagebox.showinfo("Saved", "Invoice saved and stock updated.")
        self.root.destroy()

    def print_invoice(self):
        messagebox.showinfo("Print", "Printing invoice... (demo)")

    def preview_invoice(self):
        messagebox.showinfo("Preview", "Preview invoice... (demo)")

    def make_payment(self):
        paid = tk.simpledialog.askfloat("Payment", "Enter amount paid:", initialvalue=float(self.amount_paid_var.get()))
        if paid is not None:
            self.amount_paid_var.set(f"{paid:.2f}")
            self.update_summary()

    # Optional: PDF export
    def export_pdf(self, filename="invoice.pdf"):
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF Error", "ReportLab not installed.")
            return
        c = canvas.Canvas(filename, pagesize=A4)
        c.drawString(100, 800, f"Invoice No: {self.inv_no.get()}")
        c.drawString(100, 780, f"Date: {self.inv_date.get()}")
        c.drawString(100, 760, f"Customer: {self.cust_name.get()}")
        c.drawString(100, 740, f"Address: {self.cust_addr.get()}")
        c.drawString(100, 720, f"Phone: {self.cust_phone.get()}")
        c.drawString(100, 700, f"Email: {self.cust_email.get()}")
        y = 680
        c.drawString(100, y, "Items:")
        y -= 20
        for item in self.items:
            c.drawString(100, y, f"{item['product_id']} {item['name']} x{item['qty']} @ {item['price']} = {item['total']:.2f}")
            y -= 20
        y -= 10
        c.drawString(100, y, f"Subtotal: {self.subtotal_var.get()}")
        y -= 20
        c.drawString(100, y, f"Tax: {self.tax_var.get()}")
        y -= 20
        c.drawString(100, y, f"Discount: {self.discount_var.get()}")
        y -= 20
        c.drawString(100, y, f"Grand Total: {self.grand_total_var.get()}")
        y -= 20
        c.drawString(100, y, f"Amount Paid: {self.amount_paid_var.get()}")
        y -= 20
        c.drawString(100, y, f"Balance Due: {self.balance_due_var.get()}")
        c.save()
        messagebox.showinfo("PDF", f"Invoice saved as {filename}")

# Sample materials data (define before usage)
materials = [
    {"code": "M01", "name": "ItemA", "stock": 50, "rate": 100},
    {"code": "M02", "name": "ItemB", "stock": 30, "rate": 75}
]

# Sample bills list (define before usage)
bills = []

# Export bills to Excel
def export_to_excel(bills_list, filename):
    try:
        import pandas as pd
    except ImportError:
        messagebox.showerror("Error", "Pandas is required to export to Excel.")
        return
    if not bills_list:
        messagebox.showinfo("Info", "No bills to export.")
        return
    df = pd.DataFrame(bills_list)
    df.to_excel(filename, index=False)
    messagebox.showinfo("Exported", f"Data exported to {filename}")

def main_menu():
    # Destroy all Toplevel windows except the main menu
    for w in tk._default_root.winfo_children():
        if isinstance(w, tk.Toplevel):
            w.destroy()
    # Optionally, you can add logic to show the main menu window if hidden


# --- Login and Main Menu ---
def login_screen():
    root = tk.Tk()
    root.title("Login")
    root.state('zoomed')
    frame = tk.Frame(root)
    frame.place(relx=0.5, rely=0.5, anchor='center')
    tk.Label(frame, text="User Login", font=("Arial", 24)).pack(pady=20)
    tk.Label(frame, text="Username", font=("Arial", 16)).pack(pady=5)
    entry_user = tk.Entry(frame, font=("Arial", 16), width=20)
    entry_user.pack(pady=5)
    tk.Label(frame, text="Password", font=("Arial", 16)).pack(pady=5)
    entry_pass = tk.Entry(frame, show="*", font=("Arial", 16), width=20)
    entry_pass.pack(pady=5)
    def check_login():
        if entry_user.get() == "admin" and entry_pass.get() == "admin":
            root.destroy()
            main_menu()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password")
    tk.Button(frame, text="Login", command=check_login, font=("Arial", 16), width=15).pack(pady=10)
    tk.Button(frame, text="Exit", command=root.quit, font=("Arial", 16), width=15).pack(pady=10)
    root.mainloop()

def main_menu():
    main = tk.Tk()
    main.title("Main Menu")
    main.state('zoomed')
    paned = tk.PanedWindow(main, orient=tk.HORIZONTAL)
    paned.pack(fill='both', expand=True)
    menu_frame = tk.Frame(paned, width=320, bg='#f0f0f0')
    paned.add(menu_frame, minsize=320)
    button_opts = {'anchor': 'w', 'padx': 10, 'pady': 15, 'ipadx': 40, 'ipady': 10}
    right_frame = tk.Frame(paned, bg='#ffffff')
    paned.add(right_frame, minsize=int(main.winfo_screenwidth()*0.75), stretch='always')

    def show_billing_in_right():
        for widget in right_frame.winfo_children():
            widget.destroy()
        paned.paneconfig(right_frame, minsize=int(main.winfo_screenwidth()*0.75))
        # --- Top: Customer & Invoice Details ---
        top_frame = tk.Frame(right_frame, padx=10, pady=10)
        top_frame.pack(fill='x')
        # Customer Details
        cust_frame = tk.LabelFrame(top_frame, text="Customer Details", padx=10, pady=5)
        cust_frame.pack(side='left', fill='y', padx=5)
        cust_name = tk.Entry(cust_frame, width=25)
        cust_phone = tk.Entry(cust_frame, width=25)
        cust_email = tk.Entry(cust_frame, width=25)
        for i, (lbl, ent) in enumerate([
            ("Name", cust_name),
            ("Phone", cust_phone),
            ("Email", cust_email)
        ]):
            tk.Label(cust_frame, text=lbl).grid(row=i, column=0, sticky='e')
            ent.grid(row=i, column=1, pady=2)
        # Invoice Details
        inv_frame = tk.LabelFrame(top_frame, text="Invoice Details", padx=10, pady=5)
        inv_frame.pack(side='left', fill='y', padx=5)
        inv_no = tk.Entry(inv_frame, width=20)
        inv_date = tk.Entry(inv_frame, width=20)
        inv_terms = tk.Entry(inv_frame, width=20)
        inv_no.insert(0, f"INV{int(datetime.datetime.now().timestamp())}")
        inv_date.insert(0, datetime.datetime.now().strftime("%Y-%m-%d"))
        for i, (lbl, ent) in enumerate([
            ("Invoice No", inv_no),
            ("Date", inv_date),
            ("Payment Terms", inv_terms)
        ]):
            tk.Label(inv_frame, text=lbl).grid(row=i, column=0, sticky='e')
            ent.grid(row=i, column=1, pady=2)

        # --- Middle: Item Table ---
        mid_frame = tk.Frame(right_frame, padx=10, pady=5)
        mid_frame.pack(fill='both', expand=True)
        columns = ("Product ID", "Product Name", "Qty", "Price", "Total")
        tree = ttk.Treeview(mid_frame, columns=columns, show='headings', height=8)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120 if col != "Product Name" else 200)
        tree.pack(side='left', fill='both', expand=True)
        # Item Entry
        entry_frame = tk.Frame(mid_frame)
        entry_frame.pack(side='left', fill='y', padx=10)
        db = Database()
        prod_id_cb = ttk.Combobox(entry_frame, width=15, values=[p[0] for p in db.get_products()])
        prod_name_lbl = tk.Label(entry_frame, text="", width=20)
        qty_entry = tk.Entry(entry_frame, width=8)
        price_lbl = tk.Label(entry_frame, text="", width=10)
        for i, (lbl, widget) in enumerate([
            ("Product ID", prod_id_cb),
            ("Name", prod_name_lbl),
            ("Quantity", qty_entry),
            ("Price", price_lbl)
        ]):
            tk.Label(entry_frame, text=lbl).grid(row=i, column=0, sticky='e')
            widget.grid(row=i, column=1, pady=2)

        items = []
        def fill_product_details(event=None):
            pid = prod_id_cb.get()
            prod = db.get_product(pid)
            if prod:
                prod_name_lbl.config(text=prod[1])
                price_lbl.config(text=f"{prod[2]:.2f}")
            else:
                prod_name_lbl.config(text="")
                price_lbl.config(text="")
        prod_id_cb.bind("<<ComboboxSelected>>", fill_product_details)

        # --- Buttons ---
        btn_frame = tk.Frame(entry_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
        def add_item():
            pid = prod_id_cb.get()
            prod = db.get_product(pid)
            try:
                qty = int(qty_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Quantity must be a number.")
                return
            if not prod or qty <= 0 or qty > prod[3]:
                messagebox.showerror("Error", "Invalid product or insufficient stock.")
                return
            total = qty * prod[2]
            item = {
                "product_id": pid,
                "name": prod[1],
                "qty": qty,
                "price": prod[2],
                "total": total
            }
            items.append(item)
            tree.insert("", "end", values=(pid, prod[1], qty, f"{prod[2]:.2f}", f"{total:.2f}"))
            update_summary()

        def remove_item():
            selected = tree.selection()
            if not selected:
                return
            idx = tree.index(selected[0])
            tree.delete(selected[0])
            del items[idx]
            update_summary()

        tk.Button(btn_frame, text="Add Item", command=add_item).grid(row=0, column=0, padx=2)
        tk.Button(btn_frame, text="Remove Item", command=remove_item).grid(row=0, column=1, padx=2)

        # --- Summary Section ---
        sum_frame = tk.LabelFrame(right_frame, text="Summary", padx=10, pady=5)
        sum_frame.pack(fill='x', padx=10, pady=5)
        subtotal_var = tk.StringVar(value="0.00")
        tax_var = tk.StringVar(value="0.00")
        discount_var = tk.StringVar(value="0.00")
        grand_total_var = tk.StringVar(value="0.00")
        amount_paid_var = tk.StringVar(value="0.00")
        balance_due_var = tk.StringVar(value="0.00")
        tax_entry = tk.Entry(sum_frame, width=8)
        tax_entry.insert(0, "18")
        discount_entry = tk.Entry(sum_frame, width=8)
        discount_entry.insert(0, "0")
        for i, (lbl, var, entry) in enumerate([
            ("Subtotal", subtotal_var, None),
            ("Tax (GST %)", tax_var, tax_entry),
            ("Discount", discount_var, discount_entry),
            ("Grand Total", grand_total_var, None),
            ("Amount Paid", amount_paid_var, None),
            ("Balance Due", balance_due_var, None)
        ]):
            tk.Label(sum_frame, text=lbl).grid(row=i, column=0, sticky='e')
            tk.Label(sum_frame, textvariable=var, width=12).grid(row=i, column=1)
            if entry:
                entry.grid(row=i, column=2, padx=5)

        def update_summary():
            subtotal = sum(item['total'] for item in items)
            try:
                tax_percent = float(tax_entry.get())
            except ValueError:
                tax_percent = 0
            try:
                discount = float(discount_entry.get())
            except ValueError:
                discount = 0
            tax = subtotal * tax_percent / 100
            grand_total = subtotal + tax - discount
            subtotal_var.set(f"{subtotal:.2f}")
            tax_var.set(f"{tax:.2f}")
            discount_var.set(f"{discount:.2f}")
            grand_total_var.set(f"{grand_total:.2f}")
            try:
                amount_paid = float(amount_paid_var.get())
            except ValueError:
                amount_paid = 0
            balance_due = grand_total - amount_paid
            balance_due_var.set(f"{balance_due:.2f}")

        def save_and_close():
            if not items:
                messagebox.showerror("Error", "Add at least one item.")
                return
            invoice = {
                "invoice_no": inv_no.get(),
                "date": inv_date.get(),
                "customer_name": cust_name.get(),
                "customer_address": "",  # Not in UI
                "customer_phone": cust_phone.get(),
                "customer_email": cust_email.get(),
                "payment_terms": inv_terms.get(),
                "subtotal": float(subtotal_var.get()),
                "tax": float(tax_var.get()),
                "discount": float(discount_var.get()),
                "grand_total": float(grand_total_var.get()),
                "amount_paid": float(amount_paid_var.get()),
                "balance_due": float(balance_due_var.get())
            }
            db.save_invoice(invoice, items)
            messagebox.showinfo("Saved", "Invoice saved and stock updated.")
            for widget in right_frame.winfo_children():
                widget.destroy()

        def print_invoice():
            messagebox.showinfo("Print", "Printing invoice... (demo)")

        def preview_invoice():
            messagebox.showinfo("Preview", "Preview invoice... (demo)")

        def make_payment():
            paid = tk.simpledialog.askfloat("Payment", "Enter amount paid:", initialvalue=float(amount_paid_var.get()))
            if paid is not None:
                amount_paid_var.set(f"{paid:.2f}")
                update_summary()

        # --- Action Buttons ---
        action_frame = tk.Frame(right_frame, pady=10)
        action_frame.pack()
        tk.Button(action_frame, text="Save & Close", command=save_and_close, width=15).pack(side='left', padx=5)
        tk.Button(action_frame, text="Print", command=print_invoice, width=10).pack(side='left', padx=5)
        tk.Button(action_frame, text="Preview", command=preview_invoice, width=10).pack(side='left', padx=5)
        tk.Button(action_frame, text="Make Payment", command=make_payment, width=15).pack(side='left', padx=5)

    def show_stock_updating_in_right():
        for widget in right_frame.winfo_children():
            widget.destroy()
        btn_frame = tk.Frame(right_frame, pady=10)
        btn_frame.pack(fill='x')
        def show_stock_update():
            for w in right_frame.winfo_children():
                if w != btn_frame:
                    w.destroy()
            update_frame = tk.Frame(right_frame, padx=10, pady=10)
            update_frame.pack(fill='both', expand=True)
            tk.Label(update_frame, text="Stock Update Panel", font=("Arial", 14)).pack(pady=10)
            # Add your stock update logic here

        def show_stock_overview():
            for w in right_frame.winfo_children():
                if w != btn_frame:
                    w.destroy()
            overview_frame = tk.Frame(right_frame, padx=10, pady=10)
            overview_frame.pack(fill='both', expand=True)
            tk.Label(overview_frame, text="Stock Overview Panel", font=("Arial", 14)).pack(pady=10)
            tv = ttk.Treeview(overview_frame, columns=["Code","Name","Stock","Rate"], show="headings")
            for col in ["Code","Name","Stock","Rate"]:
                tv.heading(col, text=col)
            for mat in materials:
                tv.insert("", "end", values=[mat[x.lower()] for x in tv["columns"]])
            tv.pack(fill='both', expand=True)

        def show_add_new_item():
            for w in right_frame.winfo_children():
                if w != btn_frame:
                    w.destroy()
            add_frame = tk.Frame(right_frame, padx=10, pady=10)
            add_frame.pack(fill='both', expand=True)
            tk.Label(add_frame, text="Add New Item Panel", font=("Arial", 14)).pack(pady=10)
            tk.Label(add_frame, text="Code").pack()
            code_entry = tk.Entry(add_frame)
            code_entry.pack()
            tk.Label(add_frame, text="Name").pack()
            name_entry = tk.Entry(add_frame)
            name_entry.pack()
            tk.Label(add_frame, text="Stock").pack()
            stock_entry = tk.Entry(add_frame)
            stock_entry.pack()
            tk.Label(add_frame, text="Rate").pack()
            rate_entry = tk.Entry(add_frame)
            rate_entry.pack()

            def add_item():
                code = code_entry.get()
                name = name_entry.get()
                try:
                    stock = int(stock_entry.get())
                    rate = float(rate_entry.get())
                except ValueError:
                    messagebox.showerror("Error", "Stock must be integer, Rate must be number.")
                    return
                materials.append({"code": code, "name": name, "stock": stock, "rate": rate})
                messagebox.showinfo("Added", f"Item {name} added.")
                refresh_tree()
            tk.Button(add_frame, text="Add Item", command=add_item).pack(pady=10)

            # Search bar
            search_var = tk.StringVar()
            tk.Label(add_frame, text="Search Code/Name:").pack(pady=(10,0))
            search_entry = tk.Entry(add_frame, textvariable=search_var)
            search_entry.pack()

            # Treeview for materials
            tree = ttk.Treeview(add_frame, columns=["Code","Name","Material Code","Rate"], show="headings", height=6)
            for col in ["Code","Name","Material Code","Rate"]:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            tree.pack(fill='x', pady=10)

            def refresh_tree():
                tree.delete(*tree.get_children())
                query = search_var.get().lower()
                for mat in materials:
                    if query in mat["code"].lower() or query in mat["name"].lower() or ("material_code" in mat and query in mat["material_code"].lower()):
                        tree.insert("", "end", values=[mat.get("code",""), mat.get("name",""), mat.get("material_code", mat.get("code","")), mat.get("rate","")])

            search_var.trace_add('write', lambda *args: refresh_tree())
            refresh_tree()

            # Landscape action bar below the treeview
            action_bar = tk.Frame(add_frame, pady=10)
            action_bar.pack(fill='x')

            def edit_selected():
                selected = tree.selection()
                if not selected:
                    messagebox.showerror("Error", "Select a material to edit.")
                    return
                mat = [m for m in materials if (m["code"] == tree.item(selected[0])["values"][0])][0]
                code_entry.delete(0, 'end'); code_entry.insert(0, mat.get("code",""))
                name_entry.delete(0, 'end'); name_entry.insert(0, mat.get("name",""))
                material_code_entry.delete(0, 'end'); material_code_entry.insert(0, mat.get("material_code", mat.get("code","")))
                rate_entry.delete(0, 'end'); rate_entry.insert(0, str(mat.get("rate","")))

            def delete_selected():
                selected = tree.selection()
                if not selected:
                    messagebox.showerror("Error", "Select a material to delete.")
                    return
                code = tree.item(selected[0])["values"][0]
                for i, mat in enumerate(materials):
                    if mat["code"] == code:
                        del materials[i]
                        break
                refresh_tree()
                messagebox.showinfo("Deleted", f"Material {code} deleted.")

            def save_item():
                selected = tree.selection()
                if not selected:
                    messagebox.showerror("Error", "Select a material to save.")
                    return
                mat = [m for m in materials if (m["code"] == tree.item(selected[0])["values"][0])][0]
                try:
                    mat["code"] = code_entry.get()
                    mat["name"] = name_entry.get()
                    mat["material_code"] = material_code_entry.get()
                    mat["rate"] = float(rate_entry.get())
                except ValueError:
                    messagebox.showerror("Error", "Rate must be number.")
                    return
                messagebox.showinfo("Saved", "Material updated.")
                refresh_tree()

            tk.Button(action_bar, text="Edit", command=edit_selected, width=10).pack(side='left', padx=10)
            tk.Button(action_bar, text="Delete", command=delete_selected, width=10).pack(side='left', padx=10)
            tk.Button(action_bar, text="Save", command=save_item, width=10).pack(side='left', padx=10)

        tk.Button(btn_frame, text="Stock Update", command=show_stock_update, width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Stock Overview", command=show_stock_overview, width=15).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Add New Item", command=show_add_new_item, width=15).pack(side='left', padx=5)
        # Show overview by default
        show_stock_overview()

    def show_total_review_in_right():
        for widget in right_frame.winfo_children():
            widget.destroy()
        total_bills = len(bills)
        total_amount = sum(b['total'] for b in bills) if bills else 0
        tk.Label(right_frame, text=f"Total Bills: {total_bills}", font=("Arial", 16)).pack(pady=10)
        tk.Label(right_frame, text=f"Total Amount: {total_amount}", font=("Arial", 16)).pack(pady=10)

    ttk.Button(menu_frame, text="1. Billing", command=show_billing_in_right).pack(fill="x", **button_opts)
    ttk.Button(menu_frame, text="2. Stock", command=show_stock_updating_in_right).pack(fill="x", **button_opts)
    ttk.Button(menu_frame, text="3. Total Review", command=show_total_review_in_right).pack(fill="x", **button_opts)
    ttk.Button(menu_frame, text="Exit", command=main.quit).pack(fill="x", **button_opts)
    main.mainloop()

if __name__ == "__main__":
    login_screen()

def billing_screen_in_pane(paned):
    # Remove any previous right pane
    for child in paned.panes():
        if paned.panes().index(child) == 1:
            paned.forget(child)
    # Create billing frame (right, 75%)
    billing_frame = tk.Frame(paned)
    entries = {}
    for idx, label in enumerate(["Customer Name", "Contact Number", "Material Code", "Quantity"]):
        tk.Label(billing_frame, text=label).grid(row=idx, column=0, sticky='e', padx=10, pady=10)
        entry = tk.Entry(billing_frame)
        entry.grid(row=idx, column=1, padx=10, pady=10)
        entries[label] = entry

    def calc_and_save():
        code = entries["Material Code"].get()
        try:
            qty = int(entries["Quantity"].get())
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a number.")
            return
        mat = next((m for m in materials if m["code"] == code), None)
        if mat and qty <= mat["stock"]:
            total = qty * mat["rate"]
            bill = {
                "customer": entries["Customer Name"].get(),
                "contact": entries["Contact Number"].get(),
                "code": code,
                "qty": qty,
                "total": total
            }
            bills.append(bill)
            mat["stock"] -= qty
            messagebox.showinfo("Success", f"Bill Total: {total}")
        else:
            messagebox.showerror("Error", "Invalid material code or insufficient stock.")

    tk.Button(billing_frame, text="Print/Download (PDF)", command=calc_and_save).grid(row=5, column=0, padx=10, pady=10)
    tk.Button(billing_frame, text="Clear", command=lambda: [e.delete(0,'end') for e in entries.values()]).grid(row=5, column=1, padx=10, pady=10)
    def back_to_main():
        paned.forget(billing_frame)
    tk.Button(billing_frame, text="Back", command=back_to_main).grid(row=5, column=2, padx=10, pady=10)
    paned.add(billing_frame, minsize=600) 

# Billing Screen
def billing_screen():
    win = tk.Toplevel()
    win.title("Create Bill")
    entries = {}
    for idx, label in enumerate(["Customer Name", "Contact Number", "Material Code", "Quantity"]):
        tk.Label(win, text=label).grid(row=idx, column=0)
        entry = tk.Entry(win)
        entry.grid(row=idx, column=1)
        entries[label] = entry

    def calc_and_save():
        code = entries["Material Code"].get()
        try:
            qty = int(entries["Quantity"].get())
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a number.")
            return
        mat = next((m for m in materials if m["code"] == code), None)
        if mat and qty <= mat["stock"]:
            total = qty * mat["rate"]
            bill = {
                "customer": entries["Customer Name"].get(),
                "contact": entries["Contact Number"].get(),
                "code": code,
                "qty": qty,
                "total": total
            }
            bills.append(bill)
            mat["stock"] -= qty
            messagebox.showinfo("Success", f"Bill Total: {total}")
        else:
            messagebox.showerror("Error", "Invalid material code or insufficient stock.")

    tk.Button(win, text="Print/Download (PDF)", command=calc_and_save).grid(row=5, column=0)
    tk.Button(win, text="Back", command=win.destroy).grid(row=5, column=1)
    tk.Button(win, text="Main Menu", command=lambda: [win.destroy(), main_menu()]).grid(row=5, column=2)
    tk.Button(win, text="Exit", command=win.quit).grid(row=5, column=3)

# Bill History
def history_screen():
    win = tk.Toplevel()
    win.title("Bill History")
    tv = ttk.Treeview(win, columns=["Customer","Contact","Code","Qty","Total"], show="headings")
    for col in ["Customer","Contact","Code","Qty","Total"]:
        tv.heading(col, text=col)
    for bill in bills:
        tv.insert("", "end", values=[bill[k.lower()] for k in tv["columns"]])
    tv.pack()
    ttk.Button(win, text="Download Excel", command=lambda: export_to_excel(bills, "history.xlsx")).pack()
    ttk.Button(win, text="Back", command=win.destroy).pack()
    ttk.Button(win, text="Main Menu", command=lambda: [win.destroy(), main_menu()]).pack()
    ttk.Button(win, text="Exit", command=win.quit).pack()

# Bill Editing
def edit_bill_screen():
    win = tk.Toplevel()
    win.title("Edit Bill")
    if not bills:
        tk.Label(win, text="No bills to edit.").pack()
        return
    last_bill = bills[-1]
    entries = {}
    for idx, (label, value) in enumerate(last_bill.items()):
        tk.Label(win, text=label.title()).grid(row=idx, column=0)
        entry = tk.Entry(win)
        entry.insert(0, str(value))
        entry.grid(row=idx, column=1)
        entries[label] = entry

    def save_edit():
        for label, entry in entries.items():
            last_bill[label] = type(last_bill[label])(entry.get())
        messagebox.showinfo("Saved", "Bill Edited.")
    tk.Button(win, text="Save & Download", command=save_edit).pack()
    tk.Button(win, text="Back", command=win.destroy).pack()
    tk.Button(win, text="Main Menu", command=lambda: [win.destroy(), main_menu()]).pack()
    tk.Button(win, text="Exit", command=win.quit).pack()

# Material Management
def material_screen():
    win = tk.Toplevel()
    win.title("Material Management")
    tv = ttk.Treeview(win, columns=["Code","Name","Stock","Rate"], show="headings")
    for col in ["Code","Name","Stock","Rate"]:
        tv.heading(col, text=col)
    for mat in materials:
        tv.insert("", "end", values=[mat[x.lower()] for x in tv["columns"]])
    tv.pack()
    def add_material():
        materials.append({"code":"M03","name":"ItemC","stock":20,"rate":50})
        messagebox.showinfo("Added", "Material Added (demo).")
    ttk.Button(win, text="Add/Edit Material", command=add_material).pack()
    ttk.Button(win, text="Back", command=win.destroy).pack()
    ttk.Button(win, text="Main Menu", command=lambda: [win.destroy(), main_menu()]).pack()
    ttk.Button(win, text="Exit", command=win.quit).pack()

# Stock View
def stock_screen():
    win = tk.Toplevel()
    win.title("Stock")
    text = "\n".join(
        f"{mat['name']} | Total: {mat['stock']+sum(b['qty'] for b in bills if b['code']==mat['code'])} | Sold: {sum(b['qty'] for b in bills if b['code']==mat['code'])} | Available: {mat['stock']}"
        for mat in materials)
    tk.Label(win, text=text).pack()
    ttk.Button(win, text="Back", command=win.destroy).pack()
    ttk.Button(win, text="Main Menu", command=lambda: [win.destroy(), main_menu()]).pack()
    ttk.Button(win, text="Exit", command=win.quit).pack()

if __name__ == "__main__":
    login_screen()
    
#end of file 