-- =============================================================
-- LibraCore – Smart Library Management System
-- MySQL 8.0+
-- =============================================================
CREATE DATABASE IF NOT EXISTS library_management
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE library_management;

DROP VIEW IF EXISTS vw_overdue_books;
DROP VIEW IF EXISTS vw_book_catalog;
DROP VIEW IF EXISTS vw_member_activity;

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE authors (
    author_id INT AUTO_INCREMENT PRIMARY KEY,
    author_name VARCHAR(150) NOT NULL,
    email VARCHAR(120),
    country VARCHAR(80),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE publishers (
    publisher_id INT AUTO_INCREMENT PRIMARY KEY,
    publisher_name VARCHAR(150) NOT NULL UNIQUE,
    email VARCHAR(120),
    phone VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE books (
    book_id INT AUTO_INCREMENT PRIMARY KEY,
    isbn VARCHAR(30) UNIQUE,
    title VARCHAR(255) NOT NULL,
    author_id INT,
    category_id INT,
    publisher_id INT,
    publication_year YEAR,
    edition VARCHAR(50),
    language VARCHAR(50) DEFAULT 'English',
    shelf_location VARCHAR(80),
    total_copies INT NOT NULL DEFAULT 1,
    available_copies INT NOT NULL DEFAULT 1,
    price DECIMAL(10,2) DEFAULT 0.00,
    description TEXT,
    status ENUM('Available','Low Stock','Out of Stock','Archived') DEFAULT 'Available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE SET NULL,
    FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL,
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id) ON DELETE SET NULL
);

CREATE TABLE members (
    member_id INT AUTO_INCREMENT PRIMARY KEY,
    member_code VARCHAR(30) NOT NULL UNIQUE,
    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60),
    email VARCHAR(120) UNIQUE,
    phone VARCHAR(20) NOT NULL,
    address TEXT,
    membership_type ENUM('Student','Faculty','Staff','Public') DEFAULT 'Student',
    join_date DATE NOT NULL,
    expiry_date DATE,
    max_books INT DEFAULT 3,
    status ENUM('Active','Inactive','Suspended') DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE library_staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(60) NOT NULL,
    last_name VARCHAR(60),
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(20),
    role ENUM('Admin','Librarian','Assistant') DEFAULT 'Librarian',
    status ENUM('Active','Inactive','On Leave') DEFAULT 'Active',
    joined_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE loans (
    loan_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    member_id INT NOT NULL,
    issued_by INT,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    status ENUM('Issued','Returned','Overdue','Lost') DEFAULT 'Issued',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE RESTRICT,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE,
    FOREIGN KEY (issued_by) REFERENCES library_staff(staff_id) ON DELETE SET NULL
);

CREATE TABLE reservations (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    member_id INT NOT NULL,
    reservation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    expiry_date DATE,
    status ENUM('Pending','Ready','Collected','Cancelled','Expired') DEFAULT 'Pending',
    FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

CREATE TABLE fines (
    fine_id INT AUTO_INCREMENT PRIMARY KEY,
    loan_id INT NOT NULL,
    member_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    reason VARCHAR(255) NOT NULL,
    status ENUM('Pending','Paid','Waived') DEFAULT 'Pending',
    paid_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loan_id) REFERENCES loans(loan_id) ON DELETE CASCADE,
    FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
);

CREATE TABLE system_users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    staff_id INT UNIQUE,
    username VARCHAR(60) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Admin','Librarian','Assistant') DEFAULT 'Librarian',
    is_active BOOLEAN DEFAULT TRUE,
    last_login DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (staff_id) REFERENCES library_staff(staff_id) ON DELETE SET NULL
);

CREATE OR REPLACE VIEW vw_book_catalog AS
SELECT b.book_id,b.isbn,b.title,b.publication_year,b.edition,b.language,
       b.shelf_location,b.total_copies,b.available_copies,b.price,b.status,
       a.author_name,c.category_name,p.publisher_name
FROM books b
LEFT JOIN authors a ON a.author_id=b.author_id
LEFT JOIN categories c ON c.category_id=b.category_id
LEFT JOIN publishers p ON p.publisher_id=b.publisher_id;

CREATE OR REPLACE VIEW vw_overdue_books AS
SELECT l.loan_id,l.issue_date,l.due_date,l.return_date,
       b.title,b.isbn,m.member_code,
       CONCAT(m.first_name,' ',COALESCE(m.last_name,'')) member_name,
       m.phone,DATEDIFF(CURDATE(),l.due_date) days_overdue,
       COALESCE(f.amount,0) fine_amount
FROM loans l
JOIN books b ON b.book_id=l.book_id
JOIN members m ON m.member_id=l.member_id
LEFT JOIN fines f ON f.loan_id=l.loan_id AND f.status='Pending'
WHERE l.return_date IS NULL AND l.due_date < CURDATE();

