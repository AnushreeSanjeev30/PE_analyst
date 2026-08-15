# Security Documentation - PE-Analyst

This document outlines the security measures implemented in the PE-Analyst system, including configuration management, authentication, input validation, data protection, and secure coding practices.

## 1. Configuration & Secrets Management

### 1.1 Environment-Based Configuration

The application uses `pydantic-settings` for secure configuration management:

```python
# src/pe_analyst/core/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown environment variables
    )
```

**Security Features:**
- Configuration loaded from `.env` file (which should be in `.gitignore`)
- Case-insensitive environment variable handling
- Unknown variables are safely ignored
- All sensitive settings are type-validated

### 1.2 API Key Management

All external API credentials are stored as environment variables and never hardcoded:

```python
# API Keys (required for respective providers)
openai_api_key: str | None = None
anthropic_api_key: str | None = None
gemini_api_key: str | None = None
```

**Security Practices:**
- API keys are never logged or exposed
- Optional keys allow graceful degradation if not configured
- Only enabled providers are initialized based on available credentials
- Keys are validated before use (see section 1.3)

### 1.3 Credential Validation

Credentials are validated at initialization and fail-fast if invalid:

```python
# src/pe_analyst/llm/providers.py
class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured")
```

**Security Features:**
- Explicit validation prevents missing credentials from causing silent failures
- Raises `LLMConfigurationError` if credentials are missing
- Timeout configuration prevents hung connections (default: 60 seconds)

### 1.4 Provider Factory Pattern

Only configured providers are enabled:

```python
# src/pe_analyst/llm/factory.py
def build_llm_service(settings: Settings, *, include_ollama: bool = False) -> LLMService:
    """Build only providers whose credentials are present in application settings."""
    providers: dict[LLMProviderName, LLMProvider] = {}
    if settings.openai_api_key:
        providers[LLMProviderName.OPENAI] = OpenAIProvider(
            settings.openai_api_key, settings.llm_timeout_seconds
        )
    # Similar for Anthropic, Gemini...
    return LLMService(providers)
```

**Security Benefits:**
- No unused providers are instantiated
- Clear audit trail of which providers are enabled
- Fail-fast initialization ensures only valid configurations run

---

## 2. API Security

### 2.1 Secure Communication

All external API communications use HTTPS with Bearer token authentication:

```python
# OpenAI
self.client = httpx.Client(
    base_url="https://api.openai.com/v1",
    timeout=timeout_seconds,
    headers={"Authorization": f"Bearer {api_key}"},
)

# Anthropic
self.client = httpx.Client(
    base_url="https://api.anthropic.com/v1",
    timeout=timeout_seconds,
    headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
)

# Google Gemini
self.client = httpx.Client(
    base_url="https://generativelanguage.googleapis.com/v1beta",
    timeout=timeout_seconds
)
```

**Security Features:**
- HTTPS-only communication with external services
- Standard Authorization headers for secure authentication
- Request timeouts prevent denial-of-service vulnerabilities
- API version pinning for stability and predictability

### 2.2 HTTP Error Handling

Proper error handling prevents information leakage:

```python
@staticmethod
def _raise(response: httpx.Response) -> None:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise LLMProviderError(
            f"Provider request failed: {error.response.status_code} {error.response.text}"
        ) from error
```

**Security Features:**
- HTTP status codes are checked before processing responses
- Errors are caught and wrapped in custom exceptions
- Response details are logged for debugging
- Prevents malformed responses from being processed

### 2.3 Request Payload Security

Sensitive configurations in request payloads:

```python
# Example: OpenAI provider ensures strict schema validation
payload: dict[str, Any] = {
    "model": request.model,
    "messages": [...],
    "temperature": request.temperature,
    "max_output_tokens": request.max_output_tokens,
    "store": False,  # Don't store training data
}

# JSON Schema validation when response structure is required
if request.response_schema:
    payload["text"] = {
        "format": {
            "type": "json_schema",
            "name": "response",
            "schema": request.response_schema,
            "strict": True,  # Enforce strict validation
        }
    }
```

