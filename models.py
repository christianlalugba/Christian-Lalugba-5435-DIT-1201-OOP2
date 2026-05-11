"""
models.py — Pydantic Data Models
=================================
Defines all request bodies, response schemas, and shared data models
used throughout the Limkokwing University Library Management System API.

All models enforce strict type validation via Pydantic v2.
"""

from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional, Any


# ---------------------------------------------------------------------------
# Core Domain Model
# ---------------------------------------------------------------------------


class Book(BaseModel):
    """
    Represents a single book in the library catalogue.

    Attributes:
        id          (int):            Unique identifier for the book.
        title       (str):            Full title of the book.
        author      (str):            Author's full name.
        category    (str):            Genre or subject category.
        isbn        (str):            International Standard Book Number.
        year        (int):            Year of publication.
        is_borrowed (bool):           Whether the book is currently on loan.
        borrowed_by (str | None):     Student ID of the current borrower, if any.
        borrowed_on (str | None):     ISO date string of when the book was borrowed.
        due_date    (str | None):     ISO date string of the return deadline.
    """

    id: int = Field(..., description="Unique book identifier", example=1)
    title: str = Field(..., description="Book title", example="Clean Code")
    author: str = Field(..., description="Author full name", example="Robert C. Martin")
    category: str = Field(..., description="Genre or subject", example="Computer Science")
    isbn: str = Field(..., description="ISBN number", example="978-0132350884")
    year: int = Field(..., description="Publication year", example=2008)
    is_borrowed: bool = Field(False, description="Whether the book is borrowed")
    borrowed_by: Optional[str] = Field(None, description="Student ID of borrower")
    borrowed_on: Optional[str] = Field(None, description="Date borrowed (ISO 8601)")
    due_date: Optional[str] = Field(None, description="Return due date (ISO 8601)")

    model_config = {"json_schema_extra": {"example": {
        "id": 1,
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "category": "Computer Science",
        "isbn": "978-0132350884",
        "year": 2008,
        "is_borrowed": False,
        "borrowed_by": None,
        "borrowed_on": None,
        "due_date": None,
    }}}


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------


class BorrowRequest(BaseModel):
    """
    Request body for borrowing a book (POST /borrow).

    Attributes:
        book_id    (int): The ID of the book to borrow.
        student_id (str): The ID of the student requesting the book.
    """

    book_id: int = Field(..., description="ID of the book to borrow", example=3)
    student_id: str = Field(
        ...,
        description="Student ID number",
        example="LIM2024001",
        min_length=3,
        max_length=20,
    )

    @field_validator("student_id")
    @classmethod
    def student_id_must_not_be_blank(cls, v: str) -> str:
        """Ensure the student ID is not just whitespace."""
        if not v.strip():
            raise ValueError("student_id must not be blank or whitespace.")
        return v.strip().upper()

    model_config = {"json_schema_extra": {"example": {
        "book_id": 3,
        "student_id": "LIM2024001",
    }}}


class ReturnRequest(BaseModel):
    """
    Request body for returning a book (POST /return).

    Attributes:
        book_id    (int): The ID of the book being returned.
        student_id (str): The student ID — must match the original borrower.
    """

    book_id: int = Field(..., description="ID of the book to return", example=3)
    student_id: str = Field(
        ...,
        description="Student ID of the borrower returning the book",
        example="LIM2024001",
        min_length=3,
        max_length=20,
    )

    @field_validator("student_id")
    @classmethod
    def student_id_must_not_be_blank(cls, v: str) -> str:
        """Ensure the student ID is not just whitespace."""
        if not v.strip():
            raise ValueError("student_id must not be blank or whitespace.")
        return v.strip().upper()

    model_config = {"json_schema_extra": {"example": {
        "book_id": 3,
        "student_id": "LIM2024001",
    }}}


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class SearchResponse(BaseModel):
    """
    Response body for GET /books.

    Attributes:
        results         (list[Book]):  List of books matching the search criteria.
        total           (int):         Total count of matching results.
        filters_applied (dict):        Active search filters echoed back to the client.
    """

    results: list[Book] = Field(..., description="List of matching books")
    total: int = Field(..., description="Total number of matching results", example=5)
    filters_applied: dict[str, Any] = Field(
        default_factory=dict,
        description="Active filters used for this query",
    )


class BorrowResponse(BaseModel):
    """
    Response body for POST /borrow.

    Attributes:
        message     (str):  Human-readable confirmation message.
        book        (Book): The updated book record.
        borrowed_on (date): Date the book was borrowed.
        due_date    (date): Return deadline.
    """

    message: str = Field(..., description="Confirmation message")
    book: Book = Field(..., description="Updated book record")
    borrowed_on: date = Field(..., description="Date borrowed")
    due_date: date = Field(..., description="Return due date")


class ReturnResponse(BaseModel):
    """
    Response body for POST /return.

    Attributes:
        message       (str):   Human-readable confirmation message.
        book          (Book):  The updated (cleared) book record.
        fine_amount   (float): Fine in MYR (0.0 if returned on time).
        days_overdue  (int):   Number of days past due (0 if on time).
        returned_on   (date):  Date the book was returned.
    """

    message: str = Field(..., description="Confirmation message")
    book: Book = Field(..., description="Updated book record")
    fine_amount: float = Field(..., description="Fine in MYR", example=0.0)
    days_overdue: int = Field(..., description="Days past the due date", example=0)
    returned_on: date = Field(..., description="Date returned")


class OverdueRecord(BaseModel):
    """
    Represents a single overdue borrow record (used by GET /overdue).

    Attributes:
        book         (Book):  The overdue book.
        student_id   (str):   ID of the student who borrowed it.
        due_date     (date):  Original return deadline.
        days_overdue (int):   How many days past the deadline.
        fine_amount  (float): Accrued fine in MYR.
    """

    book: Book = Field(..., description="The overdue book")
    student_id: str = Field(..., description="Borrowing student ID", example="LIM2024002")
    due_date: date = Field(..., description="Return deadline")
    days_overdue: int = Field(..., description="Days past due", example=5)
    fine_amount: float = Field(..., description="Fine in MYR", example=5.00)


class HealthResponse(BaseModel):
    """
    Response body for GET / (health check).

    Attributes:
        status   (str): Application status string.
        message  (str): Welcome or status message.
        version  (str): Current API version.
        docs_url (str): URL to the interactive API documentation.
    """

    status: str = Field(..., example="online")
    message: str = Field(..., example="Welcome to Limkokwing University Library API")
    version: str = Field(..., example="1.0.0")
    docs_url: str = Field(..., example="/docs")
