---
mode: agent
---

Plan:

- Review the codebase to identify key modules, classes, and functions to test.
- Determine dependencies and required libraries using context7.
- Use the sequential MCP server and utilize the context7 MCP server for context and orchestration.
- Use sequential thinking to structure tests: setup, execution, and assertions.
- Write tests using pytest, following best practices for readability and maintainability.
- Ensure tests cover typical, edge, and error cases for core functionalities.
- Use fixtures for database/session setup if needed.
- Mock external dependencies where appropriate.

Task:
Generate a comprehensive suite of pytest tests for the codebase.
Requirements:

- Use pytest as the testing framework.
- Import and utilize necessary libraries as identified in context7.
- Use the sequential MCP server and leverage the context7 MCP server for context management.
- Write tests for main modules, focusing on public methods and critical logic.
- Include tests for database interactions, ensuring queries return expected results.
- Test error handling and edge cases.
- Use type hints and docstrings in test functions for clarity.
- Organize tests modularly, grouping by feature or module.
- Use fixtures for setup/teardown where appropriate.
- Mock external APIs or services if present.
- Ensure tests are readable, maintainable, and follow project conventions.

Success Criteria:

- All major functionalities are covered by tests.
- Tests are passing and can be run with `pytest`.
- Tests are modular, clear, and follow codebase conventions.
- Edge cases and error handling are tested.
- Database interactions are tested with fixtures/mocks as needed.
