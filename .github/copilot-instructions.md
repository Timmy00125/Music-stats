# GitHub Copilot Instructions for Music-stats Project

## General Guidelines

1.  **Language:** All code should be written in Python.
2.  **Type Hinting:** Use type hints for all function signatures (arguments and return types) and variable declarations where appropriate. Utilize the `typing` module (e.g., `List`, `Dict`, `Any`, `Optional`).
3.  **Docstrings:** Write clear and concise docstrings for all public classes and methods. For non-trivial private methods (prefixed with `_`), also include docstrings. Follow standard Python docstring conventions.
4.  **Naming Conventions:**
    - Classes: `CapWords` (e.g., `InsightsGenerator`)
    - Methods and Functions: `snake_case` (e.g., `get_detailed_insights`, `_get_recent_favorites`)
    - Variables: `snake_case` (e.g., `cutoff_date`, `listen_count`)
    - Constants: `UPPER_SNAKE_CASE`
5.  **Modularity:** Keep functions and methods focused on a single responsibility. Private helper methods should be prefixed with an underscore (e.g., `_calculate_average`).
6.  **Database Interaction:**
    - When interacting with the database (presumably SQLAlchemy, based on existing code like `self.db.query`), ensure queries are efficient.
    - Use ORM features where possible.
    - Clearly label aggregated columns (e.g., `func.count(ListeningHistory.id).label("listen_count")`).
7.  **Error Handling:** Implement basic error handling where necessary (e.g., checking for empty query results, handling potential `None` values).
8.  **Readability:** Prioritize clear and readable code. Use comments to explain complex logic where docstrings are not sufficient.
9.  **Imports:** Organize imports standardly: standard library, third-party libraries, then project-specific modules.
10. **Data Structures:** Return structured data, often as `List[Dict[str, Any]]` or `Dict[str, Any]`, for API-like responses or internal data passing.

## Specific Patterns from `insights.py`

- **Insight Generation:** Methods that generate insights often query a database, process the results, and return them in a structured dictionary or list of dictionaries.
- **Helper Methods:** Complex calculations or data transformations are often broken down into private helper methods (e.g., `_get_listening_by_time_of_day`, `_get_audio_features_averages`).
- **Date/Time Handling:** Use `datetime` and `timedelta` from the `datetime` module for date calculations.
- **SQLAlchemy Usage:**
  - `self.db.query(...)` is the primary way to build queries.
  - Use `filter()` for WHERE clauses.
  - Use `group_by()` for aggregations.
  - Use `order_by()` with `desc()` or `asc()` for sorting.
  - Use `limit()` for restricting the number of results.
  - Use `.all()` to execute the query and get all results, `.scalar()` for a single value.
  - Use `func` for SQL functions (e.g., `func.count`, `func.avg`).
  - Use `distinct` for unique values.

## When Generating New Code

- **Understand Context:** Pay attention to the existing class structure (e.g., `InsightsGenerator`) and try to fit new functionality within it logically.
- **Re-use Existing Logic:** If similar functionality exists, try to adapt or extend it rather than writing completely new code.
- **Follow the Style:** Adhere strictly to the type hinting, naming conventions, and docstring practices observed in the existing codebase.
- **Database Models:** Assume the existence of SQLAlchemy models like `ListeningHistory` and `AudioFeatures` with relevant fields. If new fields are needed, make a note, but primarily work with existing schema assumptions.
