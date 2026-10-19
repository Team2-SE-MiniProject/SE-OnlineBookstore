from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import Book
from .models import Review


class ReviewModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="reviewer",
            password="testpassword123"
        )
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            price="299.00",
            stock=10
        )

    def test_create_review(self):
        review = Review.objects.create(
            user=self.user,
            book=self.book,
            rating=5,
            comment="Great book!"
        )

        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Great book!")
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.book, self.book)

    def test_one_review_per_user_per_book(self):
        Review.objects.create(
            user=self.user,
            book=self.book,
            rating=5
        )

        with self.assertRaises(Exception):
            Review.objects.create(
                user=self.user,
                book=self.book,
                rating=4
            )
