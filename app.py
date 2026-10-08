"""
LibraCore Smart Library Management System
Flask + MySQL backend
Run: python app.py
"""
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pymysql
import pymysql.cursors
from datetime import date, timedelta

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "library_management",
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8mb4",
    "autocommit": False
}

@app.route("/")
def index():
    return send_from_directory(".", "library_management.html")

def get_db():
    return pymysql.connect(**DB_CONFIG)

def error_response(e):
    return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/dashboard")
def dashboard():
    db = get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT COUNT(*) total FROM books WHERE status <> 'Archived'")
            books = c.fetchone()["total"]
            c.execute("SELECT COALESCE(SUM(total_copies),0) total FROM books WHERE status <> 'Archived'")
            copies = c.fetchone()["total"]
            c.execute("SELECT COALESCE(SUM(available_copies),0) total FROM books WHERE status <> 'Archived'")
            available = c.fetchone()["total"]
            c.execute("SELECT COUNT(*) total FROM members WHERE status='Active'")
            members = c.fetchone()["total"]
            c.execute("SELECT COUNT(*) total FROM loans WHERE return_date IS NULL")
            issued = c.fetchone()["total"]
            c.execute("SELECT COUNT(*) total FROM loans WHERE return_date IS NULL AND due_date < CURDATE()")
            overdue = c.fetchone()["total"]
            c.execute("SELECT COALESCE(SUM(amount),0) total FROM fines WHERE status='Paid' AND MONTH(paid_date)=MONTH(CURDATE()) AND YEAR(paid_date)=YEAR(CURDATE())")
            revenue = c.fetchone()["total"]
            c.execute("SELECT COUNT(*) total FROM books WHERE available_copies <= 1 AND status <> 'Archived'")
            low_stock = c.fetchone()["total"]
        return jsonify({"books":books,"copies":copies,"available":available,"members":members,
                        "issued":issued,"overdue":overdue,"monthly_fines":float(revenue),"low_stock":low_stock})
    finally:
        db.close()

@app.route("/api/books", methods=["GET","POST"])
def books_api():
    db = get_db()
    try:
        with db.cursor() as c:
            if request.method == "GET":
                search = request.args.get("search","").strip()
                category = request.args.get("category","").strip()
                sql = """SELECT b.*,a.author_name,c.category_name,p.publisher_name
                         FROM books b LEFT JOIN authors a ON a.author_id=b.author_id
                         LEFT JOIN categories c ON c.category_id=b.category_id
                         LEFT JOIN publishers p ON p.publisher_id=b.publisher_id
                         WHERE b.status <> 'Archived'"""
                params=[]
                if search:
                    sql += " AND (b.title LIKE %s OR b.isbn LIKE %s OR a.author_name LIKE %s OR b.shelf_location LIKE %s)"
                    q=f"%{search}%"; params += [q,q,q,q]
                if category:
                    sql += " AND b.category_id=%s"; params.append(category)
                sql += " ORDER BY b.created_at DESC"
                c.execute(sql,params)
                return jsonify(c.fetchall())
            d=request.json
            total=int(d.get("total_copies",1))
            c.execute("""INSERT INTO books
                (isbn,title,author_id,category_id,publisher_id,publication_year,edition,language,
                 shelf_location,total_copies,available_copies,price,description)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d.get("isbn"),d["title"],d.get("author_id") or None,d.get("category_id") or None,
                 d.get("publisher_id") or None,d.get("publication_year") or None,d.get("edition"),
                 d.get("language","English"),d.get("shelf_location"),total,total,float(d.get("price",0) or 0),
                 d.get("description")))
            db.commit()
            return jsonify({"success":True,"book_id":c.lastrowid}),201
    except Exception as e:
        db.rollback(); return error_response(e)
    finally: db.close()

@app.route("/api/books/<int:book_id>", methods=["PUT","DELETE"])
def book_detail(book_id):
    db=get_db()
    try:
        with db.cursor() as c:
            if request.method=="DELETE":
                c.execute("UPDATE books SET status='Archived' WHERE book_id=%s",(book_id,))
            else:
                d=request.json
                fields=["title","isbn","author_id","category_id","publisher_id","publication_year","edition","language","shelf_location","price","description"]
                sets=[]; vals=[]
                for f in fields:
                    if f in d:
                        sets.append(f"{f}=%s"); vals.append(d[f] if d[f] != "" else None)
                if not sets: return jsonify({"success":True})
                vals.append(book_id); c.execute("UPDATE books SET "+",".join(sets)+" WHERE book_id=%s",vals)
            db.commit(); return jsonify({"success":True})
    except Exception as e:
        db.rollback(); return error_response(e)
    finally: db.close()

@app.route("/api/members", methods=["GET","POST"])
def members_api():
    db=get_db()
    try:
        with db.cursor() as c:
            if request.method=="GET":
                search=request.args.get("search","").strip()
                sql="SELECT * FROM members WHERE 1=1"; params=[]
                if search:
                    q=f"%{search}%"; sql += " AND (member_code LIKE %s OR first_name LIKE %s OR last_name LIKE %s OR phone LIKE %s OR email LIKE %s)"; params += [q]*5
                sql+=" ORDER BY created_at DESC"; c.execute(sql,params); return jsonify(c.fetchall())
            d=request.json
            c.execute("""INSERT INTO members
                (member_code,first_name,last_name,email,phone,address,membership_type,join_date,expiry_date,max_books)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (d["member_code"],d["first_name"],d.get("last_name"),d.get("email"),d["phone"],d.get("address"),
                 d.get("membership_type","Student"),d["join_date"],d.get("expiry_date"),d.get("max_books",3)))
            db.commit(); return jsonify({"success":True,"member_id":c.lastrowid}),201
    except Exception as e:
        db.rollback(); return error_response(e)
    finally: db.close()

