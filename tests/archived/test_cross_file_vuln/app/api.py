"""
API endpoints module.

This module defines the REST API endpoints for the application.
"""

from flask import Flask, jsonify
from .input_handler import (
    get_user_search_query,
    get_user_id,
    get_username_from_form,
    get_sort_column
)
from .database import Database

app = Flask(__name__)
db = Database()


@app.route('/api/search')
def search_products():
    """
    Search for products endpoint.

    This endpoint searches products based on user query.
    The data flow is:
    1. User provides 'q' parameter in URL
    2. input_handler.get_user_search_query() extracts it
    3. database.search_products() executes SQL query
    4. Results returned as JSON

    VULNERABILITY: SQL Injection
    - User input flows from request → database query
    - No sanitization or parameterization
    """
    # Get user input (TAINTED SOURCE)
    search_query = get_user_search_query()

    # Execute database query (SINK)
    results = db.search_products(search_query)

    return jsonify({
        'status': 'success',
        'results': results,
        'query': search_query
    })


@app.route('/api/user/<user_id>')
def get_user(user_id):
    """
    Get user by ID endpoint.

    VULNERABILITY: SQL Injection via path parameter
    - user_id comes from URL path
    - No validation or sanitization
    - Passed directly to database query
    """
    # user_id is TAINTED (from URL path)

    # Get more details from query params
    additional_id = get_user_id()

    # Execute query (SINK)
    user = db.get_user_by_id(user_id if user_id else additional_id)

    if user:
        return jsonify(user)
    else:
        return jsonify({'error': 'User not found'}), 404


@app.route('/api/login', methods=['POST'])
def login():
    """
    User login endpoint.

    VULNERABILITY: SQL Injection via form data
    - Username from POST form
    - No validation
    - String concatenation in SQL
    """
    # Get username from form (TAINTED SOURCE)
    username = get_username_from_form()

    # Look up user (SINK)
    user = db.find_user_by_username(username)

    if user:
        return jsonify({
            'status': 'success',
            'user_id': user['id']
        })
    else:
        return jsonify({'error': 'Invalid credentials'}), 401


@app.route('/api/items')
def list_items():
    """
    List items with sorting.

    VULNERABILITY: SQL Injection via sort parameter
    - Sort column from query string
    - No whitelist validation
    - Dynamic SQL construction
    """
    # Get sort preference (TAINTED SOURCE)
    sort_by = get_sort_column()

    # Get items sorted (SINK)
    items = db.get_sorted_items('products', sort_by)

    return jsonify({
        'items': items,
        'sorted_by': sort_by
    })


if __name__ == '__main__':
    app.run(debug=True)