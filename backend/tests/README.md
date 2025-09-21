# Comprehensive Test Suite Documentation

This document provides detailed information about the test suite for the Artisan Promotion Platform backend.

## Test Structure

The test suite is organized into several categories:

### 1. Unit Tests (`@pytest.mark.unit`)
- **Purpose**: Test individual functions, methods, and classes in isolation
- **Location**: `test_*_unit.py` files and tests marked with `@pytest.mark.unit`
- **Coverage**: All service classes, utilities, and business logic
- **Mocking**: Heavy use of mocks to isolate units under test

### 2. Integration Tests (`@pytest.mark.integration`)
- **Purpose**: Test interactions between components
- **Location**: `test_integration_*.py` files and tests marked with `@pytest.mark.integration`
- **Coverage**: API endpoints, database operations, service interactions
- **Database**: Uses test database with real database operations

### 3. End-to-End Tests (`@pytest.mark.e2e`)
- **Purpose**: Test complete user workflows
- **Location**: `test_e2e_*.py` files and tests marked with `@pytest.mark.e2e`
- **Coverage**: Complete user journeys from registration to analytics
- **Environment**: Full application stack with mocked external services

### 4. Performance Tests (`@pytest.mark.performance`)
- **Purpose**: Test system performance and resource usage
- **Location**: `test_performance.py` and tests marked with `@pytest.mark.performance`
- **Coverage**: Image processing, concurrent operations, large datasets
- **Metrics**: Response times, memory usage, throughput

### 5. Security Tests (`@pytest.mark.security`)
- **Purpose**: Test security measures and vulnerability prevention
- **Location**: `test_security.py` and tests marked with `@pytest.mark.security`
- **Coverage**: Authentication, authorization, input validation, rate limiting
- **Tools**: Custom security test utilities

## Running Tests

### Prerequisites
```bash
cd backend
pip install -r requirements.txt
```

### Run All Tests
```bash
python -m pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
python -m pytest -m unit

# Integration tests only
python -m pytest -m integration

# E2E tests only
python -m pytest -m e2e

# Performance tests only
python -m pytest -m performance

# Security tests only
python -m pytest -m security
```

### Run Tests with Coverage
```bash
python -m pytest --cov=app --cov-report=html --cov-report=term-missing
```

### Run Tests for Specific Platform
```bash
# Facebook platform tests
python -m pytest -m facebook

# All platform tests
python -m pytest -m platform
```

### Using the Test Suite Runner
```bash
# Run comprehensive test suite
python tests/test_suite_runner.py all

# Run specific category
python tests/test_suite_runner.py unit
python tests/test_suite_runner.py integration
python tests/test_suite_runner.py e2e
python tests/test_suite_runner.py performance
python tests/test_suite_runner.py security

# Run quick tests for development
python tests/test_suite_runner.py quick

# Run CI-optimized tests
python tests/test_suite_runner.py ci
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings
- Markers for test categorization
- Warning filters
- Async test support

### Test Markers
- `unit`: Unit tests
- `integration`: Integration tests
- `e2e`: End-to-end tests
- `performance`: Performance tests
- `security`: Security tests
- `slow`: Slow-running tests
- `external`: Tests requiring external services
- Platform-specific markers: `facebook`, `instagram`, `etsy`, etc.

## Test Fixtures

### Database Fixtures
- `db_session`: Fresh database session for each test
- `client`: FastAPI test client with database override

### Authentication Fixtures
- `sample_user_data`: Standard user data for testing
- `authenticated_client`: Pre-authenticated test client

### Mock Fixtures
- External API mocks (Gemini, platform APIs)
- Storage service mocks
- Email service mocks

## Coverage Requirements

### Minimum Coverage Thresholds
- **Overall**: 80%
- **Services**: 85%
- **Utilities**: 90%
- **Critical paths**: 95%

### Coverage Reports
- Terminal output with missing lines
- HTML report in `htmlcov/`
- XML report for CI/CD integration

## Best Practices

### Writing Unit Tests
1. **Isolation**: Mock all external dependencies
2. **Clarity**: Use descriptive test names
3. **Completeness**: Test happy path, edge cases, and error conditions
4. **Speed**: Keep tests fast by avoiding I/O operations

### Writing Integration Tests
1. **Real Dependencies**: Use real database, avoid mocking internal services
2. **Data Cleanup**: Ensure tests clean up after themselves
3. **Realistic Scenarios**: Test realistic user interactions
4. **Error Handling**: Test error conditions and recovery

### Writing E2E Tests
1. **User Perspective**: Test from user's point of view
2. **Complete Workflows**: Test entire user journeys
3. **External Mocking**: Mock external APIs but use real internal services
4. **Stability**: Make tests resilient to timing issues

### Writing Performance Tests
1. **Baseline Metrics**: Establish performance baselines
2. **Realistic Load**: Use realistic data volumes and concurrency
3. **Resource Monitoring**: Monitor memory, CPU, and I/O usage
4. **Regression Detection**: Fail tests if performance degrades significantly

## Continuous Integration

### GitHub Actions Workflow
- Parallel test execution for faster feedback
- Separate jobs for different test categories
- Coverage reporting to Codecov
- Artifact collection for test reports
- Performance benchmarking

### Test Environments
- **Development**: Local testing with SQLite
- **CI**: PostgreSQL and Redis services
- **Staging**: Full environment with external service mocks
- **Production**: Monitoring and health checks only

## Debugging Tests

### Common Issues
1. **Async Test Failures**: Ensure proper async/await usage
2. **Database State**: Check for test isolation issues
3. **Mock Configuration**: Verify mock setup and assertions
4. **Timing Issues**: Use proper waiting mechanisms

### Debugging Tools
```bash
# Run with verbose output
python -m pytest -v

