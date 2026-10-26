from decimal import Decimal
from urllib.parse import quote_plus

from django.core.management.base import BaseCommand

from catalog.models import Book

# (title, author, genre, price)
BOOKS = [
    ("Pride and Prejudice", "Jane Austen", "Classic", "299.00"),
    ("1984", "George Orwell", "Science Fiction", "349.00"),
    ("The Hobbit", "J.R.R. Tolkien", "Fantasy", "399.00"),
    ("To Kill a Mockingbird", "Harper Lee", "Classic", "329.00"),
    ("Dune", "Frank Herbert", "Science Fiction", "499.00"),
    ("Sapiens", "Yuval Noah Harari", "Non-fiction", "449.00"),
    ("Clean Code", "Robert C. Martin", "Programming", "599.00"),
    ("The Pragmatic Programmer", "Andrew Hunt and David Thomas", "Programming", "649.00"),
    ("The Alchemist", "Paulo Coelho", "Fiction", "279.00"),
    ("Wings of Fire", "A. P. J. Abdul Kalam", "Non-fiction", "259.00"),
    ("The Great Gatsby", "F. Scott Fitzgerald", "Classic", "319.00"),
    ("The Catcher in the Rye", "J.D. Salinger", "Classic", "299.00"),
    ("Brave New World", "Aldous Huxley", "Science Fiction", "349.00"),
    ("The Lord of the Rings", "J.R.R. Tolkien", "Fantasy", "699.00"),
    ("The Lean Startup", "Eric Ries", "Business", "399.00"),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "Non-fiction", "449.00"),
    ("The Art of War", "Sun Tzu", "Non-fiction", "199.00"),
    ("The Road to Reality", "Roger Penrose", "Science", "599.00"),
    ("The Selfish Gene", "Richard Dawkins", "Science", "499.00"),
    ("Guns, Germs, and Steel", "Jared Diamond", "History", "549.00"),
    ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "Fantasy", "399.00"),
    ("The Da Vinci Code", "Dan Brown", "Thriller", "349.00"),
    ("The Girl with the Dragon Tattoo", "Stieg Larsson", "Thriller", "329.00"),
    ("The Hunger Games", "Suzanne Collins", "Science Fiction", "299.00"),
    ("The Fault in Our Stars", "John Green", "Fiction", "279.00"),
    ("The Shining", "Stephen King", "Horror", "399.00"),
    ("The Exorcist", "William Peter Blatty", "Horror", "349.00"),
    ("The Silence of the Lambs", "Thomas Harris", "Thriller", "329.00"),
    ("The Martian", "Andy Weir", "Science Fiction", "399.00"),
    ("The Girl on the Train", "Paula Hawkins", "Thriller", "299.00"),
    ("Gone Girl", "Gillian Flynn", "Thriller", "349.00"),
    ("The Help", "Kathryn Stockett", "Fiction", "279.00"),
    ("The Kite Runner", "Khaled Hosseini", "Fiction", "299.00"),
    ("Life of Pi", "Yann Martel", "Fiction", "279.00"),
]

# Real ISBN-13 numbers, so the book list can show real covers from Open Library.
# The key must match the title in BOOKS exactly. A book with no entry here keeps a
# placeholder cover and a made-up ISBN. If a cover looks wrong or is missing, check the
# ISBN on openlibrary.org (search the title, open an edition) or delete that line.
REAL_ISBNS = {
    "Pride and Prejudice": "9780141439518",
    "1984": "9780451524935",
    "The Hobbit": "9780547928227",
    "To Kill a Mockingbird": "9780060935467",
    "Dune": "9780441013593",
    "Sapiens": "9780062316097",
    "Clean Code": "9780132350884",
    "The Pragmatic Programmer": "9780135957059",
    "The Alchemist": "9780062315007",
    "Wings of Fire": "9788173711466",
    "The Great Gatsby": "9780743273565",
    "The Catcher in the Rye": "9780316769488",
    "Brave New World": "9780060850524",
    "The Lord of the Rings": "9780618640157",
    "The Lean Startup": "9780307887894",
    "Thinking, Fast and Slow": "9780374533557",
    "The Road to Reality": "9780679776314",
    "The Selfish Gene": "9780198788607",
    "Guns, Germs, and Steel": "9780393317558",
    "Harry Potter and the Sorcerer's Stone": "9780590353427",
    "The Da Vinci Code": "9780307474278",
    "The Girl with the Dragon Tattoo": "9780307454546",
    "The Hunger Games": "9780439023528",
    "The Fault in Our Stars": "9780142424179",
    "The Shining": "9780307743657",
    "The Silence of the Lambs": "9780312924584",
    "The Martian": "9780553418026",
    "The Girl on the Train": "9781594634024",
    "Gone Girl": "9780307588371",
    "The Help": "9780425232200",
    "The Kite Runner": "9781594631931",
    "Life of Pi": "9780156027328",
}

# default=false makes Open Library answer 404 when it has no cover. The page then hides
# the broken image and shows the grey box instead of a 1-pixel placeholder.
COVER_URL = "https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg?default=false"

TOTAL = 25  # more than one page (20 per page) so pagination is visible in the demo


class Command(BaseCommand):
    help = "Load sample books for development and the demo (safe to run twice)."

    def handle(self, *args, **options):
        rows = list(BOOKS)
        genres = ["Fiction", "Non-fiction", "Fantasy", "Science Fiction", "Business", "Classic", "History", "Horror", "Programming", "Science", "Thriller"]
        for i in range(len(BOOKS) + 1, TOTAL + 1):
            rows.append((f"Sample Book {i}", f"Sample Author {i}", genres[i % 4], str(199 + i)))

        created = 0
        for n, (title, author, genre, price) in enumerate(rows, start=1):
            isbn = REAL_ISBNS.get(title)
            _, was_created = Book.objects.update_or_create(
                title=title,
                author=author,
                defaults={
                    "isbn": isbn or f"9780000{n:06d}",
                    "genre": genre,
                    "price": Decimal(price),
                    "stock": 25,
                    "description": f"Sample description for {title}.",
                    "cover": (
                        COVER_URL.format(isbn=isbn)
                        if isbn
                        else f"https://placehold.co/200x300?text={quote_plus(title)}"
                    ),
                },
            )
            created += was_created

        self.stdout.write(
            self.style.SUCCESS(f"Added {created} books ({Book.objects.count()} total).")
        )