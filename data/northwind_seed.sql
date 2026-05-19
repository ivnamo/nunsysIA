DROP TABLE IF EXISTS order_details;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    contact_name TEXT,
    country TEXT NOT NULL,
    city TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    unit_price NUMERIC NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TEXT NOT NULL,
    required_date TEXT,
    shipped_date TEXT,
    erp_status TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_details (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    unit_price NUMERIC NOT NULL,
    quantity INTEGER NOT NULL,
    discount NUMERIC NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

INSERT INTO customers (customer_id, company_name, contact_name, country, city) VALUES
    ('ALFKI', 'Alfreds Futterkiste', 'Maria Anders', 'Germany', 'Berlin'),
    ('ANATR', 'Ana Trujillo Emparedados y helados', 'Ana Trujillo', 'Mexico', 'Mexico D.F.'),
    ('BONAP', 'Bon app', 'Laurence Lebihan', 'France', 'Marseille');

INSERT INTO products (product_id, product_name, unit_price) VALUES
    (1, 'Chai', 18.00),
    (2, 'Chang', 20.00),
    (3, 'Aniseed Syrup', 12.10),
    (4, 'Chef Anton Cajun Seasoning', 24.90),
    (11, 'Queso Cabrales', 14.00),
    (20, 'Sir Rodney Marmalade', 31.05),
    (42, 'Singaporean Hokkien Fried Mee', 10.00);

INSERT INTO orders (order_id, customer_id, order_date, required_date, shipped_date, erp_status) VALUES
    (10248, 'ALFKI', '2026-05-02', '2026-05-20', NULL, 'pending'),
    (10252, 'ALFKI', '2026-05-07', '2026-05-25', NULL, 'pending'),
    (10255, 'ALFKI', '2026-05-11', '2026-05-30', '2026-05-15', 'shipped'),
    (10301, 'ANATR', '2026-05-13', '2026-06-01', NULL, 'pending'),
    (10312, 'BONAP', '2026-05-18', '2026-06-08', NULL, 'pending');

INSERT INTO order_details (order_id, product_id, unit_price, quantity, discount) VALUES
    (10248, 11, 14.00, 10, 0),
    (10248, 42, 10.00, 30, 0),
    (10252, 20, 31.05, 60, 0),
    (10255, 4, 24.90, 100, 0),
    (10301, 1, 18.00, 40, 0),
    (10301, 2, 20.00, 10, 0),
    (10312, 3, 12.10, 100, 0);