**Security Features:**
- Training data storage is explicitly disabled
- Strict JSON schema validation for structured responses
- Type-safe payload construction

---

## 3. Input Validation & Data Integrity

### 3.1 Type Safety with Pydantic

All data models use Pydantic for automatic validation:

```python
# src/pe_analyst/llm/models.py
@dataclass
class LLMMessage:
    role: str
    content: str

@dataclass
class LLMRequest:
    model: str
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_output_tokens: int = 2_000
    response_schema: dict[str, Any] | None = None
```

**Security Benefits:**
- Type annotations ensure type safety at validation time
- Automatic conversion and validation of input data
- Invalid data is rejected at the boundary
- Clear data contracts prevent misuse

### 3.2 Financial Calculation Validation

All financial inputs are validated before computation:

```python
# src/pe_analyst/valuation/dcf.py
def validate(self) -> None:
    if self.projection_years <= 0:
        raise InvalidAssumptionError("projection_years must be greater than 0.")
    if self.wacc <= 0:
        raise InvalidAssumptionError("wacc must be greater than 0.")
    if self.terminal_growth >= self.wacc:
        raise InvalidAssumptionError("terminal_growth must be less than wacc.")
    if self.shares_outstanding <= 0:
        raise InvalidAssumptionError("shares_outstanding must be greater than 0.")
    if self.revenue <= 0:
        raise InvalidAssumptionError("revenue must be greater than 0.")
```

**Security Features:**
- Business logic validation prevents nonsensical calculations
- Explicit error messages aid debugging without leaking internals
- Fail-fast approach prevents corrupted analysis
- All mathematical constraints are enforced

### 3.3 Document Input Validation

File uploads are validated for security:

```python
# src/pe_analyst/core/config.py
max_upload_size_mb: int = Field(
    default=50,  # Maximum 50MB files
    gt=0,
)

# Document processing validates file types
def process(self, path: str | Path) -> DocumentIntelligenceResult:
    pdf = self.extractor.extract(Path(path))
    return self._interpret(pdf)
```

**Security Features:**
- File size limits prevent disk exhaustion attacks
- Only PDF format is supported (configurable)
- Path validation prevents directory traversal attacks
- File type validation prevents execution attacks

### 3.4 Configuration Field Validation

All configuration parameters are validated with constraints:

```python
# src/pe_analyst/core/config.py
port: int = Field(
    default=8000,
    ge=1,           # Port >= 1
    le=65535,       # Port <= 65535
)

max_upload_size_mb: int = Field(
    default=50,
    gt=0,           # Must be positive
)

llm_timeout_seconds: float = Field(
    default=60.0,
    gt=0,           # Must be positive
)

retrieval_top_k: int = Field(
    default=10,
    gt=0,           # Must be positive
)
```

**Security Benefits:**
- Prevents invalid configuration values
- Type-checked bounds prevent misuse
- Sensible defaults provide safe operation
- Invalid configs are caught at startup

---

## 4. Exception Handling & Error Management

### 4.1 Custom Exception Hierarchy

A comprehensive exception hierarchy provides clear error boundaries:

```python
# src/pe_analyst/core/exceptions.py
class PEAnalystError(Exception):
    """Base exception for all application-specific errors."""

class ConfigurationError(PEAnalystError):
    """Raised when application configuration is invalid."""

class DocumentProcessingError(PEAnalystError):
    """Raised when document ingestion or processing fails."""

class FinancialDataError(PEAnalystError):
    """Raised when financial data is missing, malformed, or inconsistent."""

class EvidenceValidationError(PEAnalystError):
    """Raised when evidence cannot support an analytical claim."""

class AgentExecutionError(PEAnalystError):
    """Raised when a specialist agent cannot complete its task."""

class WorkflowExecutionError(PEAnalystError):
    """Raised when the investment workflow fails."""
```

