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
    ("Life of Pi", "Yann Martel", "Fiction", "279.00")
]

TOTAL = 25  # more than one page (20 per page) so pagination is visible in the demo


class Command(BaseCommand):
    help = "Load sample books for development and the demo (safe to run twice)."

    def handle(self, *args, **options):
        rows = list(BOOKS)
        genres = ["Fiction", "Non-fiction", "Fantasy", "Science Fiction"]
        for i in range(len(BOOKS) + 1, TOTAL + 1):
            rows.append((f"Sample Book {i}", f"Sample Author {i}", genres[i % 4], str(199 + i)))

        created = 0
        for title, author, genre, price in rows:
            _, was_created = Book.objects.get_or_create(
                title=title,
                author=author,
                defaults={
                    "genre": genre,
                    "price": Decimal(price),
                    "stock": 25,
                    "description": f"Sample description for {title}.",
                    "cover": f"https://placehold.co/200x300?text={quote_plus(title)}",
                },
            )
            created += was_created

        self.stdout.write(
            self.style.SUCCESS(f"Added {created} books ({Book.objects.count()} total).")
        )