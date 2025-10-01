# Cross-File SQL Injection Test Project

This is a deliberately vulnerable Flask application designed to test FalconEYE's ability to detect cross-file security vulnerabilities through RAG (Retrieval-Augmented Generation).

## Project Structure

```
test_cross_file_vuln/
├── README.md                 # This file
├── app/
│   ├── __init__.py          # Package initialization
│   ├── input_handler.py     # User input extraction (TAINTED SOURCES)
│   ├── database.py          # Database operations (VULNERABLE SINKS)
│   └── api.py               # API endpoints (CONNECTS SOURCES TO SINKS)
```

## Vulnerability Pattern: Cross-File Data Flow

### The Security Issue

This application demonstrates SQL injection vulnerabilities that span multiple files:

1. **File 1 (input_handler.py)**: User input extraction
   - `get_user_search_query()` - Gets search query from HTTP request
   - `get_user_id()` - Gets user ID from request
   - `get_username_from_form()` - Gets username from form
   - `get_sort_column()` - Gets sort column name

2. **File 2 (database.py)**: Database operations
   - `search_products(search_term)` - Uses string concatenation in SQL
   - `get_user_by_id(user_id)` - Uses f-string formatting in SQL
   - `find_user_by_username(username)` - Uses string concatenation
   - `get_sorted_items(table, sort_column)` - Dynamic SQL without validation

3. **File 3 (api.py)**: Connects tainted sources to vulnerable sinks
   - Imports functions from both files
   - Passes user input directly to database functions
   - No sanitization or validation

### Data Flow Example

```
HTTP Request
    ↓
[api.py] search_products()
    ↓
[input_handler.py] get_user_search_query()
    ↓ (returns user input)
[api.py] receives tainted data
    ↓
[database.py] search_products(search_term)
    ↓
VULNERABLE: f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
```

## Expected Vulnerabilities

FalconEYE should detect the following SQL injection vulnerabilities:

### 1. Search Endpoint - SQL Injection
- **Source**: `input_handler.get_user_search_query()` (line ~12)
- **Sink**: `database.search_products()` (line ~45)
- **Flow**: api.py connects them without sanitization
- **Severity**: HIGH/CRITICAL

### 2. User Lookup - SQL Injection
- **Source**: URL path parameter in `api.get_user()`
- **Sink**: `database.get_user_by_id()` (line ~54)
- **Flow**: Path parameter → database query
- **Severity**: HIGH/CRITICAL

### 3. Login - SQL Injection
- **Source**: `input_handler.get_username_from_form()` (line ~33)
- **Sink**: `database.find_user_by_username()` (line ~62)
- **Flow**: POST form data → string concatenation in SQL
- **Severity**: CRITICAL

### 4. Sort Parameter - SQL Injection
- **Source**: `input_handler.get_sort_column()` (line ~42)
- **Sink**: `database.get_sorted_items()` (line ~71)
- **Flow**: Query parameter → dynamic column name in ORDER BY
- **Severity**: HIGH

## Testing with FalconEYE

### Step 1: Index the Project

```bash
cd /Users/w00t/Documents/projects/AI_Research/FalconEYE/FalconEYE_v2.0
falconeye index test_cross_file_vuln --language python
```

Expected output:
- 4 Python files indexed
- Embeddings generated for all code chunks
- AST metadata extracted

### Step 2: Scan for Vulnerabilities

```bash
falconeye scan test_cross_file_vuln
```

### Step 3: Review Individual Files

Test cross-file detection by analyzing the API file:

```bash
falconeye review test_cross_file_vuln/app/api.py
```

**What to look for**:
- FalconEYE should identify that user input functions return tainted data
- Should trace data flow from input handlers to database queries
- Should detect SQL injection even though source and sink are in different files

### Step 4: Verify RAG Context Retrieval

When analyzing `api.py`, FalconEYE should:
1. Read the API endpoint code
2. See imports: `from .input_handler import get_user_search_query`
3. Use RAG to retrieve the implementation of `get_user_search_query()` from `input_handler.py`
4. Use RAG to retrieve the implementation of `search_products()` from `database.py`
5. Reason about the complete data flow across all three files
6. Identify SQL injection vulnerability

## Expected AI Reasoning

The AI should reason as follows:

```
Analysis of /api.py:search_products():

1. Observed: Function calls get_user_search_query()
2. RAG Retrieved: Implementation shows it returns request.args.get('q')
   - This is user-controlled input (TAINTED SOURCE)

3. Observed: User input passed to db.search_products(search_query)
4. RAG Retrieved: Implementation shows:
   query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
   - String concatenation in SQL query (VULNERABLE SINK)

5. Conclusion: Tainted data flows from HTTP request → database query
   - No sanitization or parameterization
   - SQL injection vulnerability present

Severity: CRITICAL
Confidence: HIGH
```

## Why This Tests Cross-File Detection

This project specifically tests whether FalconEYE can:

1. ✓ **Detect vulnerabilities across file boundaries**
   - Source in `input_handler.py`
   - Sink in `database.py`
   - Connection in `api.py`

2. ✓ **Use RAG to retrieve relevant context**
   - When analyzing `api.py`, retrieve implementations from other files
   - Understand what imported functions do

3. ✓ **Reason about data flow without explicit call graph**
   - No AST-based cross-file tracking
   - Relies on semantic similarity to find related code
   - AI infers the vulnerability through reasoning

4. ✓ **Distinguish between different vulnerability types**
   - SQL injection via query string
   - SQL injection via path parameter
   - SQL injection via POST form
   - SQL injection via dynamic column names

## Secure vs Vulnerable Comparison

### Vulnerable (Current Code)
```python
# input_handler.py
def get_user_search_query():
    return request.args.get('q', '')

# database.py
def search_products(self, search_term: str):
    query = f"SELECT * FROM products WHERE name LIKE '%{search_term}%'"
    return self.execute_query(query)
```

### Secure (How It Should Be)
```python
# input_handler.py
def get_user_search_query():
    # Still returns user input, but consumers should sanitize
    return request.args.get('q', '')

# database.py
def search_products(self, search_term: str):
    # Use parameterized queries
    query = "SELECT * FROM products WHERE name LIKE ?"
    cursor.execute(query, (f'%{search_term}%',))
    return cursor.fetchall()
```

## Notes

- This is a **test application only** - DO NOT deploy to production
- All vulnerabilities are intentional for security testing
- This demonstrates FalconEYE's RAG-based cross-file analysis capabilities
- No actual database is included - this tests static analysis only

## Success Criteria

FalconEYE successfully passes this test if it:

- [x] Detects at least 3-4 SQL injection vulnerabilities
- [x] Correctly identifies severity as HIGH or CRITICAL
- [x] Shows understanding that data flows across files
- [x] Provides reasoning that references both source and sink
- [x] Includes line numbers for vulnerabilities
- [x] Suggests parameterized queries as mitigation