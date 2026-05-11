"""
Limkokwing University Library Management System API
====================================================
Author  : Senior Backend Engineer
Date    : 2026-04-27
Version : 1.0.0

A RESTful API built with FastAPI for managing the Limkokwing University library.
Supports book search, borrowing, returning, and overdue fine calculation.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime, timedelta
from typing import Optional
import asyncio

from models import (
    Book,
    BorrowRequest,
    BorrowResponse,
    ReturnRequest,
    ReturnResponse,
    OverdueRecord,
    SearchResponse,
    HealthResponse,
)
from database import BOOKS_DB
from config import (
    APP_TITLE,
    APP_DESCRIPTION,
    APP_VERSION,
    FINE_PER_DAY,
    BORROW_DURATION_DAYS,
    TAGS_METADATA,
)


# ---------------------------------------------------------------------------
# Application Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------


@app.get(
    "/",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
)
async def root() -> HealthResponse:
    """
    Health check endpoint.

    Returns a simple status message confirming the API is online and available.

    Returns:
        HealthResponse: A dict containing the API status and a welcome message.
    """
    await asyncio.sleep(0)  # yield to event loop (demonstrates async pattern)
    return HealthResponse(
        status="online",
        message="Welcome to Limkokwing University Library Management System API",
        version=APP_VERSION,
        docs_url="/docs",
    )


# ---------------------------------------------------------------------------
# GET /books — Search Books
# ---------------------------------------------------------------------------


@app.get(
    "/books",
    response_model=SearchResponse,
    tags=["Books"],
    summary="Search the book catalogue",
)
async def get_books(
    title: Optional[str] = Query(
        default=None,
        description="Filter by book title (case-insensitive partial match)",
        examples=["python"],
    ),
    author: Optional[str] = Query(
        default=None,
        description="Filter by author name (case-insensitive partial match)",
        examples=["Martin"],
    ),
    category: Optional[str] = Query(
        default=None,
        description="Filter by category/genre (case-insensitive partial match)",
        examples=["Computer Science"],
    ),
    available_only: bool = Query(
        default=False,
        description="If true, only returns books that are not currently borrowed",
    ),
) -> SearchResponse:
    """
    Search the library book catalogue with optional filters.

    Supports filtering by title, author, and/or category using case-insensitive
    partial string matching. Multiple filters may be applied simultaneously.
    If no filters are supplied, the full catalogue is returned.

    Args:
        title         (str, optional): Partial or full title to search for.
        author        (str, optional): Partial or full author name to search for.
        category      (str, optional): Partial or full category name to search for.
        available_only (bool):         When True, exclude borrowed books from results.

    Returns:
        SearchResponse: A response object containing:
            - ``results``  (list[Book]): Matching books.
            - ``total``    (int):        Number of matching books.
            - ``filters_applied`` (dict): Echo of the active search filters.

    Raises:
        HTTPException 404: Raised if no books match the given filters.
    """
    await asyncio.sleep(0)  # non-blocking yield

    results: list[dict] = list(BOOKS_DB)  # shallow copy to avoid mutation

    if title:
        results = [b for b in results if title.lower() in b["title"].lower()]

    if author:
        results = [b for b in results if author.lower() in b["author"].lower()]

    if category:
        results = [b for b in results if category.lower() in b["category"].lower()]

    if available_only:
        results = [b for b in results if not b["is_borrowed"]]

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No books found matching the provided search criteria.",
        )

    filters_applied: dict = {
        k: v
        for k, v in {
            "title": title,
            "author": author,
            "category": category,
            "available_only": available_only if available_only else None,
        }.items()
        if v is not None
    }

    return SearchResponse(
        results=[Book(**b) for b in results],
        total=len(results),
        filters_applied=filters_applied,
    )


# ---------------------------------------------------------------------------
# POST /borrow — Borrow a Book
# ---------------------------------------------------------------------------


@app.post(
    "/borrow",
    response_model=BorrowResponse,
    tags=["Borrowing"],
    summary="Borrow a book",
    status_code=200,
)
async def borrow_book(request: BorrowRequest) -> BorrowResponse:
    """
    Borrow a book from the library.

    Marks the requested book as borrowed and records the borrower's student ID
    along with the borrow date and calculated due date. The borrow period is
    defined by ``BORROW_DURATION_DAYS`` in the application config (default: 14 days).

    Args:
        request (BorrowRequest): Request body containing:
            - ``book_id``    (int):  The unique ID of the book to borrow.
            - ``student_id`` (str):  The borrower's student ID number.

    Returns:
        BorrowResponse: A response object containing:
            - ``message``       (str):  Confirmation message.
            - ``book``          (Book): Updated book record.
            - ``borrowed_on``   (date): Date the book was borrowed.
            - ``due_date``      (date): Date by which the book must be returned.

    Raises:
        HTTPException 404: Raised if the book ID does not exist in the catalogue.
        HTTPException 409: Raised if the book is already borrowed by another student.
    """
    await asyncio.sleep(0)

    # Locate the book in the in-memory database
    book: Optional[dict] = next(
        (b for b in BOOKS_DB if b["id"] == request.book_id), None
    )

    if book is None:
        raise HTTPException(
            status_code=404,
            detail=f"Book with ID {request.book_id} was not found in the catalogue.",
        )

    if book["is_borrowed"]:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Book '{book['title']}' is currently borrowed by student "
                f"{book['borrowed_by']}. Please check back later."
            ),
        )

    # Update book status
    today: date = date.today()
    due: date = today + timedelta(days=BORROW_DURATION_DAYS)

    book["is_borrowed"] = True
    book["borrowed_by"] = request.student_id
    book["borrowed_on"] = today.isoformat()
    book["due_date"] = due.isoformat()

    return BorrowResponse(
        message=f"'{book['title']}' successfully borrowed. Please return by {due}.",
        book=Book(**book),
        borrowed_on=today,
        due_date=due,
    )


# ---------------------------------------------------------------------------
# POST /return — Return a Book
# ---------------------------------------------------------------------------


@app.post(
    "/return",
    response_model=ReturnResponse,
    tags=["Borrowing"],
    summary="Return a borrowed book",
    status_code=200,
)
async def return_book(request: ReturnRequest) -> ReturnResponse:
    """
    Return a previously borrowed book to the library.

    Resets the book's status to available and clears all borrowing metadata.
    If the book is returned after the due date, an overdue fine is calculated
    based on the number of days late multiplied by ``FINE_PER_DAY`` (in MYR).

    Args:
        request (ReturnRequest): Request body containing:
            - ``book_id``    (int): The unique ID of the book being returned.
            - ``student_id`` (str): The ID of the student returning the book
                                    (must match the borrower).

    Returns:
        ReturnResponse: A response object containing:
            - ``message``       (str):            Confirmation message.
            - ``book``          (Book):            Updated (cleared) book record.
            - ``fine_amount``   (float):           Fine owed in MYR (0.0 if on time).
            - ``days_overdue``  (int):             Number of days past due (0 if on time).
            - ``returned_on``   (date):            Date the book was returned.

    Raises:
        HTTPException 404: Raised if the book ID does not exist.
        HTTPException 400: Raised if the book is not currently borrowed.
        HTTPException 403: Raised if the student_id does not match the borrower.
    """
    await asyncio.sleep(0)

    book: Optional[dict] = next(
        (b for b in BOOKS_DB if b["id"] == request.book_id), None
    )

    if book is None:
        raise HTTPException(
            status_code=404,
            detail=f"Book with ID {request.book_id} was not found in the catalogue.",
        )

    if not book["is_borrowed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Book '{book['title']}' is not currently borrowed.",
        )

    if book["borrowed_by"] != request.student_id:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Student ID '{request.student_id}' does not match the borrower on record. "
                "Only the borrowing student may return this book."
            ),
        )

    # Calculate fine if overdue
    today: date = date.today()
    due_date: date = date.fromisoformat(book["due_date"])
    days_overdue: int = max(0, (today - due_date).days)
    fine_amount: float = round(days_overdue * FINE_PER_DAY, 2)

    # Reset book status
    book["is_borrowed"] = False
    book["borrowed_by"] = None
    book["borrowed_on"] = None
    book["due_date"] = None

    fine_msg: str = (
        f" An overdue fine of MYR {fine_amount:.2f} ({days_overdue} day(s)) applies."
        if days_overdue > 0
        else " Returned on time — no fine applied."
    )

    return ReturnResponse(
        message=f"'{book['title']}' successfully returned.{fine_msg}",
        book=Book(**book),
        fine_amount=fine_amount,
        days_overdue=days_overdue,
        returned_on=today,
    )


# ---------------------------------------------------------------------------
# GET /overdue — List Overdue Books & Calculate Fines
# ---------------------------------------------------------------------------


@app.get(
    "/overdue",
    response_model=list[OverdueRecord],
    tags=["Overdue & Fines"],
    summary="Retrieve all overdue books and their fines",
)
async def get_overdue_books() -> list[OverdueRecord]:
    """
    Retrieve all currently overdue borrowed books along with accrued fines.

    Iterates through the in-memory database and identifies books that are:
    1. Currently borrowed (``is_borrowed`` is True), **and**
    2. Past their due date (``due_date`` < today).

    For each overdue book the fine is calculated as:
        ``fine = days_overdue × FINE_PER_DAY``

    Args:
        None

    Returns:
        list[OverdueRecord]: A list of overdue records, each containing:
            - ``book``          (Book):  The overdue book details.
            - ``student_id``    (str):   The ID of the borrowing student.
            - ``due_date``      (date):  The original return deadline.
            - ``days_overdue``  (int):   Number of days past the deadline.
            - ``fine_amount``   (float): Accrued fine in MYR.

        Returns an empty list if no books are currently overdue.
    """
    await asyncio.sleep(0)

    today: date = date.today()
    overdue_records: list[OverdueRecord] = []

    for book in BOOKS_DB:
        if not book["is_borrowed"] or book["due_date"] is None:
            continue

        due_date: date = date.fromisoformat(book["due_date"])
        days_overdue: int = (today - due_date).days

        if days_overdue > 0:
            fine_amount: float = round(days_overdue * FINE_PER_DAY, 2)
            overdue_records.append(
                OverdueRecord(
                    book=Book(**book),
                    student_id=book["borrowed_by"],
                    due_date=due_date,
                    days_overdue=days_overdue,
                    fine_amount=fine_amount,
                )
            )

    return overdue_records
