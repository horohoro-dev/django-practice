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

    name = models.CharField(max_length=100, unique=True, help_text="ジャンル名")
    created_at = models.DateTimeField(auto_now_add=True, help_text="作成日時")

    def __str__(self):
        return self.name


class Book(models.Model):
    """書籍"""

    isbn = models.CharField(max_length=13, unique=True, help_text="ISBN（13桁）")
    title = models.CharField(max_length=255, help_text="書籍タイトル")
    author = models.CharField(max_length=255, help_text="著者名")
    publisher = models.CharField(max_length=255, help_text="出版社名")
    genre = models.ForeignKey(
        Genre,
        on_delete=models.PROTECT,
        related_name="books",
        help_text="ジャンル",
    )
    price = models.PositiveIntegerField(help_text="税込価格（円）")
    created_at = models.DateTimeField(auto_now_add=True, help_text="作成日時")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新日時")

    def __str__(self):
        return self.title


class Inventory(models.Model):
    """在庫"""

    book = models.OneToOneField(
        Book,
        on_delete=models.CASCADE,
        related_name="inventory",
        help_text="書籍",
    )
    quantity = models.PositiveIntegerField(default=0, help_text="在庫数")
    updated_at = models.DateTimeField(auto_now=True, help_text="更新日時")

    def __str__(self):
        return f"{self.book.title}: {self.quantity}"


class InventoryTransaction(models.Model):
    """在庫変動履歴"""

    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="transactions",
        help_text="在庫",
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        help_text="取引種別（入荷/販売/紛失/万引き）",
    )
    quantity = models.PositiveIntegerField(help_text="数量（常に正の値）")
    reason = models.TextField(
        blank=True, default="", help_text="理由（紛失・万引き時の詳細）"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="作成日時")

    def __str__(self):
        return f"{self.inventory.book.title}: {self.transaction_type} {self.quantity}"


class Sale(models.Model):
    """売上"""

    book = models.ForeignKey(
        Book,
        on_delete=models.PROTECT,
        related_name="sales",
        help_text="書籍",
    )
    quantity = models.PositiveIntegerField(help_text="販売数量")
    unit_price = models.PositiveIntegerField(help_text="販売時点の単価（円）")
    sold_at = models.DateTimeField(help_text="販売日時")
    created_at = models.DateTimeField(auto_now_add=True, help_text="作成日時")

    def __str__(self):
        return f"{self.book.title} x {self.quantity}"
