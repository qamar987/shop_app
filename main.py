"""
Cloth Shop Management App
--------------------------
Features:
1. Stock Add        -> Naye suit shop me aane par entry (kitne suit aaye)
2. Sale Add          -> Suit sale hone par customer name, price, payment,
                         aur baqaya (due amount) automatically calculate hota hai
3. Sales List        -> Saari sales ek table (Treeview) me dikhengi
4. Summary Button     -> Total suits aaye, total suits sale hoye,
                         total payment aayi, total baqaya (pending amount)

Data ek local SQLite database file (shop_data.db) me save hota hai,
isliye app band karne ke baad bhi data safe rehta hai.
"""

import sqlite3
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os


def get_db_path():
    """
    Database ki file hamesha ek FIXED, permanent jagah par banani hai.
    - Agar app .py script ki tarah chal rahi ho -> usi folder me jahan script hai.
    - Agar app PyInstaller se bani .exe ki tarah chal rahi ho -> PyInstaller
      --onefile app ko run time par ek TEMPORARY folder me extract karta hai
      (sys._MEIPASS), jo app band hote hi Windows khud delete kar deta hai.
      Isi wajah se pehle database har baar delete ho rahi thi. Fix ye hai ke
      hum sys.executable (yani asal .exe file ki location) ka path use karein,
      na ke temp extraction folder ka.
    """
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "shop_data.db")


DB_FILE = get_db_path()


