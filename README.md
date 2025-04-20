# goit-pythonweb-hw-12

# FastAPI Contacts Management Application

REST API application for managing contacts with FastAPI framework.

## Technologies

- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Poetry (dependency management)
- Docker & Docker Compose
- Cloudinary (avatar storage)

## Features

- User registration, login, email verification
- Rate limiting for sensitive endpoints (register, me)
- Avatar upload and storage via Cloudinary (with avatar_url field)
- CRUD operations for contacts
- Search contacts by name, surname, or email
- Get contacts with upcoming birthdays (next 7 days)
- Data validation using Pydantic
- Interactive API documentation (Swagger UI)
- Alternative API documentation (ReDoc)

## Prerequisites

- Python 3.12 or higher
- Poetry
- Docker and Docker Compose

## Installation

1. Clone the repository:

```bash
git clone https://github.com/sandrey88/goit-pythonweb-hw-12.git
cd goit-pythonweb-hw-12
```

2. Copy environment variables:

```bash
cp .env.example .env
```

Then edit `.env` with your settings.

3. Install dependencies with Poetry:

```bash
poetry install
```

## Environment Variables

The application uses a `.env` file for configuration. Example:

```env
DATABASE_URL=postgresql://user:password@db:5432/contacts_db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=contacts_db
CLOUDINARY_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
MAIL_USERNAME=your_email@example.com
MAIL_PASSWORD=your_password
MAIL_FROM=your_email@example.com
MAIL_PORT=465
MAIL_SERVER=smtp.example.com
MAIL_STARTTLS=False
MAIL_SSL_TLS=True
SECRET_KEY=your_secret_key
```

## Running the Application

### Using Docker (recommended):

```bash
docker-compose up --build
```

The application will be available at http://localhost:8000

### Using Poetry (local development):

1. Start PostgreSQL (make sure it's running locally)

2. Create a `.env` file in the root directory with the following content:

```env
DATABASE_URL=postgresql://YOUR_USERNAME@localhost:5432/contacts_db
POSTGRES_USER=YOUR_USERNAME
POSTGRES_PASSWORD=YOUR_PASSWORD
POSTGRES_DB=contacts_db
```

Replace `YOUR_USERNAME` and `YOUR_PASSWORD` with your PostgreSQL credentials.

3. Create the database:

```bash
createdb contacts_db
```

4. Activate the virtual environment:

```bash
poetry shell
```

5. Install dependencies:

```bash
poetry install
```

6. Run the application:

```bash
poetry run uvicorn src.main:app --reload
```

## API Endpoints

### Authentication

- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token
- `GET /auth/verify-email?token=...` - Verify email address
- `GET /auth/me` - Get current user info (JWT required)
- `PATCH /auth/avatar` - Upload or update user avatar (JWT required, file upload)

### Contacts Management

- `GET /contacts` - Get list of all contacts
- `POST /contacts` - Create a new contact
- `GET /contacts/{contact_id}` - Get a specific contact by ID
- `PUT /contacts/{contact_id}` - Update an existing contact
- `DELETE /contacts/{contact_id}` - Delete a contact

### Search and Filtering

- `GET /contacts/find?q={query}` - Search contacts by name, surname, or email
- `GET /contacts/birthdays/next7days` - Get contacts with birthdays in the next 7 days

## Rate Limiting

Sensitive endpoints (`/auth/register`, `/auth/me`) are protected by rate limiting (5 requests per minute per IP) to prevent abuse. If the limit is exceeded, a 429 error is returned.

## Avatar Upload (Cloudinary)

- Users can upload an avatar via the `/auth/avatar` endpoint using a file upload (image).
- Images are stored in Cloudinary, and the returned `avatar_url` field contains the public URL.
- Cloudinary credentials must be set in the `.env` file.

## Data Validation

The API implements strict data validation:

- `first_name` and `last_name`: 2-50 characters
- `email`: Must be a valid email address
- `phone`: 10-20 characters
- `birthday`: Valid date in YYYY-MM-DD format
- `additional_data`: Optional field

Example of valid contact data:

```json
{
  "first_name": "Іван",
  "last_name": "Петренко",
  "email": "ivan@example.com",
  "phone": "0501234567",
  "birthday": "1990-01-15",
  "additional_data": "Додаткова інформація"
}
```

## API Documentation

Once the application is running, you can access:

- Swagger UI documentation at http://localhost:8000/docs
- ReDoc documentation at http://localhost:8000/redoc

## Test Coverage & Testing

### Coverage Requirements

- The project requires **at least 75% code coverage**. This is a combined requirement for all tests (unit + integration).
- You do **not** need to have 75% separately for unit and integration tests. The total coverage is calculated across all tests using `pytest-cov`.

### How to Check Coverage

To run **all tests** (unit and integration) and check coverage:

```bash
poetry run pytest --cov=src --cov-report=term-missing
```

- This will show the total coverage percentage and highlight any lines not covered by tests.
- Aim for at least 75% total coverage.

### Running Only Unit or Integration Tests

- **Unit tests:**
  ```bash
  poetry run pytest tests/repository/ --cov=src --cov-report=term-missing
  ```
- **Integration tests:**
  ```bash
  poetry run pytest tests/integration/ --cov=src --cov-report=term-missing
  ```
- For official coverage, always run all tests together.

### Integration Tests

- Integration tests are located in `tests/integration/`.
- They use a separate SQLite database and mock all external email sending.
- **No real emails are sent** during integration testing.
- Test environment variables are set at the top of each integration test file.
- To run only integration tests:
  ```bash
  poetry run pytest tests/integration/
  ```

### Known Test Warnings

When running tests, you may see warnings such as:

- SQLAlchemy `MovedIn20Warning` about `declarative_base()`
- SQLAlchemy `DeprecationWarning: datetime.datetime.utcnow() is deprecated...`
- Pydantic `PydanticDeprecatedSince20` about class-based `Config`
- Pydantic `PydanticDeprecatedSince20: The dict method is deprecated; use model_dump instead`
- passlib `DeprecationWarning: 'crypt' is deprecated and slated for removal in Python 3.13`

**These warnings do NOT affect test correctness or application logic.**

- All tests pass and the application works as expected.
- Warnings will be addressed in future updates as the codebase is refactored for full compatibility with the newest versions of dependencies.

## Documentation

Comprehensive documentation is generated using [Sphinx](https://www.sphinx-doc.org/).

- All main modules and functions are documented with English docstrings.
- To build the documentation locally, run:

  ```bash
  poetry run make -C docs html
  ```

- The generated HTML documentation will be available in `docs/build/html/index.html`.

> **Note:** Only the Sphinx source files are included in the repository. The generated HTML files are not tracked by git.

> **Note:** When building the documentation, you may see several WARNING messages (e.g., about duplicate object descriptions). These are expected due to how Sphinx processes class attributes and docstrings in SQLAlchemy and Pydantic models. They do not affect the quality or completeness of the generated documentation and can be safely ignored.

## Error Handling

- 404: Contact not found
- 409: User already exists or duplicate email
- 401: Invalid credentials
- 403: Email not verified
- 429: Too many requests (rate limit exceeded)
- 422: Validation error (invalid data format)
- 500: Internal server error