# Run with debugging
python -m pytest --pdb

# Run specific test with output
python -m pytest tests/test_specific.py::TestClass::test_method -s

# Run with coverage and show missing lines
python -m pytest --cov=app --cov-report=term-missing
```

## Test Data Management

### Test Database
- Isolated test database for each test run
- Automatic schema creation and cleanup
- Transaction rollback for test isolation

### Test Data Factories
- User factory for creating test users
- Product factory for creating test products
- Post factory for creating test posts
- Configurable data generation

### External Service Mocking
- Comprehensive mocks for all external APIs
- Realistic response simulation
- Error condition simulation
- Rate limiting simulation

## Performance Monitoring

### Metrics Tracked
- Test execution time
- Memory usage during tests
- Database query performance
- API response times
- Image processing performance

### Performance Regression Detection
- Baseline performance metrics
- Automated performance comparison
- Alerts for significant degradation
- Performance trend analysis

## Security Testing

### Security Test Categories
1. **Authentication**: Login, logout, token validation
2. **Authorization**: Access control, permission checks
3. **Input Validation**: SQL injection, XSS prevention
4. **Rate Limiting**: Brute force protection
5. **Data Protection**: Encryption, secure storage

### Security Tools Integration
- Bandit for static security analysis
- Safety for dependency vulnerability scanning
- Custom security test utilities
- Penetration testing simulation

## Maintenance

### Regular Tasks
1. **Update Dependencies**: Keep test dependencies current
2. **Review Coverage**: Ensure coverage remains high
3. **Performance Baselines**: Update performance expectations
4. **Test Data**: Refresh test data sets
5. **Documentation**: Keep test documentation current

### Test Health Monitoring
- Track test execution times
- Monitor test failure rates
- Identify flaky tests
- Optimize slow tests

## Contributing

### Adding New Tests
1. Choose appropriate test category
2. Use existing fixtures and utilities
3. Follow naming conventions
4. Add appropriate markers
5. Update documentation

### Test Review Checklist
- [ ] Tests cover happy path and edge cases
- [ ] Appropriate mocking strategy
- [ ] Clear and descriptive test names
- [ ] Proper cleanup and isolation
- [ ] Performance considerations
- [ ] Security implications considered

## Resources

### Documentation
- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites)

### Tools
- pytest: Test framework
- pytest-asyncio: Async test support
- pytest-cov: Coverage reporting
- pytest-mock: Mocking utilities
- pytest-xdist: Parallel test execution