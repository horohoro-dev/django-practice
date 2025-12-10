"""
API ビューのテスト
TDD: まずテストを書いて失敗を確認し、その後実装する
"""

from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import (
    Genre,
    Book,
    Inventory,
    InventoryTransaction,
    TransactionType,
    Sale,
)


class InventoryListAPITest(APITestCase):
    """在庫一覧API のテスト"""

    def setUp(self):
        self.genre = Genre.objects.create(name="Fiction")

    def test_get_inventory_list_returns_200(self):
        """在庫一覧を取得できること"""
        response = self.client.get("/api/v1/inventory/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_inventory_list_pagination_100(self):
        """100件単位でページングされること"""
        # 150冊の書籍と在庫を作成
        for i in range(150):
            book = Book.objects.create(
                isbn=f"978412345{i:04d}",
                title=f"Test Book {i}",
                author="Test Author",
                publisher="Test Publisher",
                genre=self.genre,
                price=1500,
            )
            Inventory.objects.create(book=book, quantity=10)

        response = self.client.get("/api/v1/inventory/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 100)
        self.assertIsNotNone(response.data["next"])

    def test_get_inventory_list_includes_book_info(self):
        """在庫一覧に書籍情報が含まれること"""
        book = Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )
        Inventory.objects.create(book=book, quantity=10)

        response = self.client.get("/api/v1/inventory/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result = response.data["results"][0]
        self.assertEqual(result["quantity"], 10)
        self.assertEqual(result["book"]["title"], "Test Book")
        self.assertEqual(result["book"]["isbn"], "9784123456789")


class ArrivalAPITest(APITestCase):
    """入荷登録API のテスト"""

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

    def test_create_arrival_success(self):
        """入荷登録が成功すること"""
        response = self.client.post(
            "/api/v1/arrivals/",
            {"book_id": self.book.id, "quantity": 10},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_arrival_increases_inventory(self):
        """入荷登録で在庫が増加すること"""
        Inventory.objects.create(book=self.book, quantity=5)
        self.client.post(
            "/api/v1/arrivals/",
            {"book_id": self.book.id, "quantity": 10},
        )
        inventory = Inventory.objects.get(book=self.book)
        self.assertEqual(inventory.quantity, 15)

    def test_create_arrival_creates_inventory_if_not_exists(self):
        """在庫が存在しない場合は新規作成すること"""
        self.client.post(
            "/api/v1/arrivals/",
            {"book_id": self.book.id, "quantity": 10},
        )
        inventory = Inventory.objects.get(book=self.book)
        self.assertEqual(inventory.quantity, 10)

    def test_create_arrival_creates_transaction(self):
        """入荷登録で在庫変動履歴が作成されること"""
        Inventory.objects.create(book=self.book, quantity=0)
        self.client.post(
            "/api/v1/arrivals/",
            {"book_id": self.book.id, "quantity": 10},
        )
        transaction = InventoryTransaction.objects.get(inventory__book=self.book)
        self.assertEqual(transaction.transaction_type, TransactionType.ARRIVAL)
        self.assertEqual(transaction.quantity, 10)


class InventoryAdjustmentAPITest(APITestCase):
    """在庫調整API (紛失・万引き) のテスト"""

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

    def test_inventory_adjustment_loss(self):
        """紛失による在庫調整ができること"""
        response = self.client.post(
            "/api/v1/inventory-adjustments/",
            {
                "book_id": self.book.id,
                "transaction_type": "LOSS",
                "quantity": 2,
                "reason": "棚卸し時に発覚",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 8)

    def test_inventory_adjustment_theft(self):
        """万引きによる在庫調整ができること"""
        response = self.client.post(
            "/api/v1/inventory-adjustments/",
            {
                "book_id": self.book.id,
                "transaction_type": "THEFT",
                "quantity": 3,
                "reason": "防犯カメラで確認",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 7)

    def test_inventory_adjustment_requires_reason(self):
        """理由が必須であること"""
        response = self.client.post(
            "/api/v1/inventory-adjustments/",
            {
                "book_id": self.book.id,
                "transaction_type": "LOSS",
                "quantity": 2,
                "reason": "",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inventory_adjustment_creates_transaction(self):
        """在庫変動履歴が作成されること"""
        self.client.post(
            "/api/v1/inventory-adjustments/",
            {
                "book_id": self.book.id,
                "transaction_type": "THEFT",
                "quantity": 2,
                "reason": "防犯カメラで確認",
            },
        )
        transaction = InventoryTransaction.objects.get(
            inventory=self.inventory, transaction_type=TransactionType.THEFT
        )
        self.assertEqual(transaction.quantity, 2)
        self.assertEqual(transaction.reason, "防犯カメラで確認")

    def test_inventory_adjustment_cannot_exceed_quantity(self):
        """在庫数を超える減少はできないこと"""
        response = self.client.post(
            "/api/v1/inventory-adjustments/",
            {
                "book_id": self.book.id,
                "transaction_type": "LOSS",
                "quantity": 15,
                "reason": "棚卸し時に発覚",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SaleAPITest(APITestCase):
    """売上記録API のテスト"""

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

    def test_create_sale_success(self):
        """売上記録が成功すること"""
        response = self.client.post(
            "/api/v1/sales/",
            {
                "book_id": self.book.id,
                "quantity": 2,
                "sold_at": timezone.now().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_sale_decreases_inventory(self):
        """売上で在庫が減少すること"""
        self.client.post(
            "/api/v1/sales/",
            {
                "book_id": self.book.id,
                "quantity": 2,
                "sold_at": timezone.now().isoformat(),
            },
        )
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, 8)

    def test_create_sale_creates_transaction(self):
        """在庫変動履歴が作成されること"""
        self.client.post(
            "/api/v1/sales/",
            {
                "book_id": self.book.id,
                "quantity": 2,
                "sold_at": timezone.now().isoformat(),
            },
        )
        transaction = InventoryTransaction.objects.get(
            inventory=self.inventory, transaction_type=TransactionType.SALE
        )
        self.assertEqual(transaction.quantity, 2)

    def test_create_sale_records_unit_price(self):
        """販売時点の価格が記録されること"""
        self.client.post(
            "/api/v1/sales/",
            {
                "book_id": self.book.id,
                "quantity": 2,
                "sold_at": timezone.now().isoformat(),
            },
        )
        sale = Sale.objects.get(book=self.book)
        self.assertEqual(sale.unit_price, 1500)

    def test_create_sale_cannot_exceed_inventory(self):
        """在庫を超える販売はできないこと"""
        response = self.client.post(
            "/api/v1/sales/",
            {
                "book_id": self.book.id,
                "quantity": 15,
                "sold_at": timezone.now().isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TopSalesAPITest(APITestCase):
    """売上上位API のテスト"""

    def setUp(self):
        self.genre1 = Genre.objects.create(name="Fiction")
        self.genre2 = Genre.objects.create(name="Non-Fiction")

        # 書籍を作成
        self.book1 = Book.objects.create(
            isbn="9784123456781",
            title="Popular Book",
            author="Author 1",
            publisher="Publisher",
            genre=self.genre1,
            price=1500,
        )
        self.book2 = Book.objects.create(
            isbn="9784123456782",
            title="Less Popular Book",
            author="Author 2",
            publisher="Publisher",
            genre=self.genre1,
            price=2000,
        )
        self.book3 = Book.objects.create(
            isbn="9784123456783",
            title="Non-Fiction Book",
            author="Author 3",
            publisher="Publisher",
            genre=self.genre2,
            price=2500,
        )

        # 売上を作成（book1 が最も売れている）
        now = timezone.now()
        Sale.objects.create(book=self.book1, quantity=10, unit_price=1500, sold_at=now)
        Sale.objects.create(
            book=self.book1, quantity=5, unit_price=1500, sold_at=now - timedelta(days=3)
        )
        Sale.objects.create(book=self.book2, quantity=3, unit_price=2000, sold_at=now)
        Sale.objects.create(book=self.book3, quantity=8, unit_price=2500, sold_at=now)

    def test_get_top_sales_1week(self):
        """1週間の売上上位を取得できること"""
        response = self.client.get("/api/v1/sales/top/", {"period": "1w"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        # book1 (15冊) が1位
        self.assertEqual(response.data[0]["book_id"], self.book1.id)
        self.assertEqual(response.data[0]["total_quantity"], 15)

    def test_get_top_sales_all_time(self):
        """全期間の売上上位を取得できること"""
        response = self.client.get("/api/v1/sales/top/", {"period": "all"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_top_sales_returns_correct_order(self):
        """売上順に正しくソートされること"""
        response = self.client.get("/api/v1/sales/top/", {"period": "1w"})
        quantities = [item["total_quantity"] for item in response.data]
        self.assertEqual(quantities, sorted(quantities, reverse=True))

    def test_get_top_sales_with_limit(self):
        """取得件数を制限できること"""
        response = self.client.get("/api/v1/sales/top/", {"period": "1w", "limit": 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_get_top_sales_requires_period(self):
        """period パラメータが必須であること"""
        response = self.client.get("/api/v1/sales/top/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TopSalesByGenreAPITest(APITestCase):
    """ジャンル別売上上位API のテスト"""

    def setUp(self):
        self.genre1 = Genre.objects.create(name="Fiction")
        self.genre2 = Genre.objects.create(name="Non-Fiction")

        self.book1 = Book.objects.create(
            isbn="9784123456781",
            title="Fiction Book 1",
            author="Author 1",
            publisher="Publisher",
            genre=self.genre1,
            price=1500,
        )
        self.book2 = Book.objects.create(
            isbn="9784123456782",
            title="Fiction Book 2",
            author="Author 2",
            publisher="Publisher",
            genre=self.genre1,
            price=2000,
        )
        self.book3 = Book.objects.create(
            isbn="9784123456783",
            title="Non-Fiction Book",
            author="Author 3",
            publisher="Publisher",
            genre=self.genre2,
            price=2500,
        )

        now = timezone.now()
        Sale.objects.create(book=self.book1, quantity=10, unit_price=1500, sold_at=now)
        Sale.objects.create(book=self.book2, quantity=5, unit_price=2000, sold_at=now)
        Sale.objects.create(book=self.book3, quantity=20, unit_price=2500, sold_at=now)

    def test_get_top_sales_by_genre(self):
        """ジャンル別売上上位を取得できること"""
        response = self.client.get(
            "/api/v1/sales/top/by-genre/",
            {"period": "1w", "genre_id": self.genre1.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Fiction ジャンルの書籍のみ
        self.assertEqual(len(response.data), 2)

    def test_get_top_sales_by_genre_filters_correctly(self):
        """指定したジャンルの書籍のみが返されること"""
        response = self.client.get(
            "/api/v1/sales/top/by-genre/",
            {"period": "1w", "genre_id": self.genre1.id},
        )
        for item in response.data:
            book = Book.objects.get(id=item["book_id"])
            self.assertEqual(book.genre_id, self.genre1.id)

    def test_get_top_sales_by_genre_requires_genre_id(self):
        """genre_id パラメータが必須であること"""
        response = self.client.get("/api/v1/sales/top/by-genre/", {"period": "1w"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GenreAPITest(APITestCase):
    """ジャンルAPI のテスト"""

    def test_list_genres(self):
        """ジャンル一覧を取得できること"""
        Genre.objects.create(name="Fiction")
        Genre.objects.create(name="Non-Fiction")
        response = self.client.get("/api/v1/genres/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_create_genre(self):
        """ジャンルを作成できること"""
        response = self.client.post("/api/v1/genres/", {"name": "Fiction"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Genre.objects.count(), 1)


class BookAPITest(APITestCase):
    """書籍API のテスト"""

    def setUp(self):
        self.genre = Genre.objects.create(name="Fiction")

    def test_list_books(self):
        """書籍一覧を取得できること"""
        Book.objects.create(
            isbn="9784123456789",
            title="Test Book",
            author="Test Author",
            publisher="Test Publisher",
            genre=self.genre,
            price=1500,
        )
        response = self.client.get("/api/v1/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_book(self):
        """書籍を作成できること"""
        response = self.client.post(
            "/api/v1/books/",
            {
                "isbn": "9784123456789",
                "title": "Test Book",
                "author": "Test Author",
                "publisher": "Test Publisher",
                "genre_id": self.genre.id,
                "price": 1500,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.count(), 1)
