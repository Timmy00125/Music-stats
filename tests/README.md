# Test Suite for Music-stats

## Overview

This directory contains comprehensive pytest tests for the Music-stats application, covering all major modules and functionalities.

## Test Structure

### Test Files

- `test_auth.py` - Tests for authentication and JWT token management
- `test_insights.py` - Tests for music insights generation functionality
- `test_main.py` - Tests for FastAPI endpoints
- `test_models.py` - Tests for SQLAlchemy database models
- `test_spotify_api.py` - Tests for Spotify API integration
- `test_database.py` - Tests for database interactions and edge cases
- `conftest.py` - Shared pytest fixtures and configuration

### Coverage Areas

- **Authentication**: JWT token creation, Spotify OAuth flow, token refresh
- **Database Models**: User, ListeningHistory, AudioFeatures, TopArtist, TopTrack
- **Insights Generation**: Basic and detailed analytics from listening data
- **Spotify API**: User profile retrieval, API request handling, error management
- **FastAPI Endpoints**: HTTP response validation
- **Database Integrity**: Constraints, relationships, edge cases
- **Error Handling**: HTTP errors, database errors, empty data scenarios

## Running Tests

### Prerequisites

```bash
pip install -r app/requirements.txt
```

### Run All Tests

```bash
PYTHONPATH=. pytest tests/ -v
```

### Run Specific Test Files

```bash
PYTHONPATH=. pytest tests/test_insights.py -v
PYTHONPATH=. pytest tests/test_auth.py -v
```

### Run Tests with Coverage

```bash
PYTHONPATH=. pytest tests/ --cov=app --cov-report=html
```

### Run Tests with Different Output Formats

```bash
# Short traceback format
PYTHONPATH=. pytest tests/ --tb=short

# Disable warnings
PYTHONPATH=. pytest tests/ --disable-warnings

# Stop after first failure
PYTHONPATH=. pytest tests/ -x
```

## Test Features

### Fixtures

- `db_session` - Database session with automatic rollback
- `test_user` - Sample user for testing
- `insights_generator` - Insights generator instance
- `spotify_api` - Spotify API instance with mocked responses
- `sample_listening_data` - Sample listening history data

### Mocking

- External API calls (Spotify Web API, requests)
- Database operations for isolated testing
- Token expiration scenarios

### Edge Cases Tested

- Empty datasets
- Large datasets (100+ records)
- Invalid input data
- Database constraint violations
- Token expiration handling
- HTTP error responses
- Extreme audio feature values

## Test Results

Current test suite: **30 tests, all passing**

### Test Coverage by Module

- Authentication: 6 tests
- Database operations: 6 tests
- Insights generation: 6 tests
- FastAPI endpoints: 1 test
- Database models: 6 tests
- Spotify API: 5 tests

### Key Testing Patterns

1. **Arrange-Act-Assert**: Clear test structure
2. **Isolation**: Each test uses fresh database session
3. **Mocking**: External dependencies mocked for reliability
4. **Edge Cases**: Comprehensive boundary testing
5. **Type Safety**: Proper type hints throughout

## Development Guidelines

### Adding New Tests

1. Follow existing naming conventions (`test_feature_scenario`)
2. Use appropriate fixtures for setup
3. Mock external dependencies
4. Test both success and failure scenarios
5. Include docstrings explaining test purpose

### Test Data

- Use realistic but minimal test data
- Leverage fixtures for reusable test objects
- Clean up test data automatically with fixtures

### Maintenance

- Keep tests updated with code changes
- Review and update mocks when external APIs change
- Monitor test performance and optimize slow tests