# ----------------------------------------------------------------------
# DATABASE LAYER
# ----------------------------------------------------------------------
class Database:
    def __init__(self, db_file=DB_FILE):
        self.conn = sqlite3.connect(db_file)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        cur = self.conn.cursor()
        # Stock table -> jab bhi naye suit shop me aayen
        cur.execute("""
            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                suit_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                purchase_price REAL NOT NULL,
                date_added TEXT NOT NULL
            )
        """)
        # Sales table -> jab suit customer ko sale ho
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                suit_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                total_price REAL NOT NULL,
                paid_amount REAL NOT NULL,
                baqaya REAL NOT NULL,
                sale_date TEXT NOT NULL
            )
        """)
        self.conn.commit()

    # ---------------- Stock methods ----------------
    def add_stock(self, suit_name, quantity, purchase_price):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO stock (suit_name, quantity, purchase_price, date_added) VALUES (?, ?, ?, ?)",
            (suit_name, quantity, purchase_price, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        self.conn.commit()

    def total_stock_quantity(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COALESCE(SUM(quantity), 0) FROM stock")
        return cur.fetchone()[0]

    # ---------------- Sales methods ----------------
    def add_sale(self, customer_name, suit_name, quantity, total_price, paid_amount):
        baqaya = total_price - paid_amount
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO sales
               (customer_name, suit_name, quantity, total_price, paid_amount, baqaya, sale_date)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (customer_name, suit_name, quantity, total_price, paid_amount, baqaya,
             datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        self.conn.commit()

    def get_all_sales(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id, customer_name, suit_name, quantity, total_price, paid_amount, baqaya, sale_date FROM sales ORDER BY id DESC")
        return cur.fetchall()

    def update_payment(self, sale_id, extra_payment):
        cur = self.conn.cursor()
        cur.execute("SELECT total_price, paid_amount FROM sales WHERE id=?", (sale_id,))
        row = cur.fetchone()
        if not row:
            return False
        total_price, paid_amount = row
        new_paid = paid_amount + extra_payment
        new_baqaya = total_price - new_paid
        cur.execute("UPDATE sales SET paid_amount=?, baqaya=? WHERE id=?", (new_paid, new_baqaya, sale_id))
        self.conn.commit()
        return True

    def summary(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COALESCE(SUM(quantity),0) FROM stock")
        total_suits_added = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(quantity),0) FROM sales")
        total_suits_sold = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(total_price),0) FROM sales")
        total_sale_amount = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(paid_amount),0) FROM sales")
        total_paid = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(baqaya),0) FROM sales")
        total_baqaya = cur.fetchone()[0]

        return {
            "total_suits_added": total_suits_added,
            "total_suits_sold": total_suits_sold,
            "remaining_stock": total_suits_added - total_suits_sold,
            "total_sale_amount": total_sale_amount,
            "total_paid": total_paid,
            "total_baqaya": total_baqaya,
        }


# ----------------------------------------------------------------------
# GUI APPLICATION
# ----------------------------------------------------------------------
class ClothShopApp:
    def __init__(self, root):
        self.root = root
        self.db = Database()

        self.root.title("Cloth Shop Management System")
        self.root.geometry("900x600")
        self.root.configure(bg="#f2f2f2")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook.Tab", font=("Segoe UI", 11, "bold"), padding=[15, 8])
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=26)

        # Top summary button (hamesha visible)
        top_frame = tk.Frame(root, bg="#2c3e50", height=55)
        top_frame.pack(fill="x")
        tk.Label(top_frame, text="🧵 Cloth Shop Manager", bg="#2c3e50", fg="white",
                  font=("Segoe UI", 16, "bold")).pack(side="left", padx=15, pady=10)
        tk.Button(top_frame, text="📊 Total Summary Dekhein", command=self.show_summary,
                   bg="#27ae60", fg="white", font=("Segoe UI", 11, "bold"),
                   relief="flat", padx=12, pady=6, cursor="hand2").pack(side="right", padx=15, pady=8)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.stock_tab = tk.Frame(notebook, bg="white")
        self.sale_tab = tk.Frame(notebook, bg="white")
        self.list_tab = tk.Frame(notebook, bg="white")

        notebook.add(self.stock_tab, text="📦 Stock Add (Suit Aaye)")
        notebook.add(self.sale_tab, text="💰 Sale Add (Suit Sale Ho)")
        notebook.add(self.list_tab, text="📋 Sales List")

        self.build_stock_tab()
        self.build_sale_tab()
        self.build_list_tab()

        notebook.bind("<<NotebookTabChanged>>", lambda e: self.refresh_sales_list())

    # ------------------------------------------------------------------
    # TAB 1: STOCK ADD
    # ------------------------------------------------------------------
    def build_stock_tab(self):
        frame = tk.Frame(self.stock_tab, bg="white", padx=30, pady=30)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Naye Suit Stock Me Add Karein", bg="white",
                  font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        tk.Label(frame, text="Suit Ka Naam / Design:", bg="white", font=("Segoe UI", 11)).grid(row=1, column=0, sticky="w", pady=8)
        self.stock_name_entry = tk.Entry(frame, font=("Segoe UI", 11), width=30)
        self.stock_name_entry.grid(row=1, column=1, pady=8)

        tk.Label(frame, text="Quantity (Kitne Suit):", bg="white", font=("Segoe UI", 11)).grid(row=2, column=0, sticky="w", pady=8)
        self.stock_qty_entry = tk.Entry(frame, font=("Segoe UI", 11), width=30)
        self.stock_qty_entry.grid(row=2, column=1, pady=8)

        tk.Label(frame, text="Purchase Price (Per Suit):", bg="white", font=("Segoe UI", 11)).grid(row=3, column=0, sticky="w", pady=8)
        self.stock_price_entry = tk.Entry(frame, font=("Segoe UI", 11), width=30)
        self.stock_price_entry.grid(row=3, column=1, pady=8)

        tk.Button(frame, text="✅ Stock Add Karein", command=self.add_stock,
                   bg="#2980b9", fg="white", font=("Segoe UI", 11, "bold"),
                   relief="flat", padx=15, pady=8, cursor="hand2").grid(row=4, column=0, columnspan=2, pady=25)

        self.stock_total_label = tk.Label(frame, text="", bg="white", font=("Segoe UI", 11, "bold"), fg="#2c3e50")
        self.stock_total_label.grid(row=5, column=0, columnspan=2, sticky="w")
        self.update_stock_total_label()

    def update_stock_total_label(self):
        total = self.db.total_stock_quantity()
        self.stock_total_label.config(text=f"Ab Tak Total Suits Shop Me Aaye: {total}")

    def add_stock(self):
        name = self.stock_name_entry.get().strip()
        qty = self.stock_qty_entry.get().strip()
        price = self.stock_price_entry.get().strip()

        if not name or not qty or not price:
            messagebox.showwarning("Missing Info", "Please tamam fields fill karein.")
            return
        try:
            qty = int(qty)
            price = float(price)
        except ValueError:
            messagebox.showerror("Invalid Input", "Quantity number aur Price number me honi chahiye.")
            return

        self.db.add_stock(name, qty, price)
        messagebox.showinfo("Success", f"{qty} '{name}' suit stock me add ho gaye.")

        self.stock_name_entry.delete(0, tk.END)
        self.stock_qty_entry.delete(0, tk.END)
        self.stock_price_entry.delete(0, tk.END)
        self.update_stock_total_label()

    # ------------------------------------------------------------------
    # TAB 2: SALE ADD
    # ------------------------------------------------------------------
    def build_sale_tab(self):
        frame = tk.Frame(self.sale_tab, bg="white", padx=30, pady=30)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Suit Sale Add Karein", bg="white",
                  font=("Segoe UI", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        labels = [
            ("Customer Ka Naam:", "sale_customer_entry"),
            ("Suit Ka Naam / Design:", "sale_suit_entry"),
            ("Quantity:", "sale_qty_entry"),
            ("Total Price (Rs.):", "sale_total_entry"),
            ("Payment Mili (Rs.):", "sale_paid_entry"),
        ]
        for i, (label_text, attr_name) in enumerate(labels, start=1):
            tk.Label(frame, text=label_text, bg="white", font=("Segoe UI", 11)).grid(row=i, column=0, sticky="w", pady=8)
            entry = tk.Entry(frame, font=("Segoe UI", 11), width=30)
            entry.grid(row=i, column=1, pady=8)
            setattr(self, attr_name, entry)

        # Baqaya auto calculate hoke yahan show hoga
        self.baqaya_preview_label = tk.Label(frame, text="Baqaya: Rs. 0", bg="white",
                                              font=("Segoe UI", 12, "bold"), fg="#c0392b")
        self.baqaya_preview_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(5, 15))

        self.sale_total_entry.bind("<KeyRelease>", self.preview_baqaya)
        self.sale_paid_entry.bind("<KeyRelease>", self.preview_baqaya)

        tk.Button(frame, text="✅ Sale Add Karein", command=self.add_sale,
                   bg="#27ae60", fg="white", font=("Segoe UI", 11, "bold"),
                   relief="flat", padx=15, pady=8, cursor="hand2").grid(row=7, column=0, columnspan=2, pady=10)

    def preview_baqaya(self, event=None):
        try:
            total = float(self.sale_total_entry.get())
        except ValueError:
            total = 0
        try:
            paid = float(self.sale_paid_entry.get())
        except ValueError:
            paid = 0
        baqaya = total - paid
        self.baqaya_preview_label.config(text=f"Baqaya: Rs. {baqaya:,.2f}")

    def add_sale(self):
        customer = self.sale_customer_entry.get().strip()
        suit = self.sale_suit_entry.get().strip()
        qty = self.sale_qty_entry.get().strip()
        total = self.sale_total_entry.get().strip()
        paid = self.sale_paid_entry.get().strip()

        if not customer or not suit or not qty or not total or not paid:
            messagebox.showwarning("Missing Info", "Please tamam fields fill karein.")
            return
        try:
            qty = int(qty)
            total = float(total)
            paid = float(paid)
        except ValueError:
            messagebox.showerror("Invalid Input", "Quantity, Total Price aur Payment sahi number me honi chahiye.")
            return

        self.db.add_sale(customer, suit, qty, total, paid)
        baqaya = total - paid
        messagebox.showinfo("Sale Added", f"Sale add ho gayi.\nCustomer: {customer}\nBaqaya: Rs. {baqaya:,.2f}")

        for e in [self.sale_customer_entry, self.sale_suit_entry, self.sale_qty_entry,
                  self.sale_total_entry, self.sale_paid_entry]:
            e.delete(0, tk.END)
        self.baqaya_preview_label.config(text="Baqaya: Rs. 0")
        self.refresh_sales_list()

    # ------------------------------------------------------------------
    # TAB 3: SALES LIST
    # ------------------------------------------------------------------
    def build_list_tab(self):
        frame = tk.Frame(self.list_tab, bg="white", padx=15, pady=15)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Saari Sales Ki List", bg="white",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))

        columns = ("id", "customer", "suit", "qty", "total", "paid", "baqaya", "date")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=15)

        headers = {
            "id": "ID", "customer": "Customer", "suit": "Suit",
            "qty": "Qty", "total": "Total (Rs.)", "paid": "Paid (Rs.)",
            "baqaya": "Baqaya (Rs.)", "date": "Date"
        }
        widths = {"id": 40, "customer": 130, "suit": 130, "qty": 50,
                  "total": 100, "paid": 100, "baqaya": 100, "date": 130}

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=widths[col], anchor="center")

        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Baqaya wapis lene ke liye chota panel
        pay_frame = tk.Frame(self.list_tab, bg="white", padx=15, pady=10)
        pay_frame.pack(fill="x")
        tk.Label(pay_frame, text="Selected Sale ID:", bg="white", font=("Segoe UI", 10)).pack(side="left")
        self.selected_id_label = tk.Label(pay_frame, text="-", bg="white", font=("Segoe UI", 10, "bold"))
        self.selected_id_label.pack(side="left", padx=(5, 20))

        tk.Label(pay_frame, text="Extra Payment (Rs.):", bg="white", font=("Segoe UI", 10)).pack(side="left")
        self.extra_payment_entry = tk.Entry(pay_frame, font=("Segoe UI", 10), width=12)
        self.extra_payment_entry.pack(side="left", padx=5)

        tk.Button(pay_frame, text="💵 Payment Update Karein", command=self.update_payment,
                   bg="#e67e22", fg="white", font=("Segoe UI", 10, "bold"),
                   relief="flat", padx=10, pady=5, cursor="hand2").pack(side="left", padx=10)

        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

        self.refresh_sales_list()

    def on_row_select(self, event=None):
        selected = self.tree.selection()
        if selected:
            values = self.tree.item(selected[0])["values"]
            self.selected_id_label.config(text=str(values[0]))

    def update_payment(self):
        sale_id_text = self.selected_id_label.cget("text")
        if sale_id_text == "-":
            messagebox.showwarning("No Selection", "Pehle Sales List se ek row select karein.")
            return
        extra = self.extra_payment_entry.get().strip()
        if not extra:
            messagebox.showwarning("Missing Info", "Extra payment amount likhein.")
            return
        try:
            extra = float(extra)
        except ValueError:
            messagebox.showerror("Invalid Input", "Payment sahi number me honi chahiye.")
            return

        sale_id = int(sale_id_text)
        success = self.db.update_payment(sale_id, extra)
        if success:
            messagebox.showinfo("Updated", "Payment update ho gayi aur baqaya recalculate ho gaya.")
            self.extra_payment_entry.delete(0, tk.END)
            self.refresh_sales_list()
        else:
            messagebox.showerror("Error", "Sale record nahi mila.")

    def refresh_sales_list(self):
        if not hasattr(self, "tree"):
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        for record in self.db.get_all_sales():
            sale_id, customer, suit, qty, total, paid, baqaya, date = record
            self.tree.insert("", "end", values=(
                sale_id, customer, suit, qty,
                f"{total:,.2f}", f"{paid:,.2f}", f"{baqaya:,.2f}", date
            ))
        self.update_stock_total_label()

    # ------------------------------------------------------------------
    # SUMMARY POPUP
    # ------------------------------------------------------------------
    def show_summary(self):
        s = self.db.summary()

        win = tk.Toplevel(self.root)
        win.title("Shop Summary")
        win.geometry("400x420")
        win.configure(bg="white")
        win.resizable(False, False)

        tk.Label(win, text="📊 Shop Ki Total Summary", bg="white",
                  font=("Segoe UI", 15, "bold")).pack(pady=(20, 15))

        rows = [
            ("Total Suits Shop Me Aaye:", s["total_suits_added"]),
            ("Total Suits Sale Hoye:", s["total_suits_sold"]),
            ("Baqi Stock (Bache Huye Suit):", s["remaining_stock"]),
            ("Total Sale Amount (Rs.):", f"{s['total_sale_amount']:,.2f}"),
            ("Total Payment Aayi (Rs.):", f"{s['total_paid']:,.2f}"),
            ("Total Baqaya (Pending) (Rs.):", f"{s['total_baqaya']:,.2f}"),
        ]

        for label_text, value in rows:
            row_frame = tk.Frame(win, bg="white")
            row_frame.pack(fill="x", padx=25, pady=8)
            tk.Label(row_frame, text=label_text, bg="white",
                      font=("Segoe UI", 11), anchor="w").pack(side="left")
            tk.Label(row_frame, text=str(value), bg="white",
                      font=("Segoe UI", 11, "bold"), fg="#2980b9", anchor="e").pack(side="right")

        tk.Button(win, text="Close", command=win.destroy,
                   bg="#c0392b", fg="white", font=("Segoe UI", 10, "bold"),
                   relief="flat", padx=15, pady=6, cursor="hand2").pack(pady=20)


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = ClothShopApp(root)
    root.mainloop()