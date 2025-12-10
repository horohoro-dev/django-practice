"""
在庫管理システムのモデル定義
"""

from django.db import models


class TransactionType(models.TextChoices):
    """在庫変動の種類"""

    ARRIVAL = "ARRIVAL", "Arrival"  # 入荷
    SALE = "SALE", "Sale"  # 販売
    LOSS = "LOSS", "Loss"  # 紛失
    THEFT = "THEFT", "Theft"  # 万引き


class Genre(models.Model):
    """ジャンル"""

    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    """書籍"""

    isbn = models.CharField(max_length=13, unique=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    genre = models.ForeignKey(Genre, on_delete=models.PROTECT, related_name="books")
    price = models.PositiveIntegerField()  # 税込価格
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Inventory(models.Model):
    """在庫"""

    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.book.title}: {self.quantity}"


class InventoryTransaction(models.Model):
    """在庫変動履歴"""

    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity = models.PositiveIntegerField()  # 常に正の値
    reason = models.TextField(blank=True, default="")  # 紛失・万引き時の詳細
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.inventory.book.title}: {self.transaction_type} {self.quantity}"


class Sale(models.Model):
    """売上"""

    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="sales")
    quantity = models.PositiveIntegerField()
    unit_price = models.PositiveIntegerField()  # 販売時点の価格を記録
    sold_at = models.DateTimeField()  # 実際の販売日時
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.book.title} x {self.quantity}"
