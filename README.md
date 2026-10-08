# LibraCore — Smart Library Management System

A converted version of the original Flask + MySQL hospital project, redesigned for library operations.

## Features
- Dashboard with live library statistics
- Book catalog with search and stock status
- Member management
- Issue and return workflow
- Automatic overdue detection
- Automatic late fine calculation (₹10/day)
- Fine payment tracking
- Book reservations
- Staff directory
- Authors, categories and publishers
- MySQL views for catalog, overdue books and member activity
- Responsive dark interactive UI

## Setup
1. Install MySQL 8.0+ and start the MySQL service.
2. Open MySQL Workbench.
3. Run `library_schema.sql` once.
4. If your MySQL root account has a password, edit `DB_CONFIG` in `app.py`.
5. Open PowerShell in this folder.
6. Run:
   `pip install -r requirements.txt`
7. Start:
   `python app.py`
8. Open http://127.0.0.1:5000

## Important
The SQL creates the database `library_management` and sample data. The Flask application expects that exact database name.

## Project files
- `app.py` — Flask backend/API
- `library_management.html` — complete frontend
- `library_schema.sql` — database schema, views and sample data
- `requirements.txt` — Python dependencies
- `.gitignore` — common Python/VS Code exclusions
