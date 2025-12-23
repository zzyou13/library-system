from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import mysql.connector
from datetime import datetime, date, timedelta
import hashlib
import json
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'library_system_secret_key'
CORS(app)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'password',
    'database': 'library_db'
}

def get_db_connection():
    """获取数据库连接"""
    return mysql.connector.connect(**DB_CONFIG)

def hash_password(password):
    """密码加密"""
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    """管理员登录"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute(
            "SELECT * FROM admin WHERE username = %s AND password = %s",
            (username, hash_password(password))
        )
        admin = cursor.fetchone()
        
        if admin:
            session['admin_id'] = admin['admin_id']
            session['username'] = admin['username']
            return jsonify({'success': True, 'message': '登录成功'})
        else:
            return jsonify({'success': False, 'message': '用户名或密码错误'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/register_reader', methods=['POST'])
def register_reader():
    """注册读者"""
    data = request.json
    name = data.get('name')
    gender = data.get('gender')
    phone = data.get('phone')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO reader (name, gender, phone) VALUES (%s, %s, %s)",
            (name, gender, phone)
        )
        conn.commit()
        return jsonify({'success': True, 'message': '读者注册成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/add_book', methods=['POST'])
def add_book():
    """添加书籍"""
    data = request.json
    book_name = data.get('book_name')
    author = data.get('author')
    publisher = data.get('publisher')
    category_name = data.get('category_name')
    total_count = data.get('total_count', 1)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取或创建分类
        cursor.execute("SELECT category_id FROM category WHERE category_name = %s", (category_name,))
        category = cursor.fetchone()
        
        if not category:
            cursor.execute(
                "INSERT INTO category (category_name) VALUES (%s)",
                (category_name,)
            )
            category_id = cursor.lastrowid
        else:
            category_id = category[0]
        
        # 检查书籍是否已存在
        cursor.execute(
            "SELECT book_id FROM book WHERE book_name = %s AND author = %s",
            (book_name, author)
        )
        existing_book = cursor.fetchone()
        
        if existing_book:
            # 如果存在，增加库存
            cursor.execute(
                "UPDATE book SET total_count = total_count + %s, available_count = available_count + %s WHERE book_id = %s",
                (total_count, total_count, existing_book[0])
            )
        else:
            # 添加新书
            cursor.execute(
                """INSERT INTO book (book_name, author, publisher, category_id, total_count, available_count) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (book_name, author, publisher, category_id, total_count, total_count)
            )
        
        conn.commit()
        return jsonify({'success': True, 'message': '书籍添加成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/delete_book/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """删除书籍"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查书籍是否被借出
        cursor.execute(
            "SELECT COUNT(*) FROM borrow WHERE book_id = %s AND actual_return_date IS NULL",
            (book_id,)
        )
        borrowed_count = cursor.fetchone()[0]
        
        if borrowed_count > 0:
            return jsonify({'success': False, 'message': '该书已被借出，无法删除'})
        
        cursor.execute("DELETE FROM book WHERE book_id = %s", (book_id,))
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': '书籍删除成功'})
        else:
            return jsonify({'success': False, 'message': '未找到该书籍'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/list_books', methods=['GET'])
def list_books():
    """列出所有书籍"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT b.*, c.category_name 
            FROM book b 
            LEFT JOIN category c ON b.category_id = c.category_id
            ORDER BY b.book_id
        """)
        books = cursor.fetchall()
        return jsonify({'success': True, 'data': books})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/search_books', methods=['GET'])
def search_books():
    """搜索书籍"""
    keyword = request.args.get('keyword', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT b.*, c.category_name 
            FROM book b 
            LEFT JOIN category c ON b.category_id = c.category_id
            WHERE b.book_name LIKE %s OR b.author LIKE %s OR b.publisher LIKE %s
        """, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
        
        books = cursor.fetchall()
        return jsonify({'success': True, 'data': books})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/search_by_author', methods=['GET'])
def search_by_author():
    """根据作者搜索书籍"""
    author = request.args.get('author', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT b.*, c.category_name 
            FROM book b 
            LEFT JOIN category c ON b.category_id = c.category_id
            WHERE b.author LIKE %s
        """, (f'%{author}%',))
        
        books = cursor.fetchall()
        return jsonify({'success': True, 'data': books})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/update_book/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """更新书籍信息"""
    data = request.json
    book_name = data.get('book_name')
    author = data.get('author')
    publisher = data.get('publisher')
    category_name = data.get('category_name')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取分类ID
        cursor.execute("SELECT category_id FROM category WHERE category_name = %s", (category_name,))
        category = cursor.fetchone()
        
        if not category:
            cursor.execute("INSERT INTO category (category_name) VALUES (%s)", (category_name,))
            category_id = cursor.lastrowid
        else:
            category_id = category[0]
        
        # 更新书籍信息
        cursor.execute("""
            UPDATE book 
            SET book_name = %s, author = %s, publisher = %s, category_id = %s
            WHERE book_id = %s
        """, (book_name, author, publisher, category_id, book_id))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': '书籍信息更新成功'})
        else:
            return jsonify({'success': False, 'message': '未找到该书籍'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/borrow_book', methods=['POST'])
def borrow_book():
    """借书"""
    data = request.json
    reader_id = data.get('reader_id')
    book_id = data.get('book_id')
    borrow_date = date.today()
    
    # 计算还书日期（借阅30天）
    return_date = date.fromordinal(borrow_date.toordinal() + 30)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查读者是否存在
        cursor.execute("SELECT reader_id FROM reader WHERE reader_id = %s", (reader_id,))
        if not cursor.fetchone():
            return jsonify({'success': False, 'message': '读者不存在'})
        
        # 检查书籍库存
        cursor.execute("SELECT available_count FROM book WHERE book_id = %s", (book_id,))
        book = cursor.fetchone()
        
        if not book:
            return jsonify({'success': False, 'message': '书籍不存在'})
        
        if book[0] <= 0:
            return jsonify({'success': False, 'message': '该书已被全部借出'})
        
        # 创建借阅记录
        cursor.execute("""
            INSERT INTO borrow (reader_id, book_id, borrow_date, return_date, status)
            VALUES (%s, %s, %s, %s, '借出')
        """, (reader_id, book_id, borrow_date, return_date))
        
        # 更新书籍可用数量
        cursor.execute("""
            UPDATE book SET available_count = available_count - 1 
            WHERE book_id = %s AND available_count > 0
        """, (book_id,))
        
        conn.commit()
        return jsonify({'success': True, 'message': '借书成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/return_book', methods=['POST'])
def return_book():
    """还书"""
    data = request.json
    borrow_id = data.get('borrow_id')
    actual_return_date = date.today()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取借书记录和书籍ID
        cursor.execute("SELECT book_id FROM borrow WHERE borrow_id = %s", (borrow_id,))
        record = cursor.fetchone()
        
        if not record:
            return jsonify({'success': False, 'message': '借书记录不存在'})
        
        book_id = record[0]
        
        # 更新借书记录
        cursor.execute("""
            UPDATE borrow 
            SET actual_return_date = %s, status = '已归还'
            WHERE borrow_id = %s AND actual_return_date IS NULL
        """, (actual_return_date, borrow_id))
        
        # 更新书籍可用数量
        cursor.execute("""
            UPDATE book SET available_count = available_count + 1 
            WHERE book_id = %s
        """, (book_id,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            return jsonify({'success': True, 'message': '还书成功'})
        else:
            return jsonify({'success': False, 'message': '该书已归还或记录不存在'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/borrow_records', methods=['GET'])
def borrow_records():
    """查看借书记录"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT b.borrow_id, r.name as reader_name, bk.book_name, 
                   b.borrow_date, b.return_date, b.actual_return_date, b.status
            FROM borrow b
            JOIN reader r ON b.reader_id = r.reader_id
            JOIN book bk ON b.book_id = bk.book_id
            ORDER BY b.borrow_date DESC
        """)
        records = cursor.fetchall()
        return jsonify({'success': True, 'data': records})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/list_readers', methods=['GET'])
def list_readers():
    """列出所有读者"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM reader ORDER BY reader_id")
        readers = cursor.fetchall()
        return jsonify({'success': True, 'data': readers})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

# ==================== 新增的复杂查询和统计功能 ====================

@app.route('/api/statistics/book_popularity', methods=['GET'])
def book_popularity():
    """书籍借阅排行榜（复杂查询：多表联接 + 聚合函数）"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                b.book_id,
                b.book_name,
                b.author,
                COUNT(br.borrow_id) as borrow_count,
                b.total_count,
                b.available_count,
                c.category_name
            FROM book b
            LEFT JOIN borrow br ON b.book_id = br.book_id
            LEFT JOIN category c ON b.category_id = c.category_id
            GROUP BY b.book_id, b.book_name, b.author, b.total_count, b.available_count, c.category_name
            ORDER BY borrow_count DESC
            LIMIT 20
        """)
        popular_books = cursor.fetchall()
        return jsonify({'success': True, 'data': popular_books})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/statistics/reader_activity', methods=['GET'])
def reader_activity():
    """读者借阅活跃度统计（复杂查询：多表联接 + 聚合函数）"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                r.reader_id,
                r.name,
                r.gender,
                COUNT(br.borrow_id) as total_borrow,
                COUNT(CASE WHEN br.actual_return_date IS NULL THEN 1 END) as current_borrow,
                MIN(br.borrow_date) as first_borrow_date,
                MAX(br.borrow_date) as latest_borrow_date
            FROM reader r
            LEFT JOIN borrow br ON r.reader_id = br.reader_id
            GROUP BY r.reader_id, r.name, r.gender
            ORDER BY total_borrow DESC
        """)
        reader_stats = cursor.fetchall()
        return jsonify({'success': True, 'data': reader_stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/statistics/category_distribution', methods=['GET'])
def category_distribution():
    """图书分类分布统计（复杂查询：多表联接 + 聚合函数）"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT 
                c.category_id,
                c.category_name,
                COUNT(b.book_id) as book_count,
                SUM(b.total_count) as total_copies,
                SUM(b.available_count) as available_copies,
                COALESCE(SUM(br.borrow_count), 0) as total_borrow
            FROM category c
            LEFT JOIN book b ON c.category_id = b.category_id
            LEFT JOIN (
                SELECT book_id, COUNT(*) as borrow_count
                FROM borrow
                GROUP BY book_id
            ) br ON b.book_id = br.book_id
            GROUP BY c.category_id, c.category_name
            ORDER BY book_count DESC
        """)
        category_stats = cursor.fetchall()
        return jsonify({'success': True, 'data': category_stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/statistics/overdue_books', methods=['GET'])
def overdue_books():
    """逾期未还书籍查询（复杂查询：条件过滤 + 日期计算）"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        today = date.today()
        cursor.execute("""
            SELECT 
                br.borrow_id,
                r.reader_id,
                r.name as reader_name,
                r.phone,
                b.book_id,
                b.book_name,
                b.author,
                br.borrow_date,
                br.return_date,
                DATEDIFF(%s, br.return_date) as overdue_days,
                CASE 
                    WHEN DATEDIFF(%s, br.return_date) <= 0 THEN '未逾期'
                    ELSE CONCAT('逾期', DATEDIFF(%s, br.return_date), '天')
                END as overdue_status
            FROM borrow br
            JOIN reader r ON br.reader_id = r.reader_id
            JOIN book b ON br.book_id = b.book_id
            WHERE br.actual_return_date IS NULL
            AND br.return_date < %s
            AND br.status = '借出'
            ORDER BY overdue_days DESC
        """, (today, today, today, today))
        
        overdue_books = cursor.fetchall()
        return jsonify({'success': True, 'data': overdue_books})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/statistics/borrow_trend', methods=['GET'])
def borrow_trend():
    """借阅趋势统计（复杂查询：按时间分组聚合）"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取最近30天的借阅趋势
        cursor.execute("""
            SELECT 
                DATE(borrow_date) as borrow_day,
                COUNT(*) as borrow_count,
                COUNT(DISTINCT reader_id) as unique_readers
            FROM borrow
            WHERE borrow_date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(borrow_date)
            ORDER BY borrow_day
        """)
        
        trend_data = cursor.fetchall()
        
        # 按月统计
        cursor.execute("""
            SELECT 
                DATE_FORMAT(borrow_date, '%%Y-%%m') as borrow_month,
                COUNT(*) as borrow_count,
                COUNT(DISTINCT reader_id) as unique_readers
            FROM borrow
            WHERE borrow_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
            GROUP BY DATE_FORMAT(borrow_date, '%%Y-%%m')
            ORDER BY borrow_month
        """)
        
        monthly_data = cursor.fetchall()
        
        return jsonify({
            'success': True, 
            'data': {
                'daily': trend_data,
                'monthly': monthly_data
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/statistics/library_overview', methods=['GET'])
def library_overview():
    """图书馆总览统计（多个聚合查询）"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 总书籍数
        cursor.execute("SELECT COUNT(*) as total_books, SUM(total_count) as total_copies FROM book")
        book_stats = cursor.fetchone()
        
        # 总读者数
        cursor.execute("SELECT COUNT(*) as total_readers FROM reader")
        reader_stats = cursor.fetchone()
        
        # 借阅统计
        cursor.execute("""
            SELECT 
                COUNT(*) as total_borrows,
                COUNT(CASE WHEN actual_return_date IS NULL THEN 1 END) as current_borrows,
                COUNT(CASE WHEN actual_return_date IS NOT NULL THEN 1 END) as returned_borrows
            FROM borrow
        """)
        borrow_stats = cursor.fetchone()
        
        # 逾期统计
        today = date.today()
        cursor.execute("""
            SELECT COUNT(*) as overdue_count
            FROM borrow
            WHERE actual_return_date IS NULL
            AND return_date < %s
            AND status = '借出'
        """, (today,))
        overdue_stats = cursor.fetchone()
        
        # 热门作者
        cursor.execute("""
            SELECT author, COUNT(*) as book_count
            FROM book
            GROUP BY author
            ORDER BY book_count DESC
            LIMIT 5
        """)
        top_authors = cursor.fetchall()
        
        return jsonify({
            'success': True,
            'data': {
                'books': book_stats,
                'readers': reader_stats,
                'borrows': borrow_stats,
                'overdue': overdue_stats,
                'top_authors': top_authors
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

# ==================== AI/LLM集成功能（可选） ====================

@app.route('/api/recommend/books', methods=['GET'])
def recommend_books():
    """智能推荐书籍（基于借阅历史）"""
    reader_id = request.args.get('reader_id', type=int)
    
    if not reader_id:
        return jsonify({'success': False, 'message': '请提供读者ID'})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取读者借阅历史
        cursor.execute("""
            SELECT DISTINCT b.category_id, b.author
            FROM borrow br
            JOIN book b ON br.book_id = b.book_id
            WHERE br.reader_id = %s
        """, (reader_id,))
        
        history = cursor.fetchall()
        
        if not history:
            # 如果没有借阅历史，推荐热门书籍
            cursor.execute("""
                SELECT b.*, c.category_name
                FROM book b
                LEFT JOIN category c ON b.category_id = c.category_id
                WHERE b.available_count > 0
                ORDER BY (
                    SELECT COUNT(*) 
                    FROM borrow br 
                    WHERE br.book_id = b.book_id
                ) DESC
                LIMIT 10
            """)
        else:
            # 基于借阅历史推荐相似书籍
            category_ids = [str(item['category_id']) for item in history if item['category_id']]
            authors = [item['author'] for item in history if item['author']]
            
            # 构建查询条件
            conditions = []
            params = []
            
            if category_ids:
                conditions.append("b.category_id IN (%s)" % ",".join(['%s'] * len(category_ids)))
                params.extend(category_ids)
            
            if authors:
                conditions.append("b.author IN (%s)" % ",".join(['%s'] * len(authors)))
                params.extend(authors)
            
            where_clause = " OR ".join(conditions) if conditions else "1=1"
            
            query = f"""
                SELECT DISTINCT b.*, c.category_name
                FROM book b
                LEFT JOIN category c ON b.category_id = c.category_id
                WHERE b.available_count > 0
                AND ({where_clause})
                AND b.book_id NOT IN (
                    SELECT book_id 
                    FROM borrow 
                    WHERE reader_id = %s 
                    AND actual_return_date IS NULL
                    AND status = '借出'
                )
                ORDER BY b.available_count DESC
                LIMIT 10
            """
            
            params.append(reader_id)
            cursor.execute(query, params)
        
        recommendations = cursor.fetchall()
        return jsonify({'success': True, 'data': recommendations})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/recommend/similar_books', methods=['GET'])
def similar_books():
    """基于当前书籍推荐相似书籍"""
    book_id = request.args.get('book_id', type=int)
    
    if not book_id:
        return jsonify({'success': False, 'message': '请提供书籍ID'})
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # 获取当前书籍信息
        cursor.execute("""
            SELECT category_id, author, book_name
            FROM book
            WHERE book_id = %s
        """, (book_id,))
        
        current_book = cursor.fetchone()
        
        if not current_book:
            return jsonify({'success': False, 'message': '书籍不存在'})
        
        # 推荐同分类或同作者的书籍
        cursor.execute("""
            SELECT b.*, c.category_name
            FROM book b
            LEFT JOIN category c ON b.category_id = c.category_id
            WHERE b.available_count > 0
            AND b.book_id != %s
            AND (b.category_id = %s OR b.author = %s)
            ORDER BY (
                SELECT COUNT(*) 
                FROM borrow br 
                WHERE br.book_id = b.book_id
            ) DESC
            LIMIT 8
        """, (book_id, current_book['category_id'], current_book['author']))
        
        similar_books = cursor.fetchall()
        
        # 如果结果不足，补充热门书籍
        if len(similar_books) < 5:
            cursor.execute("""
                SELECT b.*, c.category_name
                FROM book b
                LEFT JOIN category c ON b.category_id = c.category_id
                WHERE b.available_count > 0
                AND b.book_id != %s
                AND b.book_id NOT IN (SELECT book_id FROM (
                    SELECT book_id FROM book 
                    WHERE category_id = %s OR author = %s
                    LIMIT 10
                ) as excluded)
                ORDER BY (
                    SELECT COUNT(*) 
                    FROM borrow br 
                    WHERE br.book_id = b.book_id
                ) DESC
                LIMIT %s
            """, (book_id, current_book['category_id'], current_book['author'], 8 - len(similar_books)))
            
            additional_books = cursor.fetchall()
            similar_books.extend(additional_books)
        
        return jsonify({'success': True, 'data': similar_books})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