@app.route("/api/members/<int:member_id>", methods=["GET","PUT"])
def member_detail(member_id):
    db=get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM members WHERE member_id=%s",(member_id,)); m=c.fetchone()
            if not m:return jsonify({"error":"Member not found"}),404
            c.execute("""SELECT l.*,b.title,b.isbn FROM loans l JOIN books b ON b.book_id=l.book_id
                         WHERE l.member_id=%s ORDER BY l.issue_date DESC""",(member_id,))
            m["loans"]=c.fetchall()
            c.execute("SELECT * FROM fines WHERE member_id=%s ORDER BY created_at DESC",(member_id,))
            m["fines"]=c.fetchall()
            if request.method=="PUT":
                d=request.json
                allowed=["first_name","last_name","email","phone","address","membership_type","expiry_date","max_books","status"]
                sets=[];vals=[]
                for f in allowed:
                    if f in d: sets.append(f"{f}=%s"); vals.append(d[f])
                if sets: vals.append(member_id); c.execute("UPDATE members SET "+",".join(sets)+" WHERE member_id=%s",vals)
                db.commit(); return jsonify({"success":True})
            return jsonify(m)
    except Exception as e:
        db.rollback(); return error_response(e)
    finally: db.close()

@app.route("/api/loans", methods=["GET","POST"])
def loans_api():
    db=get_db()
    try:
        with db.cursor() as c:
            if request.method=="GET":
                status=request.args.get("status","")
                sql="""SELECT l.*,b.title,b.isbn,m.member_code,
                        CONCAT(m.first_name,' ',COALESCE(m.last_name,'')) member_name,
                        m.phone,s.first_name staff_first_name,s.last_name staff_last_name
                        FROM loans l JOIN books b ON b.book_id=l.book_id
                        JOIN members m ON m.member_id=l.member_id
                        LEFT JOIN library_staff s ON s.staff_id=l.issued_by WHERE 1=1"""
                params=[]
                if status: sql+=" AND l.status=%s";params.append(status)
                sql+=" ORDER BY l.issue_date DESC,l.loan_id DESC";c.execute(sql,params);return jsonify(c.fetchall())
            d=request.json
            c.execute("SELECT available_copies FROM books WHERE book_id=%s FOR UPDATE",(d["book_id"],)); b=c.fetchone()
            if not b or b["available_copies"]<1: return jsonify({"error":"No available copy for this book"}),400
            c.execute("SELECT COUNT(*) active FROM loans WHERE member_id=%s AND return_date IS NULL",(d["member_id"],))
            active=c.fetchone()["active"]
            c.execute("SELECT max_books FROM members WHERE member_id=%s AND status='Active'",(d["member_id"],));m=c.fetchone()
            if not m:return jsonify({"error":"Member is not active"}),400
            if active>=m["max_books"]:return jsonify({"error":"Member has reached the borrowing limit"}),400
            issue=d.get("issue_date") or date.today().isoformat()
            due=d.get("due_date") or (date.today()+timedelta(days=14)).isoformat()
            c.execute("""INSERT INTO loans(book_id,member_id,issued_by,issue_date,due_date,status,notes)
                         VALUES(%s,%s,%s,%s,%s,'Issued',%s)""",
                      (d["book_id"],d["member_id"],d.get("issued_by") or None,issue,due,d.get("notes")))
            c.execute("""UPDATE books SET available_copies=available_copies-1,
                         status=CASE WHEN available_copies-1<=0 THEN 'Out of Stock'
                         WHEN available_copies-1<=1 THEN 'Low Stock' ELSE 'Available' END
                         WHERE book_id=%s""",(d["book_id"],))
            db.commit();return jsonify({"success":True,"loan_id":c.lastrowid}),201
    except Exception as e:
        db.rollback();return error_response(e)
    finally:db.close()

