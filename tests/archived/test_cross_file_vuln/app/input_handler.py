"""
Input handler module.

This module handles user input from web requests.
"""

from flask import request


def get_user_search_query():
    """
    Get search query from user input.

    Returns:
        str: User-provided search query from HTTP request
    """
    # Get search parameter from query string
    query = request.args.get('q', '')
    return query


def get_user_id():
    """
    Get user ID from request.

    Returns:
        str: User ID from request parameters
    """
    user_id = request.args.get('id', '')
    return user_id


def get_username_from_form():
    """
    Get username from POST form data.

    Returns:
        str: Username submitted via form
    """
    username = request.form.get('username', '')
    return username


def get_sort_column():
    """
    Get sort column from query parameters.

    Returns:
        str: Column name to sort by
    """
    return request.args.get('sort', 'created_at')