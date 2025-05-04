from flask import Flask, request, jsonify, render_template_string
import psycopg2
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from S3

# Configure logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s %(levelname)s: %(message)s')

# Database connection
conn = psycopg2.connect(
    host='db-xusanboy.clyucs4e44b4.ap-northeast-2.rds.amazonaws.com',
    database='mydatabase',
    user='postgres',
    password='postgres'
)
cur = conn.cursor()

# Helper to clean/convert data
def clean_value(value):
    if isinstance(value, str):
        value = value.strip()
        if value.lower() in ['nan', '', '__', 'hello']:
            return None
        return value.replace(',', '') if ',' in value else value
    return value

# Root route (HTML view)
@app.route('/')
def home():
    cur.execute("SELECT * FROM tbl_xusanboy_books_data")
    books = cur.fetchall()

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Xusanboy's Library API</title>
        <link rel="stylesheet" href="styles.css">
    </head>
    <body>
        <header>
   <h1>📚 Xusanboy's Library API</h1>
            <p>Welcome to the Xusanboy Library API. This API provides data about books in the library.</p>
        </header>
        <section>
            <h2>Book Data</h2>
            <table border="1">
                <thead>
                    <tr>
                        <th>Book ID</th>
                        <th>Title</th>
                        <th>Author</th>
                        <th>Category</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for book in books %}
                    <tr>
                        <td>{{ book[0] }}</td>
                        <td>{{ book[1] }}</td>
                        <td>{{ book[2] }}</td>
                        <td>{{ book[3] }}</td>
                        <td>{{ book[4] }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="5">No book data available.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>
        <footer>
            <p>Powered by Xusanboy | API Documentation</p>
        </footer>
    </body>
    </html>
    """
    return render_template_string(html_content, books=books)

# Endpoint to provide JSON data
@app.route('/data', methods=['GET'])
def get_data():
    try:
 cur.execute("SELECT * FROM tbl_xusanboy_books_data")
        books = cur.fetchall()
        return jsonify([{
            'bid': book[0],
            'title': book[1],
            'author': book[2],
            'category': book[3],
            'status': book[4]
        } for book in books])
    except Exception as e:
        logging.error(f"Error fetching data: {str(e)}")
        return jsonify({'error': f"Error fetching data: {str(e)}"}), 500

# Endpoint to add a new book
@app.route('/add', methods=['POST'])
def add():
    data = request.get_json()
    logging.info(f"Received add request: {data}")
    title = clean_value(data.get('title'))
    author = clean_value(data.get('author'))
    category = clean_value(data.get('category'))
    status = clean_value(data.get('status'))
    if not all([title, author, category, status]):
        logging.error("Missing required fields")
        return jsonify({'error': 'All fields (title, author, category, status) are required'}), 400
    try:
        cur.execute("""
            INSERT INTO tbl_xusanboy_books_data (title, author, category, status)
            VALUES (%s, %s, %s, %s) RETURNING bid
        """, (title, author, category, status))
        bid = cur.fetchone()[0]
        conn.commit()
        logging.info(f"Inserted book with bid: {bid}")
        return jsonify({'status': 'Data inserted successfully', 'bid': bid})
    except Exception as e:
        conn.rollback()
        logging.error(f"Error inserting data: {str(e)}")
        return jsonify({'error': f"Error inserting data: {str(e)}"}), 500

# Endpoint to delete a book
@app.route('/delete', methods=['POST'])
def delete():
    data = request.get_json()
    bid = data.get('bid')
    logging.info(f"Received delete request for bid: {bid}")
    if not bid:
        logging.error("Missing bid field")
        return jsonify({'error': 'bid is required'}), 400
    try:
        cur.execute("DELETE FROM tbl_xusanboy_books_data WHERE bid = %s", (bid,))
        if cur.rowcount == 0:
            logging.warning(f"No book found with bid: {bid}")
            return jsonify({'error': 'No book found with the specified bid'}), 404
        conn.commit()
        logging.info(f"Deleted book with bid: {bid}")
        return jsonify({'status': 'Data deleted successfully'})
    except Exception as e:
        conn.rollback()
        logging.error(f"Error deleting data: {str(e)}")
        return jsonify({'error': f"Error deleting data: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)