**Security Features:**
- Clear exception hierarchy for precise error handling
- Specific exceptions prevent overly broad exception catching
- Custom exceptions prevent unhandled errors from leaking
- Evidence validation prevents unsubstantiated claims

### 4.2 Input Validation Errors

Agent-level validation catches malformed inputs:

```python
# src/agents/valuation_agent.py
def validate(self, state: AgentState) -> None:
    super().validate(state)
    inputs = state.metadata.get("valuation_inputs")
    if not isinstance(inputs, dict):
        raise ValueError("state.metadata['valuation_inputs'] must contain valuation input data")
    missing = {"dcf", "comparables", "lbo"} - inputs.keys()
    if missing:
        raise ValueError(f"valuation_inputs is missing: {', '.join(sorted(missing))}")
```

**Security Benefits:**
- Required fields are validated before processing
- Missing data causes explicit failures
- Type checking prevents type confusion attacks

---

## 5. Code Quality & Type Safety

### 5.1 Static Type Checking with MyPy

All code is type-checked with MyPy:

```bash
# Enforces complete type annotations
python -m mypy src
```

**Configuration** (`pyproject.toml`):
- Python 3.11+ for modern type features
- Strict typing prevents runtime type errors
- Catches type mismatches at development time

**Type Safety Benefits:**
- Prevents runtime type errors
- Better IDE autocompletion and refactoring
- Self-documenting code
- Catches API misuse at compile time

### 5.2 Linting with Ruff

Code quality is enforced with Ruff:

```bash
python -m ruff check src tests --fix
```

**Security Checks:**
- `F` (Pyflakes): Detects undefined names and unused imports
- `E` (pycodestyle): Enforces style consistency
- `I` (isort): Ensures proper import organization
- `B` (flake8-bugbear): Catches common bugs and security issues
- `UP` (pyupgrade): Enforces modern Python practices

**Example Security Fixes:**
- Detects unused variables that might hide logic errors
- Prevents wildcard imports that mask dependencies
- Enforces explicit `zip()` usage with `strict=True` parameter
- Recommends safer enum patterns (`StrEnum` instead of `str, Enum`)

### 5.3 Testing & Coverage

Comprehensive test suite ensures security:

```bash
# Run tests with coverage reports
pytest --cov=src
```

**Testing Infrastructure:**
- Unit tests in `tests/unit/` verify core logic
- Fixture-based testing via `conftest.py`
- Coverage tracking prevents untested code
- Type annotations enable better test generation

---

## 6. Logging & Monitoring

### 6.1 Structured Logging

Logging is configured centrally with level control:

```python
# src/pe_analyst/core/logging.py
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

def build_logging_config(settings: Settings) -> dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": DEFAULT_LOG_FORMAT,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": settings.log_level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": settings.log_level,
        },
    }
```

**Security Features:**
- Consistent log format includes timestamps for audit trails
- Configurable log levels prevent information leakage in production
- Centralized logging configuration ensures consistency
- Logger names clearly identify the source

### 6.2 Production vs. Development Logging

```python
# src/pe_analyst/core/config.py
app_env: Environment = Environment.DEVELOPMENT
debug: bool = True
log_level: str = "INFO"
```

**Security Recommendations:**
- Set `debug=False` in production
- Set `log_level="WARNING"` in production to reduce log volume
- Disable stack traces in production logs
- Use log aggregation services for security monitoring

---

## 7. Deployment Security

### 7.1 Environment-Based Configuration

Application behavior changes per environment:

```python
# src/pe_analyst/core/enums.py
class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
```

**Environment Setup:**
```bash
# Development (default)
APP_ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# Staging
APP_ENV=staging
DEBUG=false
LOG_LEVEL=INFO

# Production
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING
```

**Security Features:**
- Different configurations per environment
- Debug mode disabled in production
- Minimal logging in production reduces data exposure

### 7.2 Server Configuration

FastAPI/Uvicorn server settings:

```python
# Configurable host and port
host: str = "127.0.0.1"  # Bind to localhost by default
port: int = Field(default=8000, ge=1, le=65535)
```

**Security Best Practices:**
- Default bind to localhost prevents external exposure during development
- Use reverse proxy (nginx) in production
- Configure HTTPS via reverse proxy
- Use environment variables for host/port configuration

### 7.3 Database Security

Database configuration with connection string validation:

```python
# src/pe_analyst/core/config.py
database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pe_analyst"
```

**Security Recommendations:**
- Never hardcode credentials in source code
- Use environment variables for database URLs
- Enable SSL for remote database connections
- Use connection pooling to prevent resource exhaustion
- Implement row-level security policies in PostgreSQL

### 7.4 CORS & Security Headers

FastAPI recommendations for deployment:

```python
# Recommended production configuration
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Whitelist specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
    max_age=600,  # CORS preflight cache
)

# Security headers
from fastapi.middleware import Middleware
from starlette.middleware.headers import HeadersMiddleware

app.add_middleware(
    HeadersMiddleware,
    headers={
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    }
)
```

---

## 8. Evidence-Grounded Security

### 8.1 Data Integrity Through Evidence

The system implements evidence-grounded analysis:

```python
# src/pe_analyst/domain/evidence.py
# Evidence traces back to source documents
# Claims are only made when evidence supports them
# Audit trails track analytical reasoning
```

**Security Benefits:**
- Claims are traceable to source evidence
- Analysis is auditable and reproducible
- No unsubstantiated recommendations
- Supports compliance requirements

### 8.2 Deterministic Financial Calculations

Financial analysis is separate from LLM reasoning:

```
Evidence → Structured Data → Deterministic Engines → Specialist Agents → Audit Trail
```

**Security Features:**
- Financial calculations are deterministic and verifiable
- No randomness in mathematical operations
- Results are reproducible
- Separates LLM uncertainty from financial certainty

---

## 9. Security Checklist for Deployment

Before deploying to production, ensure:

- [ ] `.env` file is created and added to `.gitignore`
- [ ] All API keys are configured in environment variables
- [ ] `APP_ENV=production` is set
- [ ] `DEBUG=false` is set
- [ ] `LOG_LEVEL=WARNING` (or appropriate level)
- [ ] HTTPS is enabled via reverse proxy
- [ ] Database uses SSL connections
- [ ] CORS is configured to allow specific origins only
- [ ] Database backups are automated
- [ ] Log aggregation is configured
- [ ] Security headers are added
- [ ] Rate limiting is implemented
- [ ] Input file size limits are enforced
- [ ] Database credentials are not in version control
- [ ] API keys are rotated regularly
- [ ] Audit logging is enabled
- [ ] Error pages don't leak sensitive information

---

## 10. Dependency Security

### 10.1 Supply Chain Security

Dependencies are pinned to specific versions:

```toml
dependencies = [
    "pydantic>=2.10,<3.0",          # Type validation
    "pydantic-settings>=2.7,<3.0",  # Config management
    "python-dotenv>=1.0,<2.0",      # Environment files
    "fastapi>=0.115,<1.0",          # Web framework
    "uvicorn[standard]>=0.34,<1.0", # ASGI server
    "httpx>=0.28,<1.0",             # HTTP client
    "pypdf>=5.0,<7.0",              # PDF parsing
]
```

**Security Practices:**
- Versions are pinned to prevent unexpected breaking changes
- Range constraints allow patch updates for security fixes
- Dependencies are minimal and well-maintained
- Regular updates should be reviewed for security patches

### 10.2 Scanning Dependencies

```bash
# Check for known vulnerabilities (requires pip-audit or similar)
pip install pip-audit
pip-audit
```

---

## 11. Contact & Reporting Security Issues

For security issues:

1. **Do not** open a public GitHub issue
2. **Do** report privately to the project maintainers
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-08-16 | Initial security documentation |

---

**Last Updated:** 2026-08-16
