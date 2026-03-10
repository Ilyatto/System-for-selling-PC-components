import sys
import re
from datetime import datetime, timedelta
import psycopg2

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QDialog, QDialogButtonBox, QFormLayout,
    QMessageBox, QTabWidget, QFrame, QScrollArea, QGridLayout,
    QGroupBox, QRadioButton, QDateEdit, QSpinBox, QDoubleSpinBox,
    QCheckBox, QSplitter, QAbstractItemView, QMenu, QStatusBar,
    QTextEdit
)
from PySide6.QtCharts import QChart, QChartView, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis
from PySide6.QtCore import Qt, QDate, Signal, Slot, QTimer, QMargins
from PySide6.QtGui import QAction, QFont, QColor, QPalette, QPainter


class Database:
    def __init__(self):
        self.conn_params = {
            'dbname': 'shop_db',
            'user': 'postgres',
            'password': '1234',
            'host': 'localhost',
            'port': '5432'
        }
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        try:
            self.conn = psycopg2.connect(**self.conn_params)
            self.cursor = self.conn.cursor()
        except Exception as e:
            raise

    def create_tables(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id SERIAL PRIMARY KEY,
                    company VARCHAR(255) NOT NULL UNIQUE,
                    contact VARCHAR(255) NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(20) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    price INTEGER NOT NULL,
                    price_str VARCHAR(50) NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    supplier_id INTEGER REFERENCES suppliers(id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id SERIAL PRIMARY KEY,
                    order_number VARCHAR(20) NOT NULL UNIQUE,
                    order_date DATE NOT NULL,
                    client VARCHAR(255) NOT NULL,
                    amount INTEGER NOT NULL,
                    amount_str VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'В обработке',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS order_items (
                    id SERIAL PRIMARY KEY,
                    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                    product_code VARCHAR(20) NOT NULL,
                    product_name VARCHAR(255) NOT NULL,
                    quantity INTEGER NOT NULL,
                    price INTEGER NOT NULL,
                    total INTEGER NOT NULL
                )
            """)

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS warehouse (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE UNIQUE,
                    product_code VARCHAR(20) NOT NULL,
                    product_name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    supplier VARCHAR(255),
                    purchase_price INTEGER NOT NULL,
                    purchase_price_str VARCHAR(50) NOT NULL,
                    retail_price INTEGER NOT NULL,
                    retail_price_str VARCHAR(50) NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.conn.commit()
        except Exception as e:
            self.conn.rollback()

    def get_all_suppliers(self):
        try:
            self.cursor.execute("""
                SELECT id, company, contact, phone, email, city 
                FROM suppliers 
                ORDER BY company
            """)
            suppliers = []
            for row in self.cursor.fetchall():
                suppliers.append({
                    'id': row[0],
                    'company': row[1],
                    'contact': row[2],
                    'phone': row[3],
                    'email': row[4],
                    'city': row[5]
                })
            return suppliers
        except Exception as e:
            print(f"Ошибка при получении поставщиков: {e}")
            return []

    def add_supplier(self, supplier):
        try:
            self.cursor.execute("""
                INSERT INTO suppliers (company, contact, phone, email, city)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (supplier['company'], supplier['contact'], supplier['phone'],
                  supplier['email'], supplier['city']))
            supplier_id = self.cursor.fetchone()[0]
            self.conn.commit()
            return supplier_id
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при добавлении поставщика: {e}")
            return None

    def update_supplier(self, supplier_id, supplier):
        try:
            self.cursor.execute("""
                UPDATE suppliers 
                SET company = %s, contact = %s, phone = %s, email = %s, city = %s
                WHERE id = %s
            """, (supplier['company'], supplier['contact'], supplier['phone'],
                  supplier['email'], supplier['city'], supplier_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при обновлении поставщика: {e}")
            return False

    def delete_supplier(self, supplier_id):
        try:
            self.cursor.execute("DELETE FROM suppliers WHERE id = %s", (supplier_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при удалении поставщика: {e}")
            return False

    def get_all_products(self):
        try:
            self.cursor.execute("""
                SELECT p.id, p.code, p.name, p.category, p.price, p.price_str, p.quantity,
                       s.id as supplier_id, s.company as supplier_name,
                       w.purchase_price, w.purchase_price_str, w.retail_price, w.retail_price_str
                FROM products p
                LEFT JOIN suppliers s ON p.supplier_id = s.id
                LEFT JOIN warehouse w ON p.id = w.product_id
                ORDER BY p.code
            """)
            products = []
            for row in self.cursor.fetchall():
                products.append({
                    'id': row[0],
                    'code': row[1],
                    'name': row[2],
                    'category': row[3],
                    'price': row[4],
                    'price_str': row[5],
                    'quantity': row[6],
                    'supplier_id': row[7],
                    'supplier_name': row[8],
                    'purchase_price': row[9] if row[9] else row[4],
                    'purchase_price_str': row[10] if row[10] else row[5],
                    'retail_price': row[11] if row[11] else row[4],
                    'retail_price_str': row[12] if row[12] else row[5]
                })
            return products
        except Exception as e:
            print(f"Ошибка при получении товаров: {e}")
            return []

    def add_product(self, product):
        try:
            self.cursor.execute("""
                INSERT INTO products (code, name, category, price, price_str, quantity, supplier_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (product['code'], product['name'], product['category'],
                  product['price'], product['price_str'], product['quantity'],
                  product.get('supplier_id')))
            product_id = self.cursor.fetchone()[0]

            supplier_name = None
            if product.get('supplier_id'):
                self.cursor.execute("SELECT company FROM suppliers WHERE id = %s", (product['supplier_id'],))
                result = self.cursor.fetchone()
                if result:
                    supplier_name = result[0]

            self.cursor.execute("""
                INSERT INTO warehouse (product_id, product_code, product_name, category,
                                      purchase_price, purchase_price_str,
                                      retail_price, retail_price_str, quantity, supplier)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (product_id, product['code'], product['name'], product['category'],
                  product.get('purchase_price', product['price']),
                  product.get('purchase_price_str', product['price_str']),
                  product['price'], product['price_str'],
                  product['quantity'], supplier_name))

            self.conn.commit()
            return product_id
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при добавлении товара: {e}")
            return None

    def update_product(self, product_id, product):
        try:
            self.cursor.execute("""
                UPDATE products 
                SET code = %s, name = %s, category = %s, price = %s, 
                    price_str = %s, quantity = %s, supplier_id = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (product['code'], product['name'], product['category'],
                  product['price'], product['price_str'], product['quantity'],
                  product.get('supplier_id'), product_id))

            supplier_name = None
            if product.get('supplier_id'):
                self.cursor.execute("SELECT company FROM suppliers WHERE id = %s", (product['supplier_id'],))
                result = self.cursor.fetchone()
                if result:
                    supplier_name = result[0]

            self.cursor.execute("""
                UPDATE warehouse
                SET product_code = %s, product_name = %s, category = %s,
                    purchase_price = %s, purchase_price_str = %s,
                    retail_price = %s, retail_price_str = %s, 
                    quantity = %s, supplier = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE product_id = %s
            """, (product['code'], product['name'], product['category'],
                  product.get('purchase_price', product['price']),
                  product.get('purchase_price_str', product['price_str']),
                  product['price'], product['price_str'],
                  product['quantity'], supplier_name, product_id))

            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при обновлении товара: {e}")
            return False

    def delete_product(self, product_id):
        try:
            self.cursor.execute("DELETE FROM warehouse WHERE product_id = %s", (product_id,))
            self.cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при удалении товара: {e}")
            return False

    def get_all_orders(self):
        try:
            self.cursor.execute("""
                SELECT id, order_number, order_date, client, amount, amount_str, status
                FROM orders 
                ORDER BY order_date DESC, order_number DESC
            """)
            orders = []
            for row in self.cursor.fetchall():
                order = {
                    'id': row[0],
                    'number': row[1],
                    'date': row[2].strftime('%d.%m.%Y') if row[2] else '',
                    'client': row[3],
                    'amount': row[4],
                    'amount_str': row[5],
                    'status': row[6],
                    'items': self.get_order_items(row[0])
                }
                orders.append(order)
            return orders
        except Exception as e:
            print(f"Ошибка при получении заказов: {e}")
            return []

    def get_order_items(self, order_id):
        try:
            self.cursor.execute("""
                SELECT product_code, product_name, quantity, price, total
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            items = []
            for row in self.cursor.fetchall():
                items.append({
                    'code': row[0],
                    'name': row[1],
                    'quantity': row[2],
                    'price': row[3],
                    'total': row[4]
                })
            return items
        except Exception as e:
            print(f"Ошибка при получении товаров заказа: {e}")
            return []

    def add_order(self, order):
        try:
            self.cursor.execute("""
                INSERT INTO orders (order_number, order_date, client, amount, amount_str, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (order['number'],
                  datetime.strptime(order['date'], '%d.%m.%Y').date(),
                  order['client'], order['amount'], order['amount_str'],
                  order['status']))
            order_id = self.cursor.fetchone()[0]

            for item in order['items']:
                self.cursor.execute("SELECT id FROM products WHERE code = %s", (str(item['code']),))
                product_row = self.cursor.fetchone()
                product_id = product_row[0] if product_row else None

                self.cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, product_code, product_name, 
                                            quantity, price, total)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (order_id, product_id, str(item['code']), item['name'],
                      item['quantity'], item['price'], item['quantity'] * item['price']))

                self.cursor.execute("""
                    UPDATE warehouse 
                    SET quantity = quantity - %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_code = %s
                """, (item['quantity'], str(item['code'])))

                self.cursor.execute("""
                    UPDATE products 
                    SET quantity = quantity - %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE code = %s
                """, (item['quantity'], str(item['code'])))

            self.conn.commit()
            return order_id
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при добавлении заказа: {e}")
            return None

    def update_order_status(self, order_id, status):
        try:
            self.cursor.execute("""
                UPDATE orders 
                SET status = %s
                WHERE id = %s
            """, (status, order_id))
            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при обновлении статуса заказа: {e}")
            return False

    def get_warehouse_items(self):
        try:
            self.cursor.execute("""
                SELECT id, product_code, product_name, category, supplier,
                       purchase_price, purchase_price_str, retail_price, 
                       retail_price_str, quantity
                FROM warehouse
                ORDER BY product_code
            """)
            items = []
            for row in self.cursor.fetchall():
                items.append({
                    'id': row[0],
                    'code': row[1],
                    'name': row[2],
                    'category': row[3],
                    'supplier': row[4] or "Не указан",
                    'purchase_price': row[5],
                    'purchase_price_str': row[6],
                    'retail_price': row[7],
                    'retail_price_str': row[8],
                    'quantity': row[9]
                })
            return items
        except Exception as e:
            print(f"Ошибка при получении склада: {e}")
            return []

    def update_warehouse_quantity(self, product_code, quantity_change, operation):
        try:
            if operation == '+':
                self.cursor.execute("""
                    UPDATE warehouse 
                    SET quantity = quantity + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE product_code = %s
                """, (quantity_change, product_code))

                self.cursor.execute("""
                    UPDATE products 
                    SET quantity = quantity + %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE code = %s
                """, (quantity_change, product_code))
            else:
                self.cursor.execute("SELECT quantity FROM warehouse WHERE product_code = %s", (product_code,))
                current = self.cursor.fetchone()
                if current and current[0] >= quantity_change:
                    self.cursor.execute("""
                        UPDATE warehouse 
                        SET quantity = quantity - %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE product_code = %s
                    """, (quantity_change, product_code))

                    self.cursor.execute("""
                        UPDATE products 
                        SET quantity = quantity - %s,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE code = %s
                    """, (quantity_change, product_code))
                else:
                    self.conn.rollback()
                    return False

            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Ошибка при обновлении склада: {e}")
            return False

    def close(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


class SupplierDialog(QDialog):
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setWindowTitle("Добавление поставщика" if not supplier else "Редактирование поставщика")
        self.setModal(True)
        self.resize(500, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton[text="Cancel"] {
                background-color: #f44336;
            }
            QPushButton[text="Cancel"]:hover {
                background-color: #da190b;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel("Информация о поставщике")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.company_edit = QLineEdit()
        self.contact_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.email_edit = QLineEdit()
        self.city_edit = QLineEdit()

        form_layout.addRow("Компания:", self.company_edit)
        form_layout.addRow("Контактное лицо:", self.contact_edit)
        form_layout.addRow("Телефон:", self.phone_edit)
        form_layout.addRow("Email:", self.email_edit)
        form_layout.addRow("Город:", self.city_edit)

        layout.addLayout(form_layout)

        if supplier:
            self.company_edit.setText(supplier['company'])
            self.contact_edit.setText(supplier['contact'])
            self.phone_edit.setText(supplier['phone'])
            self.email_edit.setText(supplier['email'])
            self.city_edit.setText(supplier['city'])

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return {
            'company': self.company_edit.text().strip(),
            'contact': self.contact_edit.text().strip(),
            'phone': self.phone_edit.text().strip(),
            'email': self.email_edit.text().strip(),
            'city': self.city_edit.text().strip()
        }


class ProductDialog(QDialog):
    def __init__(self, parent=None, product=None, next_code="000001"):
        super().__init__(parent)
        self.product = product
        self.next_code = next_code
        self.setWindowTitle("Добавление товара" if not product else "Редактирование товара")
        self.setModal(True)
        self.resize(500, 550)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 2px solid #4CAF50;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #4CAF50;
                selection-color: #ffffff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #4a4a4a;
                border: none;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton[text="Cancel"] {
                background-color: #f44336;
            }
            QPushButton[text="Cancel"]:hover {
                background-color: #da190b;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel(self.windowTitle())
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.code_edit = QLineEdit()
        self.code_edit.setReadOnly(True)

        self.name_edit = QLineEdit()

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Процессор", "Материнская плата", "Видеокарта",
                                      "Оперативная память", "SSD", "HDD",
                                      "Блок питания", "Система охлаждения", "Корпус"])

        self.purchase_price_edit = QSpinBox()
        self.purchase_price_edit.setRange(1, 9999999)
        self.purchase_price_edit.setSingleStep(100)
        self.purchase_price_edit.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.purchase_price_edit.setPrefix("₽ ")

        self.retail_price_edit = QSpinBox()
        self.retail_price_edit.setRange(1, 9999999)
        self.retail_price_edit.setSingleStep(100)
        self.retail_price_edit.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.retail_price_edit.setPrefix("₽ ")

        self.quantity_edit = QSpinBox()
        self.quantity_edit.setRange(0, 99999)
        self.quantity_edit.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Не выбран", None)
        if parent and hasattr(parent, 'window') and hasattr(parent.window(), 'suppliers_page'):
            suppliers = parent.window().suppliers_page.suppliers
            for supplier in suppliers:
                self.supplier_combo.addItem(supplier['company'], supplier['id'])

        form_layout.addRow("Код товара:", self.code_edit)
        form_layout.addRow("Наименование:", self.name_edit)
        form_layout.addRow("Категория:", self.category_combo)
        form_layout.addRow("Закупочная цена:", self.purchase_price_edit)
        form_layout.addRow("Розничная цена:", self.retail_price_edit)
        form_layout.addRow("Количество:", self.quantity_edit)
        form_layout.addRow("Поставщик:", self.supplier_combo)

        layout.addLayout(form_layout)

        if product:
            self.code_edit.setText(product['code'])
            self.name_edit.setText(product['name'])
            self.category_combo.setCurrentText(product['category'])
            self.purchase_price_edit.setValue(product.get('purchase_price', product['price']))
            self.retail_price_edit.setValue(product.get('retail_price', product['price']))
            self.quantity_edit.setValue(product['quantity'])

            if product.get('supplier_id'):
                index = self.supplier_combo.findData(product['supplier_id'])
                if index >= 0:
                    self.supplier_combo.setCurrentIndex(index)
        else:
            self.code_edit.setText(next_code)
            self.purchase_price_edit.setValue(1000)
            self.retail_price_edit.setValue(1500)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_and_accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите наименование товара")
            return

        if self.purchase_price_edit.value() <= 0:
            QMessageBox.warning(self, "Ошибка", "Закупочная цена должна быть больше 0")
            return

        if self.retail_price_edit.value() <= 0:
            QMessageBox.warning(self, "Ошибка", "Розничная цена должна быть больше 0")
            return

        if self.retail_price_edit.value() < self.purchase_price_edit.value():
            reply = QMessageBox.question(self, "Предупреждение",
                                         "Розничная цена меньше закупочной! Продолжить?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        self.accept()

    def get_data(self):
        supplier_id = self.supplier_combo.currentData()
        retail_price = self.retail_price_edit.value()

        return {
            'code': self.code_edit.text().strip(),
            'name': self.name_edit.text().strip(),
            'category': self.category_combo.currentText(),
            'price': retail_price,
            'purchase_price': self.purchase_price_edit.value(),
            'retail_price': retail_price,
            'price_str': f"{retail_price:,} руб.".replace(",", " "),
            'purchase_price_str': f"{self.purchase_price_edit.value():,} руб.".replace(",", " "),
            'retail_price_str': f"{retail_price:,} руб.".replace(",", " "),
            'quantity': self.quantity_edit.value(),
            'supplier_id': supplier_id if supplier_id is not None else None
        }

class OrderDialog(QDialog):
    def __init__(self, parent=None, products=None, next_number="001"):
        super().__init__(parent)
        self.products = products or []
        self.next_number = next_number
        self.selected_items = {}
        self.setWindowTitle("Создание нового заказа")
        self.setModal(True)
        self.resize(1000, 800)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QGroupBox {
                border: 2px solid #4a4a4a;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {
                border: 2px solid #4CAF50;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #4a4a4a;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
            }
            QTableWidget::item {
                padding: 5px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #000000;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton[text="Отмена"] {
                background-color: #f44336;
            }
            QPushButton[text="Отмена"]:hover {
                background-color: #da190b;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #4CAF50;
                selection-color: #ffffff;
            }
            QDateEdit::drop-down {
                border: none;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
            }
        """)

        main_layout = QVBoxLayout(self)

        title = QLabel("Создание нового заказа")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        info_group = QGroupBox("Информация о заказе")
        info_layout = QFormLayout(info_group)

        self.number_edit = QLineEdit()
        self.number_edit.setText(next_number)
        self.number_edit.setReadOnly(True)

        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")

        self.client_edit = QLineEdit()
        self.client_edit.setPlaceholderText("Введите ФИО клиента")

        info_layout.addRow("№ заказа:", self.number_edit)
        info_layout.addRow("Дата:", self.date_edit)
        info_layout.addRow("Клиент:", self.client_edit)

        main_layout.addWidget(info_group)

        products_group = QGroupBox("Выбор товаров")
        products_layout = QVBoxLayout(products_group)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels(["Код", "Наименование", "Категория", "Цена", "В наличии"])
        self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.products_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.products_table.setRowCount(len(self.products))
        for i, product in enumerate(self.products):
            self.products_table.setItem(i, 0, QTableWidgetItem(product['code']))
            self.products_table.setItem(i, 1, QTableWidgetItem(product['name']))
            self.products_table.setItem(i, 2, QTableWidgetItem(product['category']))

            price_item = QTableWidgetItem(product['price_str'])
            price_item.setForeground(QColor("#4CAF50"))
            self.products_table.setItem(i, 3, price_item)

            quantity_item = QTableWidgetItem(str(product['quantity']))
            if product['quantity'] > 0:
                quantity_item.setForeground(QColor("#4CAF50"))
            else:
                quantity_item.setForeground(QColor("#f44336"))
            self.products_table.setItem(i, 4, quantity_item)

        products_layout.addWidget(self.products_table)

        add_product_btn = QPushButton("Добавить выбранный товар")
        add_product_btn.clicked.connect(self.add_selected_product)
        products_layout.addWidget(add_product_btn)

        main_layout.addWidget(products_group)

        selected_group = QGroupBox("Выбранные товары")
        selected_layout = QVBoxLayout(selected_group)

        self.selected_table = QTableWidget()
        self.selected_table.setColumnCount(6)
        self.selected_table.setHorizontalHeaderLabels(["Код", "Наименование", "Кол-во", "Цена", "Сумма", ""])
        self.selected_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        selected_layout.addWidget(self.selected_table)

        main_layout.addWidget(selected_group)

        self.total_label = QLabel("Общая сумма: 0 руб.")
        self.total_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.total_label.setStyleSheet("color: #4CAF50; padding: 10px;")
        main_layout.addWidget(self.total_label)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Создать заказ")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)

    def add_selected_product(self):
        current_row = self.products_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите товар из списка")
            return

        code = self.products_table.item(current_row, 0).text()
        name = self.products_table.item(current_row, 1).text()
        price_text = self.products_table.item(current_row, 3).text()
        price = int(re.sub(r'[^0-9]', '', price_text))
        available = int(self.products_table.item(current_row, 4).text())

        if available <= 0:
            QMessageBox.warning(self, "Предупреждение", "Товара нет в наличии")
            return

        if code in self.selected_items:
            QMessageBox.warning(self, "Предупреждение", "Этот товар уже добавлен в заказ")
            return

        from PySide6.QtWidgets import QInputDialog
        quantity, ok = QInputDialog.getInt(self, "Количество",
                                           f"Введите количество для {name}:",
                                           1, 1, available, 1)
        if not ok:
            return

        total = price * quantity

        row = self.selected_table.rowCount()
        self.selected_table.insertRow(row)
        self.selected_table.setItem(row, 0, QTableWidgetItem(code))
        self.selected_table.setItem(row, 1, QTableWidgetItem(name))
        self.selected_table.setItem(row, 2, QTableWidgetItem(str(quantity)))

        price_item = QTableWidgetItem(f"{price:,} руб.".replace(",", " "))
        price_item.setForeground(QColor("#4CAF50"))
        self.selected_table.setItem(row, 3, price_item)

        total_item = QTableWidgetItem(f"{total:,} руб.".replace(",", " "))
        total_item.setForeground(QColor("#4CAF50"))
        self.selected_table.setItem(row, 4, total_item)

        remove_btn = QPushButton("✖")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        remove_btn.clicked.connect(lambda: self.remove_product(row))
        self.selected_table.setCellWidget(row, 5, remove_btn)

        self.selected_items[code] = {
            "code": code,
            "name": name,
            "quantity": quantity,
            "price": price
        }

        self.update_total()

    def remove_product(self, row):
        code = self.selected_table.item(row, 0).text()
        if code in self.selected_items:
            del self.selected_items[code]
        self.selected_table.removeRow(row)
        self.update_total()

    def update_total(self):
        total = sum(item['quantity'] * item['price'] for item in self.selected_items.values())
        self.total_label.setText(f"Общая сумма: {total:,} руб.".replace(",", " "))

    def get_data(self):
        date = self.date_edit.date().toString("dd.MM.yyyy")
        total_amount = sum(item['quantity'] * item['price'] for item in self.selected_items.values())

        return {
            "number": self.number_edit.text(),
            "date": date,
            "client": self.client_edit.text().strip(),
            "amount": total_amount,
            "amount_str": f"{total_amount:,} руб.".replace(",", " "),
            "status": "В обработке",
            "items": list(self.selected_items.values())
        }


class WarehouseOperationDialog(QDialog):
    def __init__(self, parent=None, warehouse_items=None, operation="+"):
        super().__init__(parent)
        self.warehouse_items = warehouse_items or []
        self.operation = operation
        self.setWindowTitle("Приход товара" if operation == "+" else "Расход товара")
        self.setModal(True)
        self.resize(500, 200)
        self.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QComboBox, QSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
                font-size: 14px;
            }
            QComboBox:focus, QSpinBox:focus {
                border: 2px solid #4CAF50;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #4CAF50;
                selection-color: #ffffff;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #4a4a4a;
                border: none;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton[text="Отмена"] {
                background-color: #f44336;
            }
            QPushButton[text="Отмена"]:hover {
                background-color: #da190b;
            }
        """)

        layout = QVBoxLayout(self)

        title = QLabel(self.windowTitle())
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.product_combo = QComboBox()
        for item in warehouse_items:
            self.product_combo.addItem(
                f"{item['code']} - {item['name']} (в наличии: {item['quantity']})",
                item['code']
            )

        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 99999)
        self.quantity_spin.setValue(1)
        self.quantity_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        form_layout.addRow("Товар:", self.product_combo)
        form_layout.addRow("Количество:", self.quantity_spin)

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        execute_btn = QPushButton("Выполнить")
        execute_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(execute_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def get_data(self):
        return {
            'code': self.product_combo.currentData(),
            'quantity': self.quantity_spin.value()
        }


class MainWindow(QMainWindow):
    order_status_changed = Signal()

    def __init__(self):
        super().__init__()
        self.db = None
        self.init_db()
        self.init_ui()
        self.apply_dark_theme()

        self.order_status_changed.connect(self.main_page.load_data)

    def init_db(self):
        try:
            self.db = Database()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения к БД",
                                 f"Не удалось подключиться к базе данных.\n\n"
                                 f"Ошибка: {e}\n\n"
                                 f"Проверьте настройки подключения")
            sys.exit(1)

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QTabWidget::pane {
                border: 1px solid #3c3c3c;
                background-color: #2b2b2b;
                border-radius: 3px;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                padding: 8px 15px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4a4a4a;
                border-bottom-color: #4a4a4a;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
            QGroupBox {
                border: 2px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton[text="Отмена"] {
                background-color: #f44336;
            }
            QPushButton[text="Отмена"]:hover {
                background-color: #da190b;
            }
            QLineEdit, QComboBox, QSpinBox, QDateEdit {
                border: 1px solid #3c3c3c;
                border-radius: 3px;
                padding: 5px;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDateEdit:focus {
                border: 2px solid #4CAF50;
            }
            QTableWidget {
                border: 1px solid #3c3c3c;
                background-color: #2b2b2b;
                gridline-color: #3c3c3c;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 5px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #000000;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                border: 1px solid #2b2b2b;
                padding: 5px;
                font-weight: bold;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QScrollBar:vertical {
                border: 1px solid #3c3c3c;
                background: #2b2b2b;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #4a4a4a;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #5a5a5a;
            }
            QFrame {
                color: #ffffff;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #000000;
                selection-color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
            }
            QDialog {
                background-color: #2b2b2b;
            }
            QDialog QLabel {
                color: #ffffff;
            }
            QDialog QLineEdit, QDialog QComboBox, QDialog QSpinBox, QDialog QDateEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }
            QDialog QPushButton {
                min-width: 80px;
            }
            QDialog QGroupBox {
                color: #ffffff;
                border: 2px solid #4a4a4a;
            }
            QTextEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
            }
            QDateEdit::drop-down {
                border: none;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #4a4a4a;
                border: none;
                border-radius: 2px;
                width: 15px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #5a5a5a;
            }
        """)

    def init_ui(self):
        self.setWindowTitle("Информационная система для компании по продаже комплектующих для ПК")
        self.setGeometry(100, 100, 1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        main_layout.addWidget(self.tab_widget)

        self.main_page = MainPage(self.db)
        self.catalog_page = CatalogPage(self.db)
        self.orders_page = OrdersPage(self.db)
        self.suppliers_page = SuppliersPage(self.db)
        self.reports_page = ReportsPage(self.db)
        self.warehouse_page = WarehousePage(self.db)

        self.tab_widget.addTab(self.main_page, "Главная")
        self.tab_widget.addTab(self.catalog_page, "Каталог")
        self.tab_widget.addTab(self.orders_page, "Заказы")
        self.tab_widget.addTab(self.suppliers_page, "Поставщики")
        self.tab_widget.addTab(self.warehouse_page, "Склад")
        self.tab_widget.addTab(self.reports_page, "Отчеты")

        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        if index == 1:
            self.catalog_page.load_products()
        elif index == 2:
            self.orders_page.load_orders()
        elif index == 3:
            self.suppliers_page.load_suppliers()
        elif index == 4:
            self.warehouse_page.load_warehouse()

    def closeEvent(self, event):
        if self.db:
            self.db.close()
        event.accept()

class MainPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3c3c3c;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
            QTableWidget::item {
                color: #ffffff;
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
            QFrame {
                background-color: #2b2b2b;
                border: none;
            }
        """)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("Главный экран")
        title.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #ffffff; margin-bottom: 10px;")
        layout.addWidget(title)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)

        self.orders_card = self.create_stat_card("Количество заказов за день", "0", "#3498db")
        self.revenue_card = self.create_stat_card("Продажи за день", "0 руб.", "#2ecc71")
        self.best_product_card = self.create_stat_card("Самый продаваемый товар за день", "Нет данных", "#e74c3c")

        stats_layout.addWidget(self.orders_card)
        stats_layout.addWidget(self.revenue_card)
        stats_layout.addWidget(self.best_product_card)

        layout.addLayout(stats_layout)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #3c3c3c; max-height: 2px; margin: 20px 0;")
        layout.addWidget(separator)

        orders_label = QLabel("Последние заказы")
        orders_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        orders_label.setStyleSheet("color: #ffffff; margin-bottom: 15px;")
        layout.addWidget(orders_label)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(3)
        self.orders_table.setHorizontalHeaderLabels(["№ заказа", "Сумма", "Статус"])
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.orders_table.setMinimumHeight(150)
        layout.addWidget(self.orders_table)

        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #3c3c3c; max-height: 2px; margin: 20px 0;")
        layout.addWidget(separator2)

        chart_label = QLabel("График продаж за неделю")
        chart_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        chart_label.setStyleSheet("color: #ffffff; margin-bottom: 15px;")
        layout.addWidget(chart_label)

        self.chart_container = QFrame()
        self.chart_container.setStyleSheet("""
            QFrame {
                background-color: #2b2b2b;
                border: none;
                min-height: 300px;
            }
        """)

        chart_layout = QVBoxLayout(self.chart_container)
        chart_layout.setSpacing(5)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        self.chart = QChart()
        self.chart.setBackgroundVisible(False)
        self.chart.legend().setVisible(False)
        self.chart.setTitle("")
        self.chart.setMargins(QMargins(0, 0, 0, 0))

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setMinimumHeight(250)
        self.chart_view.setMaximumHeight(280)

        chart_layout.addWidget(self.chart_view)
        layout.addWidget(self.chart_container)

        layout.addStretch()

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 10px;
                padding: 20px;
                border: none;
                min-width: 200px;
            }}
            QLabel {{
                color: white;
                background-color: transparent;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(10)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)

        card.value_label = value_label

        return card

    def load_data(self):
        orders = self.db.get_all_orders()

        today = datetime.now().strftime("%d.%m.%Y")

        today_completed_orders = [
            o for o in orders
            if o['date'] == today and o['status'] == "Выполнен"
        ]

        if hasattr(self.orders_card, 'value_label'):
            self.orders_card.value_label.setText(str(len(today_completed_orders)))

        today_revenue = sum(o['amount'] for o in today_completed_orders)
        if hasattr(self.revenue_card, 'value_label'):
            self.revenue_card.value_label.setText(f"{today_revenue:,} руб.".replace(",", " "))

        product_sales = {}
        for order in today_completed_orders:
            for item in order['items']:
                if item['name'] in product_sales:
                    product_sales[item['name']] += item['quantity']
                else:
                    product_sales[item['name']] = item['quantity']

        best_product = "Нет продаж"
        max_quantity = 0
        for product, quantity in product_sales.items():
            if quantity > max_quantity:
                max_quantity = quantity
                best_product = product

        if hasattr(self.best_product_card, 'value_label'):
            self.best_product_card.value_label.setText(best_product)

        recent_orders = sorted(orders, key=lambda x: x['date'], reverse=True)[:5]
        self.orders_table.setRowCount(len(recent_orders))

        for i, order in enumerate(recent_orders):
            number_item = QTableWidgetItem(order['number'])
            number_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            number_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.orders_table.setItem(i, 0, number_item)

            amount_item = QTableWidgetItem(order['amount_str'])
            amount_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.orders_table.setItem(i, 1, amount_item)

            status_item = QTableWidgetItem(order['status'])
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if order['status'] == "Выполнен":
                status_item.setForeground(QColor("#4CAF50"))
            elif order['status'] == "Отменен":
                status_item.setForeground(QColor("#f44336"))
            else:
                status_item.setForeground(QColor("#FF9800"))

            self.orders_table.setItem(i, 2, status_item)

        self.update_sales_chart()

    def update_sales_chart(self):
        orders = self.db.get_all_orders()

        from datetime import timedelta

        today = datetime.now()

        days = []
        values = []

        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

        for i in range(6, -1, -1):
            day = today - timedelta(days=i)

            full_date = day.strftime("%d.%m.%Y")
            days.append(weekdays[day.weekday()])

            daily_sales = 0

            for order in orders:
                if order['date'] == full_date and order['status'] == "Выполнен":
                    daily_sales += order['amount']

            values.append(daily_sales)

        self.chart.removeAllSeries()

        bar_set = QBarSet("Продажи")

        for value in values:
            bar_set.append(value)

        bar_set.setColor(QColor("#4CAF50"))

        series = QBarSeries()
        series.append(bar_set)
        series.setLabelsVisible(True)
        series.setLabelsPosition(QBarSeries.LabelsOutsideEnd)
        series.setLabelsFormat("@value")

        self.chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(days)
        axis_x.setLabelsColor(QColor("#ffffff"))
        axis_x.setGridLineVisible(False)
        axis_x.setLabelsFont(QFont("Arial", 9))

        axis_y = QValueAxis()
        axis_y.setVisible(False)
        axis_y.setLabelsVisible(False)
        axis_y.setGridLineVisible(False)
        axis_y.setTickCount(0)

        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)

        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        self.chart.setBackgroundVisible(False)
        self.chart.setPlotAreaBackgroundVisible(False)

        self.chart.setMinimumSize(500, 200)

class CatalogPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.products = []
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                border: 2px solid #3c3c3c;
            }
            QLineEdit, QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3c3c3c;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #000000;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.init_ui()
        self.load_products()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Каталог товаров")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout(filter_group)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по названию...")
        self.search_edit.textChanged.connect(self.apply_filters)

        self.category_combo = QComboBox()
        self.category_combo.addItems(["Все", "Процессор", "Материнская плата",
                                      "Видеокарта", "Оперативная память", "SSD"])
        self.category_combo.currentTextChanged.connect(self.apply_filters)

        self.availability_combo = QComboBox()
        self.availability_combo.addItems(["Все", "В наличии", "Нет в наличии"])
        self.availability_combo.currentTextChanged.connect(self.apply_filters)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["По названию", "По цене (возр.)", "По цене (убыв.)"])
        self.sort_combo.currentTextChanged.connect(self.apply_filters)

        filter_layout.addWidget(QLabel("Поиск:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(QLabel("Категория:"))
        filter_layout.addWidget(self.category_combo)
        filter_layout.addWidget(QLabel("Наличие:"))
        filter_layout.addWidget(self.availability_combo)
        filter_layout.addWidget(QLabel("Сортировка:"))
        filter_layout.addWidget(self.sort_combo)
        filter_layout.addStretch()

        layout.addWidget(filter_group)

        self.products_table = QTableWidget()
        self.products_table.setColumnCount(6)
        self.products_table.setHorizontalHeaderLabels(["Код", "Наименование", "Категория",
                                                       "Цена", "Наличие", "Действия"])
        self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.products_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.products_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.products_table)

        add_btn = QPushButton("Добавить новый товар")
        add_btn.clicked.connect(self.add_product)
        layout.addWidget(add_btn)

    def load_products(self):
        self.products = self.db.get_all_products()
        self.refresh_table()

    def refresh_table(self):
        self.products_table.setRowCount(len(self.products))

        for i, product in enumerate(self.products):
            self.products_table.setItem(i, 0, QTableWidgetItem(product['code']))
            self.products_table.setItem(i, 1, QTableWidgetItem(product['name']))
            self.products_table.setItem(i, 2, QTableWidgetItem(product['category']))

            price_item = QTableWidgetItem(product['price_str'])
            price_item.setForeground(QColor("#4CAF50"))
            self.products_table.setItem(i, 3, price_item)

            quantity_item = QTableWidgetItem(str(product['quantity']))
            if product['quantity'] > 0:
                quantity_item.setForeground(QColor("#4CAF50"))
            else:
                quantity_item.setForeground(QColor("#f44336"))
            self.products_table.setItem(i, 4, quantity_item)

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet("background-color: #3498db; padding: 5px;")
            edit_btn.clicked.connect(lambda checked, idx=i: self.edit_product(idx))

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet("background-color: #f44336; padding: 5px;")
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_product(idx))

            layout.addWidget(edit_btn)
            layout.addWidget(delete_btn)

            self.products_table.setCellWidget(i, 5, widget)

    def apply_filters(self):
        search_text = self.search_edit.text().lower()
        category = self.category_combo.currentText()
        availability = self.availability_combo.currentText()
        sort_by = self.sort_combo.currentText()

        filtered = []
        for product in self.products:
            if search_text and search_text not in product['name'].lower():
                continue
            if category != "Все" and product['category'] != category:
                continue
            if availability == "В наличии" and product['quantity'] <= 0:
                continue
            if availability == "Нет в наличии" and product['quantity'] > 0:
                continue
            filtered.append(product)

        if sort_by == "По названию":
            filtered.sort(key=lambda x: x['name'])
        elif sort_by == "По цене (возр.)":
            filtered.sort(key=lambda x: x['price'])
        elif sort_by == "По цене (убыв.)":
            filtered.sort(key=lambda x: x['price'], reverse=True)

        self.display_filtered(filtered)

    def display_filtered(self, filtered):
        self.products_table.setRowCount(len(filtered))

        for i, product in enumerate(filtered):
            self.products_table.setItem(i, 0, QTableWidgetItem(product['code']))
            self.products_table.setItem(i, 1, QTableWidgetItem(product['name']))
            self.products_table.setItem(i, 2, QTableWidgetItem(product['category']))

            price_item = QTableWidgetItem(product['price_str'])
            price_item.setForeground(QColor("#4CAF50"))
            self.products_table.setItem(i, 3, price_item)

            quantity_item = QTableWidgetItem(str(product['quantity']))
            if product['quantity'] > 0:
                quantity_item.setForeground(QColor("#4CAF50"))
            else:
                quantity_item.setForeground(QColor("#f44336"))
            self.products_table.setItem(i, 4, quantity_item)

    def generate_next_code(self):
        if not self.products:
            return "000001"
        max_code = 0
        for product in self.products:
            try:
                code_num = int(product['code'])
                max_code = max(max_code, code_num)
            except ValueError:
                pass
        return f"{max_code + 1:06d}"

    def add_product(self):
        next_code = self.generate_next_code()
        dialog = ProductDialog(self, next_code=next_code)

        if dialog.exec():
            data = dialog.get_data()

            if not data['name']:
                QMessageBox.warning(self, "Ошибка", "Заполните наименование товара")
                return

            for product in self.products:
                if product['code'] == data['code']:
                    QMessageBox.warning(self, "Ошибка", f"Товар с кодом {data['code']} уже существует")
                    return

            product_id = self.db.add_product(data)
            if product_id:
                self.load_products()
                QMessageBox.information(self, "Успешно", f"Товар '{data['name']}' успешно добавлен")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить товар")

    def edit_product(self, index):
        product = self.products[index]
        dialog = ProductDialog(self, product=product)

        if dialog.exec():
            data = dialog.get_data()
            data['price_str'] = f"{data['price']:,} руб.".replace(",", " ")

            if self.db.update_product(product['id'], data):
                self.load_products()

                QMessageBox.information(self, "Успешно",
                                        f"Товар '{data['name']}' успешно обновлен\n"
                                        f"Поставщик: {self.get_supplier_name(data.get('supplier_id'))}")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить товар")

    def get_supplier_name(self, supplier_id):
        if not supplier_id:
            return "Не указан"
        for supplier in self.window().suppliers_page.suppliers:
            if supplier['id'] == supplier_id:
                return supplier['company']
        return "Не указан"

    def delete_product(self, index):
        product = self.products[index]
        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы действительно хотите удалить товар\n{product['code']} - {product['name']}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_product(product['id']):
                self.load_products()
                QMessageBox.information(self, "Успешно", "Товар удален")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить товар")


class OrdersPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.orders = []
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                border: 2px solid #3c3c3c;
            }
            QLineEdit, QComboBox, QDateEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3c3c3c;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #000000;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton[text="Отмена"] {
                background-color: #f44336;
            }
            QPushButton[text="Отмена"]:hover {
                background-color: #da190b;
            }
        """)
        self.init_ui()
        self.load_orders()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Заказы клиентов")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout(filter_group)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по номеру или клиенту...")
        self.search_edit.textChanged.connect(self.apply_filters)

        self.status_combo = QComboBox()
        self.status_combo.addItems(["Все", "Выполнен", "В обработке", "Отменен"])
        self.status_combo.currentTextChanged.connect(self.apply_filters)

        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.dateChanged.connect(self.apply_filters)

        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.dateChanged.connect(self.apply_filters)

        filter_layout.addWidget(QLabel("Поиск:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(QLabel("Статус:"))
        filter_layout.addWidget(self.status_combo)
        filter_layout.addWidget(QLabel("С:"))
        filter_layout.addWidget(self.date_from)
        filter_layout.addWidget(QLabel("По:"))
        filter_layout.addWidget(self.date_to)
        filter_layout.addStretch()

        layout.addWidget(filter_group)

        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)
        self.orders_table.setHorizontalHeaderLabels(["№ заказа", "Дата", "Клиент",
                                                     "Сумма", "Статус", "Детали", "Изм. статус"])
        self.orders_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.orders_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.orders_table)

        create_btn = QPushButton("Создать новый заказ")
        create_btn.clicked.connect(self.create_order)
        layout.addWidget(create_btn)

    def load_orders(self):
        self.orders = self.db.get_all_orders()
        self.refresh_table()

    def refresh_table(self):
        self.orders_table.setRowCount(len(self.orders))

        for i, order in enumerate(self.orders):
            self.orders_table.setItem(i, 0, QTableWidgetItem(order['number']))
            self.orders_table.setItem(i, 1, QTableWidgetItem(order['date']))
            self.orders_table.setItem(i, 2, QTableWidgetItem(order['client']))
            self.orders_table.setItem(i, 3, QTableWidgetItem(order['amount_str']))

            status_item = QTableWidgetItem(order['status'])
            if order['status'] == "Выполнен":
                status_item.setForeground(QColor("#4CAF50"))
            elif order['status'] == "Отменен":
                status_item.setForeground(QColor("#f44336"))
            else:
                status_item.setForeground(QColor("#FF9800"))
            self.orders_table.setItem(i, 4, status_item)

            details_btn = QPushButton("🔍")
            details_btn.setStyleSheet("background-color: #3498db; padding: 5px;")
            details_btn.clicked.connect(lambda checked, idx=i: self.show_order_details(idx))
            self.orders_table.setCellWidget(i, 5, details_btn)

            status_btn = QPushButton("↻")
            status_btn.setStyleSheet("background-color: #f39c12; padding: 5px;")
            status_btn.clicked.connect(lambda checked, idx=i: self.change_order_status(idx))
            self.orders_table.setCellWidget(i, 6, status_btn)

    def apply_filters(self):
        search_text = self.search_edit.text().lower()
        status_filter = self.status_combo.currentText()
        date_from = self.date_from.date().toString("dd.MM.yyyy")
        date_to = self.date_to.date().toString("dd.MM.yyyy")

        def parse_date(date_str):
            try:
                day, month, year = map(int, date_str.split('.'))
                return datetime(year, month, day)
            except:
                return None

        date_from_obj = parse_date(date_from)
        date_to_obj = parse_date(date_to)

        filtered = []
        for order in self.orders:
            if search_text:
                if search_text not in order['number'].lower() and search_text not in order['client'].lower():
                    continue
            if status_filter != "Все" and order['status'] != status_filter:
                continue
            if date_from_obj and date_to_obj:
                order_date = parse_date(order['date'])
                if order_date and (order_date < date_from_obj or order_date > date_to_obj):
                    continue
            filtered.append(order)

        self.display_filtered(filtered)

    def display_filtered(self, filtered):
        self.orders_table.setRowCount(len(filtered))

        for i, order in enumerate(filtered):
            self.orders_table.setItem(i, 0, QTableWidgetItem(order['number']))
            self.orders_table.setItem(i, 1, QTableWidgetItem(order['date']))
            self.orders_table.setItem(i, 2, QTableWidgetItem(order['client']))
            self.orders_table.setItem(i, 3, QTableWidgetItem(order['amount_str']))

            status_item = QTableWidgetItem(order['status'])
            if order['status'] == "Выполнен":
                status_item.setForeground(QColor("#4CAF50"))
            elif order['status'] == "Отменен":
                status_item.setForeground(QColor("#f44336"))
            else:
                status_item.setForeground(QColor("#FF9800"))
            self.orders_table.setItem(i, 4, status_item)

    def show_order_details(self, index):
        if index < 0 or index >= len(self.orders):
            return

        order = self.orders[index]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Детали заказа №{order['number']}")
        dialog.resize(600, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QTextEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3c3c3c;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        layout = QVBoxLayout(dialog)

        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(150)

        info = f"""Заказ №{order['number']}
Дата: {order['date']}
Клиент: {order['client']}
Статус: {order['status']}
Общая сумма: {order['amount_str']}"""

        info_text.setText(info)
        layout.addWidget(info_text)

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Код", "Наименование", "Кол-во", "Цена", "Сумма"])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        items = order['items']
        table.setRowCount(len(items))

        for i, item in enumerate(items):
            table.setItem(i, 0, QTableWidgetItem(item['code']))
            table.setItem(i, 1, QTableWidgetItem(item['name']))
            table.setItem(i, 2, QTableWidgetItem(str(item['quantity'])))

            price_item = QTableWidgetItem(f"{item['price']:,} руб.".replace(",", " "))
            price_item.setForeground(QColor("#4CAF50"))
            table.setItem(i, 3, price_item)

            total = item['quantity'] * item['price']
            total_item = QTableWidgetItem(f"{total:,} руб.".replace(",", " "))
            total_item.setForeground(QColor("#4CAF50"))
            table.setItem(i, 4, total_item)

        layout.addWidget(table)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def change_order_status(self, index):
        if index < 0 or index >= len(self.orders):
            return

        order = self.orders[index]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Изменение статуса заказа №{order['number']}")
        dialog.resize(300, 200)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 14px;
            }
            QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 3px;
                padding: 8px;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                width: 0;
                height: 0;
            }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #ffffff;
                selection-background-color: #4CAF50;
                selection-color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton[text="Cancel"] {
                background-color: #f44336;
            }
            QPushButton[text="Cancel"]:hover {
                background-color: #da190b;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)

        title_label = QLabel(f"Заказ №{order['number']}")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        status_label = QLabel("Выберите новый статус:")
        status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(status_label)

        status_combo = QComboBox()
        status_combo.addItems(["Выполнен", "В обработке", "Отменен"])
        status_combo.setCurrentText(order['status'])

        status_combo.setItemData(0, QColor("#4CAF50"), Qt.ItemDataRole.ForegroundRole)
        status_combo.setItemData(1, QColor("#FF9800"), Qt.ItemDataRole.ForegroundRole)
        status_combo.setItemData(2, QColor("#f44336"), Qt.ItemDataRole.ForegroundRole)

        layout.addWidget(status_combo)

        button_layout = QHBoxLayout()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_status = status_combo.currentText()
            if self.db.update_order_status(order['id'], new_status):
                self.load_orders()

                main_window = self.window()
                if hasattr(main_window, 'main_page'):
                    main_window.main_page.load_data()

                QMessageBox.information(self, "Успешно",
                                        f"Статус заказа №{order['number']} изменен на '{new_status}'")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось изменить статус заказа")

    def create_order(self):
        catalog_page = self.window().catalog_page
        products = catalog_page.products

        if not products:
            QMessageBox.warning(self, "Предупреждение", "В каталоге нет товаров")
            return

        next_number = self.generate_next_order_number()
        dialog = OrderDialog(self, products, next_number)

        if dialog.exec():
            data = dialog.get_data()
            if not data['client']:
                QMessageBox.warning(self, "Ошибка", "Заполните все поля")
                return

            order_id = self.db.add_order(data)
            if order_id:
                self.load_orders()
                catalog_page.load_products()

                main_window = self.window()
                if hasattr(main_window, 'main_page'):
                    main_window.main_page.load_data()

                QMessageBox.information(self, "Успешно", f"Заказ №{data['number']} успешно создан")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось создать заказ")

    def generate_next_order_number(self):
        if not self.orders:
            return "001"
        max_num = 0
        for order in self.orders:
            try:
                num = int(order['number'])
                max_num = max(max_num, num)
            except ValueError:
                pass
        return f"{max_num + 1:03d}"


class SuppliersPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.suppliers = []
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                border: 2px solid #3c3c3c;
            }
            QLineEdit, QComboBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3c3c3c;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #000000;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton[text="Отмена"] {
                background-color: #f44336;
            }
            QPushButton[text="Отмена"]:hover {
                background-color: #da190b;
            }
        """)
        self.init_ui()
        self.load_suppliers()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Поставщики")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        filter_group = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout(filter_group)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по компании, контакту, городу...")
        self.search_edit.textChanged.connect(self.apply_filters)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["По названию", "По контактному лицу", "По городу"])
        self.sort_combo.currentTextChanged.connect(self.apply_filters)

        filter_layout.addWidget(QLabel("Поиск:"))
        filter_layout.addWidget(self.search_edit)
        filter_layout.addWidget(QLabel("Сортировка:"))
        filter_layout.addWidget(self.sort_combo)
        filter_layout.addStretch()

        layout.addWidget(filter_group)

        self.suppliers_table = QTableWidget()
        self.suppliers_table.setColumnCount(7)
        self.suppliers_table.setHorizontalHeaderLabels(["Компания", "Контактное лицо", "Телефон",
                                                        "Email", "Город", "Ред.", "Уд."])
        self.suppliers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.suppliers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.suppliers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.suppliers_table)

        add_btn = QPushButton("Добавить поставщика")
        add_btn.clicked.connect(self.add_supplier)
        layout.addWidget(add_btn)

    def load_suppliers(self):
        self.suppliers = self.db.get_all_suppliers()
        self.refresh_table()

    def refresh_table(self):
        self.suppliers_table.setRowCount(len(self.suppliers))

        for i, supplier in enumerate(self.suppliers):
            self.suppliers_table.setItem(i, 0, QTableWidgetItem(supplier['company']))
            self.suppliers_table.setItem(i, 1, QTableWidgetItem(supplier['contact']))
            self.suppliers_table.setItem(i, 2, QTableWidgetItem(supplier['phone']))
            self.suppliers_table.setItem(i, 3, QTableWidgetItem(supplier['email']))
            self.suppliers_table.setItem(i, 4, QTableWidgetItem(supplier['city']))

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet("background-color: #3498db; padding: 5px;")
            edit_btn.clicked.connect(lambda checked, idx=i: self.edit_supplier(idx))
            self.suppliers_table.setCellWidget(i, 5, edit_btn)

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet("background-color: #f44336; padding: 5px;")
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_supplier(idx))
            self.suppliers_table.setCellWidget(i, 6, delete_btn)

    def apply_filters(self):
        search_text = self.search_edit.text().lower()
        sort_by = self.sort_combo.currentText()

        filtered = []
        for supplier in self.suppliers:
            if search_text:
                if (search_text in supplier['company'].lower() or
                        search_text in supplier['contact'].lower() or
                        search_text in supplier['city'].lower() or
                        search_text in supplier['phone'] or
                        search_text in supplier['email'].lower()):
                    filtered.append(supplier)
            else:
                filtered.append(supplier)

        if sort_by == "По названию":
            filtered.sort(key=lambda x: x['company'])
        elif sort_by == "По контактному лицу":
            filtered.sort(key=lambda x: x['contact'])
        elif sort_by == "По городу":
            filtered.sort(key=lambda x: x['city'])

        self.display_filtered(filtered)

    def display_filtered(self, filtered):
        self.suppliers_table.setRowCount(len(filtered))

        for i, supplier in enumerate(filtered):
            self.suppliers_table.setItem(i, 0, QTableWidgetItem(supplier['company']))
            self.suppliers_table.setItem(i, 1, QTableWidgetItem(supplier['contact']))
            self.suppliers_table.setItem(i, 2, QTableWidgetItem(supplier['phone']))
            self.suppliers_table.setItem(i, 3, QTableWidgetItem(supplier['email']))
            self.suppliers_table.setItem(i, 4, QTableWidgetItem(supplier['city']))

    def add_supplier(self):
        dialog = SupplierDialog(self)

        if dialog.exec():
            data = dialog.get_data()
            if not all(data.values()):
                QMessageBox.warning(self, "Ошибка", "Заполните все поля")
                return

            if "@" not in data['email'] or "." not in data['email']:
                QMessageBox.warning(self, "Ошибка", "Введите корректный email адрес")
                return

            for s in self.suppliers:
                if s['company'].lower() == data['company'].lower():
                    QMessageBox.warning(self, "Ошибка", f"Поставщик '{data['company']}' уже существует")
                    return

            supplier_id = self.db.add_supplier(data)
            if supplier_id:
                self.load_suppliers()
                QMessageBox.information(self, "Успешно", f"Поставщик '{data['company']}' успешно добавлен")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить поставщика")

    def edit_supplier(self, index):
        supplier = self.suppliers[index]
        dialog = SupplierDialog(self, supplier)

        if dialog.exec():
            data = dialog.get_data()
            if not all(data.values()):
                QMessageBox.warning(self, "Ошибка", "Заполните все поля")
                return

            if "@" not in data['email'] or "." not in data['email']:
                QMessageBox.warning(self, "Ошибка", "Введите корректный email адрес")
                return

            for i, s in enumerate(self.suppliers):
                if i != index and s['company'].lower() == data['company'].lower():
                    QMessageBox.warning(self, "Ошибка", f"Поставщик '{data['company']}' уже существует")
                    return

            if self.db.update_supplier(supplier['id'], data):
                self.load_suppliers()
                QMessageBox.information(self, "Успешно", f"Поставщик '{data['company']}' успешно обновлен")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось обновить поставщика")

    def delete_supplier(self, index):
        supplier = self.suppliers[index]
        reply = QMessageBox.question(self, "Подтверждение удаления",
                                     f"Вы действительно хотите удалить поставщика\n'{supplier['company']}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_supplier(supplier['id']):
                self.load_suppliers()
                QMessageBox.information(self, "Успешно", f"Поставщик '{supplier['company']}' удален")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить поставщика")


class WarehousePage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.warehouse_items = []
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3c3c3c;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #000000;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
            }
        """)
        self.init_ui()
        self.load_warehouse()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Склад")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        stats_layout = QHBoxLayout()

        self.total_items_label = QLabel("Товарных позиций: 0")
        self.total_items_label.setStyleSheet(
            "background-color: #3498db; color: white; padding: 15px; border-radius: 5px; font-weight: bold;")

        self.in_stock_label = QLabel("В наличии: 0 шт.")
        self.in_stock_label.setStyleSheet(
            "background-color: #2ecc71; color: white; padding: 15px; border-radius: 5px; font-weight: bold;")

        self.total_value_label = QLabel("Стоимость остатков: 0 руб.")
        self.total_value_label.setStyleSheet(
            "background-color: #e74c3c; color: white; padding: 15px; border-radius: 5px; font-weight: bold;")

        stats_layout.addWidget(self.total_items_label)
        stats_layout.addWidget(self.in_stock_label)
        stats_layout.addWidget(self.total_value_label)

        layout.addLayout(stats_layout)

        self.warehouse_table = QTableWidget()
        self.warehouse_table.setColumnCount(9)
        self.warehouse_table.setHorizontalHeaderLabels(["Код", "Наименование", "Категория", "Поставщик",
                                                        "Закуп. цена", "Розн. цена", "Наличие", "Ред.", "Уд."])
        self.warehouse_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.warehouse_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.warehouse_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        layout.addWidget(self.warehouse_table)

        buttons_layout = QHBoxLayout()

        arrival_btn = QPushButton("Приход товара")
        arrival_btn.clicked.connect(self.open_arrival_dialog)
        arrival_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 10px; font-weight: bold;")

        expense_btn = QPushButton("Расход товара")
        expense_btn.clicked.connect(self.open_expense_dialog)
        expense_btn.setStyleSheet("background-color: #f44336; color: white; padding: 10px; font-weight: bold;")

        buttons_layout.addWidget(arrival_btn)
        buttons_layout.addWidget(expense_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

    def load_warehouse(self):
        self.warehouse_items = self.db.get_warehouse_items()
        self.update_statistics()
        self.refresh_table()

    def update_statistics(self):
        total_items = len(self.warehouse_items)
        total_in_stock = sum(item['quantity'] for item in self.warehouse_items)
        total_value = sum(item['purchase_price'] * item['quantity'] for item in self.warehouse_items)

        self.total_items_label.setText(f"Товарных позиций: {total_items}")
        self.in_stock_label.setText(f"В наличии: {total_in_stock} шт.")
        self.total_value_label.setText(f"Стоимость остатков: {total_value:,} руб.".replace(",", " "))

    def refresh_table(self):
        self.warehouse_table.setRowCount(len(self.warehouse_items))

        for i, item in enumerate(self.warehouse_items):
            self.warehouse_table.setItem(i, 0, QTableWidgetItem(item['code']))
            self.warehouse_table.setItem(i, 1, QTableWidgetItem(item['name']))
            self.warehouse_table.setItem(i, 2, QTableWidgetItem(item['category']))
            self.warehouse_table.setItem(i, 3, QTableWidgetItem(item['supplier']))

            purchase_item = QTableWidgetItem(item['purchase_price_str'])
            purchase_item.setForeground(QColor("#FF9800"))
            self.warehouse_table.setItem(i, 4, purchase_item)

            retail_item = QTableWidgetItem(item['retail_price_str'])
            retail_item.setForeground(QColor("#4CAF50"))
            self.warehouse_table.setItem(i, 5, retail_item)

            quantity_item = QTableWidgetItem(str(item['quantity']))
            if item['quantity'] > 0:
                quantity_item.setForeground(QColor("#4CAF50"))
            else:
                quantity_item.setForeground(QColor("#f44336"))
            self.warehouse_table.setItem(i, 6, quantity_item)

            edit_btn = QPushButton("✏️")
            edit_btn.setStyleSheet("background-color: #3498db; padding: 5px;")
            edit_btn.clicked.connect(lambda checked, idx=i: self.edit_item(idx))
            self.warehouse_table.setCellWidget(i, 7, edit_btn)

            delete_btn = QPushButton("🗑️")
            delete_btn.setStyleSheet("background-color: #f44336; padding: 5px;")
            delete_btn.clicked.connect(lambda checked, idx=i: self.delete_item(idx))
            self.warehouse_table.setCellWidget(i, 8, delete_btn)

    def edit_item(self, index):
        catalog_page = self.window().catalog_page
        catalog_page.edit_product(index)

    def delete_item(self, index):
        catalog_page = self.window().catalog_page
        catalog_page.delete_product(index)

    def open_arrival_dialog(self):
        if not self.warehouse_items:
            QMessageBox.warning(self, "Предупреждение", "На складе нет товаров")
            return

        dialog = WarehouseOperationDialog(self, self.warehouse_items, "+")

        if dialog.exec():
            data = dialog.get_data()
            if self.db.update_warehouse_quantity(data['code'], data['quantity'], '+'):
                self.load_warehouse()
                self.window().catalog_page.load_products()
                QMessageBox.information(self, "Успешно", "Приход товара выполнен")
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось выполнить операцию")

    def open_expense_dialog(self):
        if not self.warehouse_items:
            QMessageBox.warning(self, "Предупреждение", "На складе нет товаров")
            return

        dialog = WarehouseOperationDialog(self, self.warehouse_items, "-")

        if dialog.exec():
            data = dialog.get_data()
            if self.db.update_warehouse_quantity(data['code'], data['quantity'], '-'):
                self.load_warehouse()
                self.window().catalog_page.load_products()
                QMessageBox.information(self, "Успешно", "Расход товара выполнен")
            else:
                QMessageBox.critical(self, "Ошибка", "Недостаточно товара на складе или другая ошибка")


class ReportsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #ffffff;
                border: 2px solid #3c3c3c;
            }
            QRadioButton {
                color: #ffffff;
            }
            QDateEdit {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
            }
            QTableWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                gridline-color: #3c3c3c;
            }
            QTableWidget::item {
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #ffffff;
            }
        """)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        title = QLabel("Отчеты")
        title.setFont(QFont("Arial", 28, QFont.Weight.Bold))
        layout.addWidget(title)

        period_group = QGroupBox("Продажи")
        period_layout = QVBoxLayout(period_group)

        type_layout = QHBoxLayout()
        self.day_radio = QRadioButton("За день")
        self.week_radio = QRadioButton("За неделю")
        self.month_radio = QRadioButton("За месяц")

        self.day_radio.setChecked(True)
        self.day_radio.toggled.connect(self.on_period_changed)

        type_layout.addWidget(self.day_radio)
        type_layout.addWidget(self.week_radio)
        type_layout.addWidget(self.month_radio)
        type_layout.addStretch()

        period_layout.addLayout(type_layout)

        dates_layout = QHBoxLayout()

        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")

        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")

        dates_layout.addWidget(QLabel("С:"))
        dates_layout.addWidget(self.date_from)
        dates_layout.addWidget(QLabel("По:"))
        dates_layout.addWidget(self.date_to)
        dates_layout.addStretch()

        period_layout.addLayout(dates_layout)

        generate_btn = QPushButton("Сгенерировать отчет")
        generate_btn.clicked.connect(self.generate_report)
        generate_btn.setStyleSheet("background-color: #3498db; color: white; padding: 10px; font-weight: bold;")
        period_layout.addWidget(generate_btn)

        layout.addWidget(period_group)

        self.report_table = QTableWidget()
        self.report_table.setColumnCount(2)
        self.report_table.setHorizontalHeaderLabels(["Показатель", "Значение"])
        self.report_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.report_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.report_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.report_table.setWordWrap(True)

        self.report_table.setColumnWidth(1, 300)

        self.report_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.report_table.setAlternatingRowColors(True)

        layout.addWidget(self.report_table)

    def on_period_changed(self):
        if self.day_radio.isChecked():
            self.date_from.setDate(QDate.currentDate())
            self.date_to.setDate(QDate.currentDate())
        elif self.week_radio.isChecked():
            self.date_from.setDate(QDate.currentDate().addDays(-7))
            self.date_to.setDate(QDate.currentDate())
        elif self.month_radio.isChecked():
            self.date_from.setDate(QDate.currentDate().addDays(-30))
            self.date_to.setDate(QDate.currentDate())

    def generate_report(self):
        orders = self.db.get_all_orders()
        warehouse_items = self.db.get_warehouse_items()

        date_from = self.date_from.date().toString("dd.MM.yyyy")
        date_to = self.date_to.date().toString("dd.MM.yyyy")

        def parse_date(date_str):
            try:
                day, month, year = map(int, date_str.split('.'))
                return datetime(year, month, day)
            except:
                return None

        date_from_obj = parse_date(date_from)
        date_to_obj = parse_date(date_to)

        filtered_orders = []
        for order in orders:
            order_date = parse_date(order['date'])
            if order_date and order['status'] == "Выполнен":
                if date_from_obj and date_to_obj:
                    if date_from_obj <= order_date <= date_to_obj:
                        filtered_orders.append(order)

        total_orders = len(filtered_orders)
        total_revenue = sum(order['amount'] for order in filtered_orders)

        total_items_sold = 0
        product_sales = {}

        for order in filtered_orders:
            for item in order['items']:
                total_items_sold += item['quantity']
                if item['name'] in product_sales:
                    product_sales[item['name']] += item['quantity']
                else:
                    product_sales[item['name']] = item['quantity']

        best_product = "Нет данных"
        if product_sales:
            best_product = max(product_sales, key=product_sales.get)

        avg_check = total_revenue // total_orders if total_orders > 0 else 0

        total_in_stock = sum(item['quantity'] for item in warehouse_items)

        report_data = [
            ("Период", f"{date_from} - {date_to}"),
            ("Прибыль", f"{total_revenue:,} руб.".replace(",", " ")),
            ("Количество заказов", str(total_orders)),
            ("Количество проданных товаров", str(total_items_sold)),
            ("Самый продаваемый товар", best_product),
            ("Средний чек", f"{avg_check:,} руб.".replace(",", " ")),
            ("Товаров в наличии", f"{total_in_stock} шт.")
        ]

        self.report_table.setRowCount(len(report_data))

        for i, (label, value) in enumerate(report_data):
            self.report_table.setItem(i, 0, QTableWidgetItem(label))

            value_item = QTableWidgetItem(value)
            if "руб" in value and value != "0 руб." and "Нет" not in value:
                value_item.setForeground(QColor("#4CAF50"))
            self.report_table.setItem(i, 1, value_item)


def main():
    app = QApplication(sys.argv)

    app.setStyle('Fusion')

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(60, 60, 60))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(70, 70, 70))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(60, 60, 60))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 0, 0))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
