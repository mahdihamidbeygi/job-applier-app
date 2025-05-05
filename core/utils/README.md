# Core Utilities

This directory contains utility modules that provide reusable functionality across the application.

## Available Utilities

### Database Utilities (`db_utils.py`)

Safe database operations with error handling:

- `safe_get_or_none(model_class, **kwargs)`: Safely get a model instance or return None
- `safe_create(model_class, **kwargs)`: Safely create a model instance
- `safe_update(instance, **kwargs)`: Safely update a model instance
- `safe_delete(instance)`: Safely delete a model instance
- `safe_filter(model_class, **kwargs)`: Safely filter model instances
- `safe_bulk_create(model_class, objects_list)`: Safely bulk create model instances

Example usage:
```python
from core.utils.db_utils import safe_get_or_none, safe_update

# Safely get a user profile or return None
profile = safe_get_or_none(UserProfile, user=request.user)

# Safely update an object, handling exceptions
updated_profile, success = safe_update(profile, name="John Doe", title="Developer")
```

### Logging Utilities (`logging_utils.py`)

Enhanced logging functionality:

- `get_logger(name)`: Get a logger with the specified name
- `log_execution_time(logger=None)`: Decorator to log function execution time
- `log_exceptions(logger=None, level=logging.ERROR, reraise=True)`: Decorator to log exceptions
- `LoggerAdapter`: Logger adapter that prepends a context prefix to log messages
- `get_prefixed_logger(name, prefix)`: Get a logger with a prefix for all messages

Example usage:
```python
from core.utils.logging_utils import get_logger, log_execution_time, log_exceptions

# Get a logger
logger = get_logger(__name__)

# Log execution time
@log_execution_time()
def some_function():
    # Function code here
    pass

# Log exceptions
@log_exceptions(level=logging.WARNING, reraise=False)
def risky_function():
    # Function code that might raise exceptions
    pass
```

### Import Utilities (`profile_importers.py`)

Utilities for importing profile data from external sources:

- `GitHubProfileImporter`: Import profile data from GitHub
- `ResumeImporter`: Import data from resumes
- `LinkedInImporter`: Import data from LinkedIn profiles

## Best Practices

1. **Error Handling**: Always use `try/except` blocks to handle exceptions in utility functions
2. **Logging**: Use the logging utilities to log errors and debug information
3. **Type Annotations**: Add type hints to functions and methods for better code clarity
4. **Documentation**: Document utility functions with docstrings that include parameters and return values
5. **Testing**: Write unit tests for utility functions to ensure they work as expected 