@app.route("/api/loans/<int:loan_id>/return", methods=["POST"])
def return_book(loan_id):
    db=get_db()
    try:
        with db.cursor() as c:
            c.execute("SELECT * FROM loans WHERE loan_id=%s FOR UPDATE",(loan_id,)); l=c.fetchone()
            if not l:return jsonify({"error":"Loan not found"}),404
            if l["return_date"]:return jsonify({"error":"Book already returned"}),400
            ret=request.json.get("return_date") or date.today().isoformat()
            c.execute("UPDATE loans SET return_date=%s,status='Returned' WHERE loan_id=%s",(ret,loan_id))
            c.execute("""UPDATE books SET available_copies=LEAST(total_copies,available_copies+1),
                         status=CASE WHEN LEAST(total_copies,available_copies+1)<=0 THEN 'Out of Stock'
                         WHEN LEAST(total_copies,available_copies+1)<=1 THEN 'Low Stock' ELSE 'Available' END
                         WHERE book_id=%s""",(l["book_id"],))
            c.execute("SELECT DATEDIFF(%s,due_date) days_late FROM loans WHERE loan_id=%s",(ret,loan_id)); late=c.fetchone()["days_late"]
            fine=0
            if late and late>0:
                fine=late*10
                c.execute("INSERT INTO fines(loan_id,member_id,amount,reason,status) VALUES(%s,%s,%s,%s,'Pending')",
                          (loan_id,l["member_id"],fine,f"Late return: {late} day(s)"))
            db.commit();return jsonify({"success":True,"fine":fine})
    except Exception as e:
        db.rollback();return error_response(e)
    finally:db.close()

@app.route("/api/fines", methods=["GET"])
def fines():
    db=get_db()
    try:
        with db.cursor() as c:
            c.execute("""SELECT f.*,l.issue_date,l.due_date,b.title,m.member_code,
                         CONCAT(m.first_name,' ',COALESCE(m.last_name,'')) member_name
                         FROM fines f JOIN loans l ON l.loan_id=f.loan_id
                         JOIN books b ON b.book_id=l.book_id JOIN members m ON m.member_id=f.member_id
                         ORDER BY f.created_at DESC""")
            return jsonify(c.fetchall())
    finally:db.close()

@app.route("/api/fines/<int:fine_id>/pay", methods=["POST"])
def pay_fine(fine_id):
    db=get_db()
    try:
        with db.cursor() as c:
            c.execute("UPDATE fines SET status='Paid',paid_date=CURDATE() WHERE fine_id=%s AND status='Pending'",(fine_id,))
            db.commit();return jsonify({"success":True})
    except Exception as e:
        db.rollback();return error_response(e)
    finally:db.close()

@app.route("/api/categories")
def categories():
    db=get_db()
    try:
        with db.cursor() as c:c.execute("SELECT * FROM categories ORDER BY category_name");return jsonify(c.fetchall())
    finally:db.close()

@app.route("/api/authors")
def authors():
    db=get_db()
    try:
        with db.cursor() as c:c.execute("SELECT * FROM authors ORDER BY author_name");return jsonify(c.fetchall())
    finally:db.close()

@app.route("/api/publishers")
def publishers():
    db=get_db()
    try:
        with db.cursor() as c:c.execute("SELECT * FROM publishers ORDER BY publisher_name");return jsonify(c.fetchall())
    finally:db.close()

@app.route("/api/staff")
def staff():
    db=get_db()
    try:
        with db.cursor() as c:c.execute("SELECT * FROM library_staff ORDER BY role,first_name");return jsonify(c.fetchall())
    finally:db.close()

@app.route("/api/reservations", methods=["GET","POST"])
def reservations():
    db=get_db()
    try:
        with db.cursor() as c:
            if request.method=="GET":
                c.execute("""SELECT r.*,b.title,m.member_code,
                    CONCAT(m.first_name,' ',COALESCE(m.last_name,'')) member_name
                    FROM reservations r JOIN books b ON b.book_id=r.book_id JOIN members m ON m.member_id=r.member_id
                    ORDER BY r.reservation_date DESC""");return jsonify(c.fetchall())
            d=request.json
            c.execute("INSERT INTO reservations(book_id,member_id,expiry_date) VALUES(%s,%s,%s)",
                      (d["book_id"],d["member_id"],d.get("expiry_date")))
            db.commit();return jsonify({"success":True,"reservation_id":c.lastrowid}),201
    except Exception as e:
        db.rollback();return error_response(e)
    finally:db.close()

if __name__=="__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
