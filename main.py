import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from psycopg2 import Error
from datetime import datetime
import sys


class ProductCatalogApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Каталог товаров - PostgreSQL")
        self.root.geometry("1000x600")

        # Настройка масштабирования
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Устанавливаем минимальный размер окна
        self.root.minsize(800, 500)

        # Параметры подключения к PostgreSQL
        self.db_params = {
            'host': 'localhost',
            'database': 'product_catalog',
            'user': 'postgres',
            'password': '1234',  # замените на ваш пароль
            'port': '5432'
        }

        # Инициализация базы данных
        if not self.init_database():
            messagebox.showerror("Ошибка", "Не удалось подключиться к базе данных PostgreSQL")
            sys.exit(1)

        # Загрузка товаров из базы данных
        self.products = self.load_products_from_db()

        self.setup_ui()

    def get_connection(self):
        """Получение соединения с базой данных"""
        try:
            conn = psycopg2.connect(**self.db_params)
            return conn
        except Error as e:
            print(f"Ошибка подключения к PostgreSQL: {e}")
            return None

    def init_database(self):
        """Инициализация базы данных PostgreSQL"""
        try:
            conn = self.get_connection()
            if conn is None:
                return False

            cursor = conn.cursor()

            # Создаем таблицу, если она не существует
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    code VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    price VARCHAR(50) NOT NULL,
                    stock VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Создаем индекс для быстрого поиска по коду
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_products_code ON products(code)
            ''')

            conn.commit()

            # Проверяем, есть ли данные в таблице
            cursor.execute('SELECT COUNT(*) FROM products')
            count = cursor.fetchone()[0]

            if count == 0:
                self.add_sample_data(cursor, conn)

            cursor.close()
            conn.close()
            return True

        except Error as e:
            print(f"Ошибка при инициализации БД: {e}")
            return False

    def add_sample_data(self, cursor, conn):
        """Добавление тестовых данных в базу данных"""
        sample_products = [
            ("00001", "Intel Core i5-14400F OEM", "Процессор", "15 000 руб.", "5 шт."),
            ("00002", "ASUS TUF Gaming B760", "Материнская плата", "12 000 руб.", "3 шт."),
            ("00003", "NVIDIA GeForce RTX 4060", "Видеокарта", "35 000 руб.", "2 шт."),
            ("00004", "Kingston DDR4 16GB", "Оперативная память", "4 500 руб.", "10 шт."),
            ("00005", "Samsung 970 EVO Plus 1TB", "SSD накопитель", "8 000 руб.", "7 шт.")
        ]

        try:
            for product in sample_products:
                cursor.execute('''
                    INSERT INTO products (code, name, category, price, stock)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (code) DO NOTHING
                ''', product)

            conn.commit()
            print("Тестовые данные добавлены в базу данных")
        except Error as e:
            print(f"Ошибка при добавлении тестовых данных: {e}")

    def load_products_from_db(self):
        """Загрузка товаров из базы данных"""
        try:
            conn = self.get_connection()
            if conn is None:
                return []

            cursor = conn.cursor()
            cursor.execute('''
                SELECT code, name, category, price, stock 
                FROM products 
                ORDER BY code
            ''')

            products_data = cursor.fetchall()

            # Преобразуем в список словарей
            products = []
            for row in products_data:
                product = {
                    "code": row[0],
                    "name": row[1],
                    "category": row[2],
                    "price": row[3],
                    "stock": row[4]
                }
                products.append(product)

            cursor.close()
            conn.close()
            return products

        except Error as e:
            print(f"Ошибка при загрузке данных из БД: {e}")
            return []

    def save_product_to_db(self, product):
        """Сохранение товара в базу данных"""
        try:
            conn = self.get_connection()
            if conn is None:
                return False, "Нет соединения с БД"

            cursor = conn.cursor()

            # Проверяем, существует ли товар с таким кодом
            cursor.execute('SELECT code FROM products WHERE code = %s', (product["code"],))
            existing_product = cursor.fetchone()

            if existing_product:
                # Обновляем существующий товар
                cursor.execute('''
                    UPDATE products 
                    SET name = %s, category = %s, price = %s, stock = %s
                    WHERE code = %s
                ''', (product["name"], product["category"], product["price"], product["stock"], product["code"]))
                message = "Товар обновлен"
            else:
                # Добавляем новый товар
                cursor.execute('''
                    INSERT INTO products (code, name, category, price, stock)
                    VALUES (%s, %s, %s, %s, %s)
                ''', (product["code"], product["name"], product["category"], product["price"], product["stock"]))
                message = "Товар успешно добавлен"

            conn.commit()
            cursor.close()
            conn.close()
            return True, message

        except Error as e:
            if conn:
                conn.rollback()
            return False, f"Ошибка при сохранении в БД: {str(e)}"

    def delete_product_from_db(self, product_code):
        """Удаление товара из базы данных"""
        try:
            conn = self.get_connection()
            if conn is None:
                return False

            cursor = conn.cursor()
            cursor.execute('DELETE FROM products WHERE code = %s', (product_code,))
            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()
            return deleted_count > 0

        except Error as e:
            print(f"Ошибка при удалении товара: {e}")
            return False

    def setup_ui(self):
        # Основной контейнер с масштабированием
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Конфигурация сетки для масштабирования
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Строка с таблицей
        main_frame.rowconfigure(6, weight=0)  # Строка с формой добавления

        # Заголовок с информацией о БД
        header_frame = tk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=4, pady=(0, 10), sticky="ew")

        title_label = tk.Label(header_frame, text="Каталог товаров (PostgreSQL)", font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)

        # Информация о подключении к БД
        db_info = f"БД: {self.db_params['database']}@{self.db_params['host']}"
        self.db_info_label = tk.Label(
            header_frame,
            text=db_info,
            font=("Arial", 9),
            fg="blue"
        )
        self.db_info_label.pack(side=tk.RIGHT, padx=(0, 10))

        # Информация о количестве товаров
        self.product_count_label = tk.Label(
            header_frame,
            text=f"Товаров: {len(self.products)}",
            font=("Arial", 10),
            fg="gray"
        )
        self.product_count_label.pack(side=tk.RIGHT)

        # Разделитель
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=1, column=0, columnspan=4, pady=20, sticky="ew")

        # Заголовок списка товаров
        list_title = tk.Label(main_frame, text="Список товаров", font=("Arial", 14, "bold"))
        list_title.grid(row=2, column=0, columnspan=4, pady=(0, 10), sticky="w")

        # Таблица товаров
        self.create_product_table(main_frame)

        # Фрейм для добавления нового товара
        add_product_frame = tk.Frame(main_frame)
        add_product_frame.grid(row=6, column=0, columnspan=4, pady=20, sticky="nsew")
        add_product_frame.columnconfigure(0, weight=1)

        tk.Label(add_product_frame, text="Добавить/Обновить товар", font=("Arial", 12, "bold")).pack(anchor="w",
                                                                                                     pady=(0, 10))

        # Поля для ввода нового товара
        input_frame = tk.Frame(add_product_frame)
        input_frame.pack(fill=tk.X)

        # Конфигурация сетки для полей ввода
        for i in range(10):  # 10 колонок (5 пар: label + entry)
            input_frame.columnconfigure(i, weight=1)

        labels = ["Код:", "Наименование:", "Категория:", "Цена:", "Наличие:"]
        self.entry_widgets = []

        for i, label_text in enumerate(labels):
            # Метка
            tk.Label(input_frame, text=label_text, anchor="w").grid(
                row=0, column=i * 2, padx=(0, 5), sticky="ew"
            )

            # Поле ввода
            entry = tk.Entry(input_frame)
            entry.grid(row=0, column=i * 2 + 1, padx=(0, 20), sticky="ew")
            self.entry_widgets.append(entry)

        # Фрейм для кнопок
        button_frame = tk.Frame(add_product_frame)
        button_frame.pack(pady=10, fill=tk.X)

        # Кнопка добавления/обновления товара
        add_button = tk.Button(button_frame, text="Сохранить товар", command=self.add_product,
                               bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), padx=20, pady=5)
        add_button.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопка очистки полей
        clear_button = tk.Button(button_frame, text="Очистить поля", command=self.clear_fields,
                                 bg="#f0ad4e", fg="white", font=("Arial", 10), padx=20, pady=5)
        clear_button.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопка загрузки выбранного товара для редактирования
        load_button = tk.Button(button_frame, text="Загрузить для редактирования",
                                command=self.load_product_for_edit,
                                bg="#5bc0de", fg="white", font=("Arial", 10), padx=20, pady=5)
        load_button.pack(side=tk.LEFT)

        # Кнопка обновления списка
        refresh_button = tk.Button(button_frame, text="Обновить список", command=self.refresh_products,
                                   bg="#6c757d", fg="white", font=("Arial", 10), padx=20, pady=5)
        refresh_button.pack(side=tk.RIGHT)

    def create_product_table(self, parent):
        # Создание Treeview для отображения товаров
        columns = ("Код", "Наименование", "Категория", "Цена", "Наличие")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=15)

        # Настройка колонок с весом для масштабирования
        self.tree.heading("Код", text="Код")
        self.tree.heading("Наименование", text="Наименование")
        self.tree.heading("Категория", text="Категория")
        self.tree.heading("Цена", text="Цена")
        self.tree.heading("Наличие", text="Наличие")

        # Ширина колонок в процентах
        self.tree.column("Код", width=80, minwidth=80, stretch=False)
        self.tree.column("Наименование", width=300, minwidth=200, stretch=True)
        self.tree.column("Категория", width=150, minwidth=100, stretch=True)
        self.tree.column("Цена", width=120, minwidth=100, stretch=False)
        self.tree.column("Наличие", width=80, minwidth=80, stretch=False)

        self.tree.grid(row=3, column=0, columnspan=3, pady=(0, 10), sticky="nsew")

        # Добавление полосы прокрутки
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=3, column=3, sticky="ns", pady=(0, 10))
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Добавление горизонтальной полосы прокрутки
        hscrollbar = ttk.Scrollbar(parent, orient="horizontal", command=self.tree.xview)
        hscrollbar.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        self.tree.configure(xscrollcommand=hscrollbar.set)

        # Бинд для двойного клика и правого клика
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Контекстное меню
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Редактировать", command=self.load_product_for_edit)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Удалить товар", command=self.delete_selected_product)

        # Заполнение таблицы данными из базы
        self.update_product_table()

        # Стиль для таблицы
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

    def update_product_table(self):
        """Обновление таблицы товаров"""
        # Очистка таблицы
        for item in self.tree.get_children():
            self.tree.delete(item)

        # Добавление товаров в таблицу
        for product in self.products:
            self.tree.insert("", tk.END, values=(
                product["code"],
                product["name"],
                product["category"],
                product["price"],
                product["stock"]
            ))

        # Обновление счетчика товаров
        self.product_count_label.config(text=f"Товаров: {len(self.products)}")

    def on_double_click(self, event):
        """Обработка двойного клика по товару"""
        self.load_product_for_edit()

    def show_context_menu(self, event):
        """Показать контекстное меню"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def load_product_for_edit(self):
        """Загрузить выбранный товар в форму для редактирования"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите товар для редактирования")
            return

        # Получаем данные выбранного товара
        item_values = self.tree.item(selected_item[0], "values")

        # Заполняем поля формы
        for i, value in enumerate(item_values):
            self.entry_widgets[i].delete(0, tk.END)
            self.entry_widgets[i].insert(0, value)

        messagebox.showinfo("Загружено", "Товар загружен в форму для редактирования")

    def delete_selected_product(self):
        """Удалить выбранный товар"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Внимание", "Выберите товар для удаления")
            return

        # Получаем данные выбранного товара
        item_values = self.tree.item(selected_item[0], "values")
        product_code = item_values[0]
        product_name = item_values[1]

        # Подтверждение удаления
        confirm = messagebox.askyesno(
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить товар:\n{product_name} (код: {product_code})?"
        )

        if confirm:
            # Удаляем из базы данных
            if self.delete_product_from_db(product_code):
                # Обновляем список товаров
                self.products = self.load_products_from_db()
                self.update_product_table()
                messagebox.showinfo("Успех", "Товар удален")
            else:
                messagebox.showerror("Ошибка", "Не удалось удалить товар")

    def add_product(self):
        """Добавление нового товара"""
        # Получение данных из полей ввода
        new_product = {
            "code": self.entry_widgets[0].get().strip(),
            "name": self.entry_widgets[1].get().strip(),
            "category": self.entry_widgets[2].get().strip(),
            "price": self.entry_widgets[3].get().strip(),
            "stock": self.entry_widgets[4].get().strip()
        }

        # Проверка заполнения всех полей
        for key, value in new_product.items():
            if not value:
                field_names = {
                    "code": "Код",
                    "name": "Наименование",
                    "category": "Категория",
                    "price": "Цена",
                    "stock": "Наличие"
                }
                messagebox.showwarning("Внимание", f"Поле '{field_names[key]}' не заполнено!")
                return

        # Сохранение товара в базу данных
        success, message = self.save_product_to_db(new_product)

        if success:
            # Обновляем список товаров
            self.products = self.load_products_from_db()
            self.update_product_table()
            self.clear_fields()
            messagebox.showinfo("Успех", message)
        else:
            messagebox.showerror("Ошибка", message)

    def clear_fields(self):
        """Очистка полей ввода"""
        for entry in self.entry_widgets:
            entry.delete(0, tk.END)

    def refresh_products(self):
        """Обновление списка товаров из базы данных"""
        self.products = self.load_products_from_db()
        self.update_product_table()
        messagebox.showinfo("Обновлено", f"Список товаров обновлен. Загружено {len(self.products)} товаров")


if __name__ == "__main__":
    # Проверяем наличие psycopg2
    try:
        import psycopg2
    except ImportError:
        print("Ошибка: Библиотека psycopg2 не установлена.")
        print("Установите её командой: pip install psycopg2-binary")
        sys.exit(1)

    root = tk.Tk()
    app = ProductCatalogApp(root)


    # Бинд для масштабирования при изменении размера окна
    def on_resize(event):
        pass


    root.bind("<Configure>", on_resize)


    # Обработка закрытия окна
    def on_closing():
        if messagebox.askokcancel("Выход", "Вы уверены, что хотите выйти?"):
            root.destroy()


    root.protocol("WM_DELETE_WINDOW", on_closing)

    root.mainloop()