CREATE OR REPLACE VIEW vw_member_activity AS
SELECT m.member_id,m.member_code,
       CONCAT(m.first_name,' ',COALESCE(m.last_name,'')) member_name,
       m.membership_type,m.status,
       COUNT(l.loan_id) total_loans,
       SUM(CASE WHEN l.return_date IS NULL THEN 1 ELSE 0 END) active_loans,
       COALESCE(SUM(CASE WHEN f.status='Pending' THEN f.amount ELSE 0 END),0) pending_fines
FROM members m
LEFT JOIN loans l ON l.member_id=m.member_id
LEFT JOIN fines f ON f.member_id=m.member_id
GROUP BY m.member_id,m.member_code,member_name,m.membership_type,m.status;

INSERT INTO categories (category_name,description) VALUES
('Computer Science','Programming, software, AI and technology'),
('Data Science','Analytics, statistics, machine learning and data'),
('Fiction','Novels, stories and literature'),
('Business','Management, finance, marketing and entrepreneurship'),
('Self Development','Productivity, communication and personal growth'),
('Reference','Academic and general reference material');

INSERT INTO authors (author_name,email,country) VALUES
('Robert C. Martin','clean.code@example.com','USA'),
('Andrew Hunt','pragmatic@example.com','USA'),
('Aurélien Géron','ml@example.com','France'),
('Yuval Noah Harari','books@example.com','Israel'),
('James Clear','atomic@example.com','USA'),
('George Orwell','classic@example.com','United Kingdom'),
('R. S. Aggarwal','reference@example.com','India');

INSERT INTO publishers (publisher_name,email,phone) VALUES
('Pearson','contact@pearson.com','1800-000-100'),
('O''Reilly Media','contact@oreilly.com','1800-000-101'),
('McGraw Hill','contact@mcgrawhill.com','1800-000-102'),
('Penguin Random House','contact@penguin.com','1800-000-103');

INSERT INTO books
(isbn,title,author_id,category_id,publisher_id,publication_year,edition,language,shelf_location,total_copies,available_copies,price,description)
VALUES
('9780132350884','Clean Code',1,1,1,2008,'1st','English','CS-A01',5,4,650,'A practical guide to writing clean and maintainable code.'),
('9780135957059','The Pragmatic Programmer',2,1,1,2019,'2nd','English','CS-A02',4,3,750,'Classic software engineering practices for modern developers.'),
('9781492032649','Hands-On Machine Learning',3,2,2,2022,'3rd','English','DS-B01',6,5,950,'Machine learning concepts and practical Python implementations.'),
('9780062316097','Sapiens',4,3,4,2015,'1st','English','FIC-C01',3,2,550,'A broad history of humankind.'),
('9780735211292','Atomic Habits',5,5,4,2018,'1st','English','SD-D01',5,4,499,'A practical framework for building good habits.'),
('9780451524935','1984',6,3,4,1949,'1st','English','FIC-C02',2,0,299,'A dystopian classic.'),
('9788121905070','Quantitative Aptitude',7,6,3,2020,'1st','English','REF-E01',8,7,480,'Competitive examination quantitative aptitude reference.');

INSERT INTO members
(member_code,first_name,last_name,email,phone,address,membership_type,join_date,expiry_date,max_books)
VALUES
('LIB-1001','Aarav','Sharma','aarav@example.com','9876500001','Lucknow, Uttar Pradesh','Student','2026-01-10','2027-01-10',3),
('LIB-1002','Ananya','Verma','ananya@example.com','9876500002','Lucknow, Uttar Pradesh','Student','2026-02-05','2027-02-05',3),
('LIB-1003','Rahul','Singh','rahul@example.com','9876500003','Lucknow, Uttar Pradesh','Faculty','2026-01-20','2027-01-20',6),
('LIB-1004','Priya','Mishra','priya@example.com','9876500004','Lucknow, Uttar Pradesh','Staff','2026-03-12','2027-03-12',4),
('LIB-1005','Vivek','Gupta','vivek@example.com','9876500005','Lucknow, Uttar Pradesh','Public','2026-04-01','2027-04-01',2);

INSERT INTO library_staff (first_name,last_name,email,phone,role,status,joined_date) VALUES
('Neha','Agarwal','neha@library.local','9876510001','Admin','Active','2025-06-01'),
('Rohan','Mehta','rohan@library.local','9876510002','Librarian','Active','2025-08-15'),
('Kavita','Rao','kavita@library.local','9876510003','Assistant','Active','2026-01-05');

INSERT INTO loans (book_id,member_id,issued_by,issue_date,due_date,return_date,status,notes) VALUES
(1,1,2,'2026-09-20','2026-10-04',NULL,'Overdue','Please return at earliest.'),
(3,2,2,'2026-10-01','2026-10-15',NULL,'Issued',''),
(5,3,2,'2026-09-28','2026-10-12',NULL,'Issued',''),
(2,4,3,'2026-08-10','2026-08-24','2026-08-22','Returned','Returned in good condition.'),
(7,5,3,'2026-09-15','2026-09-29','2026-09-30','Returned','One day late.');

INSERT INTO fines (loan_id,member_id,amount,reason,status) VALUES
(1,1,30.00,'Overdue fine','Pending'),
(5,5,10.00,'One day late return','Paid');
