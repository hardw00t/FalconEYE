"""
Database module.

This module handles all database operations.
"""

import sqlite3
from typing import List, Dict, Any


class Database:
    """Database connection and query handler."""

    def __init__(self, db_path: str = 'app.db'):
        """Initialize database connection."""
        self.db_path = db_path
        self.connection = None

    def connect(self):
        """Establish database connection."""
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Execute SQL query and return results.

        Args:
            query: SQL query string to execute

        Returns:
            List of result rows as dictionaries
        """
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()

        return [dict(row) for row in results]

    def search_products(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search for products by name.

        Args:
            search_term: Product name to search for

        Returns:
            List of matching products
        """
        # VULNERABLE: String concatenation in SQL query
        query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
        return self.execute_query(query)

    def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Get user by ID.

        Args:
            user_id: User identifier

        Returns:
            User data dictionary
        """
        # VULNERABLE: String formatting in SQL
        query = f"SELECT * FROM users WHERE id = {user_id}"
        results = self.execute_query(query)
        return results[0] if results else None

    def find_user_by_username(self, username: str) -> Dict[str, Any]:
        """
        Find user by username.

        Args:
            username: Username to search

        Returns:
            User data or None
        """
        # VULNERABLE: String interpolation
        query = "SELECT * FROM users WHERE username = '" + username + "'"
        results = self.execute_query(query)
        return results[0] if results else None

    def get_sorted_items(self, table: str, sort_column: str) -> List[Dict[str, Any]]:
        """
        Get items from table sorted by column.

        Args:
            table: Table name
            sort_column: Column to sort by

        Returns:
            Sorted list of items
        """
        # VULNERABLE: Dynamic column name without validation
        query = f"SELECT * FROM {table} ORDER BY {sort_column}"
        return self.execute_query(query)

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None