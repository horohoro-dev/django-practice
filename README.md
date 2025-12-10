# Django Practice - Bookstore Inventory Management

Django practice project for managing bookstore inventory.

## Tech Stack

- **Python**: 3.13
- **Framework**: Django 5.x
- **Package Manager**: uv
- **Formatter/Linter**: ruff

## Setup

```bash
# Install dependencies
uv sync

# Run migrations
uv run manage.py migrate

# Start development server
uv run manage.py runserver
```

## Project Structure

```
backend/
├── config/          # Django project settings
├── inventory/       # Inventory management app
│   ├── models.py    # Data models
│   ├── views.py     # API views
│   ├── serializers.py
│   └── management/  # Custom management commands
└── docs/            # Documentation
```

## Models

- **Genre**: Book genres/categories
- **Book**: Book information (ISBN, title, author, publisher, price)
- **Inventory**: Stock quantity per book
- **InventoryTransaction**: Stock movement history (arrival, sale, loss, theft)
- **Sale**: Sales records

## Management Commands

### Generate ER Diagram

Generate Mermaid ER diagram from Django models:

```bash
# Default (data app)
uv run manage.py generate_er_diagram

# Specify app
uv run manage.py generate_er_diagram -a inventory

# Specify output file
uv run manage.py generate_er_diagram -a inventory -o docs/er-diagram.md
```

Options:
- `-a, --app`: App label to generate diagram for (default: `data`)
- `-o, --output`: Output file path (default: `docs/er-diagram.md`)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/genres/` | List all genres |
| POST | `/api/genres/` | Create a genre |
| GET | `/api/books/` | List all books |
| POST | `/api/books/` | Create a book |
| GET | `/api/books/{id}/` | Get book details |
| PUT | `/api/books/{id}/` | Update a book |
| DELETE | `/api/books/{id}/` | Delete a book |
| GET | `/api/inventory/` | List all inventory |
| POST | `/api/inventory/transactions/` | Record inventory transaction |
| GET | `/api/sales/` | List all sales |
| POST | `/api/sales/` | Record a sale |

## Testing

```bash
# Run all tests
uv run manage.py test

# Run specific app tests
uv run manage.py test inventory
```

## Documentation

- [ER Diagram](backend/docs/er-diagram.md)
