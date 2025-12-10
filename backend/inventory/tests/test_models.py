"""
モデルのテスト
TDD: まずテストを書いて失敗を確認し、その後実装する
"""

from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone

from inventory.models import (
    Genre,
    Book,
    Inventory,
    InventoryTransaction,
    TransactionType,
    Sale,
)


class GenreModelTest(TestCase):
    """Genre モデルのテスト"""

    def test_genre_creation(self):
        """ジャンルを作成できること"""
        genre = Genre.objects.create(name="Fiction")
        self.assertEqual(genre.name, "Fiction")
        self.assertIsNotNone(genre.created_at)

    def test_genre_unique_name(self):
        """ジャンル名は一意であること"""
        Genre.objects.create(name="Fiction")
        with self.assertRaises(IntegrityError):
            Genre.objects.create(name="Fiction")

    def test_genre_str(self):
        """__str__ はジャンル名を返すこと"""
        genre = Genre.objects.create(name="Fiction")
        self.assertEqual(str(genre), "Fiction")


class BookModelTest(TestCase):
    """Book モデルのテスト"""

    def setUp(self):
        self.genre = Genre.objects.create(name="Fiction")

    def test_book_creation(self):
        """書籍を作成できること"""
        book = Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )
        self.assertEqual(book.isbn, "9784123456789")
        self.assertEqual(book.title, "Test Book")
        self.assertEqual(book.author, "Test Author")
        self.assertEqual(book.publisher, "Test Publisher")
        self.assertEqual(book.genre, self.genre)
        self.assertEqual(book.price, 1500)
        self.assertIsNotNone(book.created_at)
        self.assertIsNotNone(book.updated_at)

    def test_book_isbn_unique(self):
        """ISBN は一意であること"""
        Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )
        with self.assertRaises(IntegrityError):
            Book.objects.create(
                isbn="9784123456789",
                title="Another Book",
                author="Another Author",
                publisher="Another Publisher",
                genre=self.genre,
                price=2000,
            )

    def test_book_genre_relationship(self):
        """書籍からジャンルを参照できること"""
        book = Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )
        self.assertEqual(book.genre.name, "Fiction")
        self.assertIn(book, self.genre.books.all())

    def test_book_str(self):
        """__str__ は書籍タイトルを返すこと"""
        book = Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )
        self.assertEqual(str(book), "Test Book")


class InventoryModelTest(TestCase):
    """Inventory モデルのテスト"""

    def setUp(self):
        self.genre = Genre.objects.create(name="Fiction")
        self.book = Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )

    def test_inventory_creation(self):
        """在庫を作成できること"""
        inventory = Inventory.objects.create(book=self.book, quantity=10)
        self.assertEqual(inventory.book, self.book)
        self.assertEqual(inventory.quantity, 10)
        self.assertIsNotNone(inventory.updated_at)

    def test_inventory_default_quantity(self):
        """在庫のデフォルト数量は 0 であること"""
        inventory = Inventory.objects.create(book=self.book)
        self.assertEqual(inventory.quantity, 0)

    def test_inventory_book_one_to_one(self):
        """書籍と在庫は 1:1 の関係であること"""
        Inventory.objects.create(book=self.book, quantity=10)
        with self.assertRaises(IntegrityError):
            Inventory.objects.create(book=self.book, quantity=5)

    def test_inventory_str(self):
        """__str__ は書籍タイトルと数量を返すこと"""
        inventory = Inventory.objects.create(book=self.book, quantity=10)
        self.assertEqual(str(inventory), "Test Book: 10")


class InventoryTransactionModelTest(TestCase):
    """InventoryTransaction モデルのテスト"""

    def setUp(self):
        self.genre = Genre.objects.create(name="Fiction")
        self.book = Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )
        self.inventory = Inventory.objects.create(book=self.book, quantity=10)

    def test_transaction_creation(self):
        """在庫変動履歴を作成できること"""
        transaction = InventoryTransaction.objects.create(
            inventory=self.inventory,
            transaction_type=TransactionType.ARRIVAL,
            quantity=10,
        )
        self.assertEqual(transaction.inventory, self.inventory)
        self.assertEqual(transaction.transaction_type, TransactionType.ARRIVAL)
        self.assertEqual(transaction.quantity, 10)
        self.assertEqual(transaction.reason, "")
        self.assertIsNotNone(transaction.created_at)

    def test_transaction_types(self):
        """すべてのトランザクションタイプを作成できること"""
        for tx_type in TransactionType:
            transaction = InventoryTransaction.objects.create(
                inventory=self.inventory,
                transaction_type=tx_type,
                quantity=1,
            )
            self.assertEqual(transaction.transaction_type, tx_type)

    def test_transaction_with_reason(self):
        """理由付きの在庫変動履歴を作成できること"""
        transaction = InventoryTransaction.objects.create(
            inventory=self.inventory,
            transaction_type=TransactionType.THEFT,
            quantity=2,
            reason="棚卸し時に発覚",
        )
        self.assertEqual(transaction.reason, "棚卸し時に発覚")

    def test_transaction_str(self):
        """__str__ はトランザクション情報を返すこと"""
        transaction = InventoryTransaction.objects.create(
            inventory=self.inventory,
            transaction_type=TransactionType.ARRIVAL,
            quantity=10,
        )
        self.assertEqual(str(transaction), "Test Book: ARRIVAL 10")


class SaleModelTest(TestCase):
    """Sale モデルのテスト"""

    def setUp(self):
        self.genre = Genre.objects.create(name="Fiction")
        self.book = Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )

    def test_sale_creation(self):
        """売上を作成できること"""
        sold_at = timezone.now()
        sale = Sale.objects.create(
            book=self.book,
            quantity=2,
            unit_price=1500,
            sold_at=sold_at,
        )
        self.assertEqual(sale.book, self.book)
        self.assertEqual(sale.quantity, 2)
        self.assertEqual(sale.unit_price, 1500)
        self.assertEqual(sale.sold_at, sold_at)
        self.assertIsNotNone(sale.created_at)

    def test_sale_book_relationship(self):
        """売上から書籍を参照できること"""
        sale = Sale.objects.create(
            book=self.book,
            quantity=2,
            unit_price=1500,
            sold_at=timezone.now(),
        )
        self.assertEqual(sale.book.title, "Test Book")
        self.assertIn(sale, self.book.sales.all())

    def test_sale_str(self):
        """__str__ は売上情報を返すこと"""
        sale = Sale.objects.create(
            book=self.book,
            quantity=2,
            unit_price=1500,
            sold_at=timezone.now(),
        )
        self.assertEqual(str(sale), "Test Book x 2")
