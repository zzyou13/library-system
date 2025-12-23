CREATE DATABASE IF NOT EXISTS library_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_general_ci;

USE library_db;

CREATE TABLE admin (
    admin_id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    create_time DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE reader (
    reader_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    gender VARCHAR(10),
    phone VARCHAR(20),
    register_date DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE category (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200)
) ENGINE=InnoDB;

CREATE TABLE book (
    book_id INT PRIMARY KEY AUTO_INCREMENT,
    book_name VARCHAR(100) NOT NULL,
    author VARCHAR(100),
    publisher VARCHAR(100),
    category_id INT,
    total_count INT DEFAULT 0,
    available_count INT DEFAULT 0,
    CONSTRAINT fk_book_category
        FOREIGN KEY (category_id)
        REFERENCES category(category_id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE borrow (
    borrow_id INT PRIMARY KEY AUTO_INCREMENT,
    reader_id INT NOT NULL,
    book_id INT NOT NULL,
    borrow_date DATE NOT NULL,
    return_date DATE NOT NULL,
    actual_return_date DATE,
    status VARCHAR(20) DEFAULT '借出',
    CONSTRAINT fk_borrow_reader
        FOREIGN KEY (reader_id)
        REFERENCES reader(reader_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    CONSTRAINT fk_borrow_book
        FOREIGN KEY (book_id)
        REFERENCES book(book_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB;

-- 创建统计视图（为复杂查询提供便利）
CREATE OR REPLACE VIEW book_borrow_stats AS
SELECT 
    b.book_id,
    b.book_name,
    b.author,
    b.publisher,
    c.category_name,
    b.total_count,
    b.available_count,
    COUNT(br.borrow_id) as borrow_count
FROM book b
LEFT JOIN category c ON b.category_id = c.category_id
LEFT JOIN borrow br ON b.book_id = br.book_id
GROUP BY b.book_id, b.book_name, b.author, b.publisher, c.category_name, b.total_count, b.available_count;

CREATE OR REPLACE VIEW reader_borrow_stats AS
SELECT 
    r.reader_id,
    r.name,
    r.gender,
    r.phone,
    COUNT(br.borrow_id) as total_borrow,
    COUNT(CASE WHEN br.actual_return_date IS NULL THEN 1 END) as current_borrow,
    MIN(br.borrow_date) as first_borrow_date,
    MAX(br.borrow_date) as latest_borrow_date
FROM reader r
LEFT JOIN borrow br ON r.reader_id = br.reader_id
GROUP BY r.reader_id, r.name, r.gender, r.phone;
