"""
API シリアライザ定義
"""

from rest_framework import serializers

from .models import Genre, Book, Inventory, InventoryTransaction, Sale


class GenreSerializer(serializers.ModelSerializer):
    """ジャンルシリアライザ"""

    class Meta:
        model = Genre
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class BookSerializer(serializers.ModelSerializer):
    """書籍シリアライザ（読み取り用）"""

    genre = GenreSerializer(read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "isbn",
            "title",
            "author",
            "publisher",
            "genre",
            "price",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class BookCreateSerializer(serializers.ModelSerializer):
    """書籍シリアライザ（作成用）"""

    genre_id = serializers.PrimaryKeyRelatedField(
        queryset=Genre.objects.all(), source="genre"
    )

    class Meta:
        model = Book
        fields = [
            "id",
            "isbn",
            "title",
            "author",
            "publisher",
            "genre_id",
            "price",
        ]
        read_only_fields = ["id"]


class InventorySerializer(serializers.ModelSerializer):
    """在庫シリアライザ"""

    book = BookSerializer(read_only=True)

    class Meta:
        model = Inventory
        fields = ["id", "book", "quantity", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class ArrivalSerializer(serializers.Serializer):
    """入荷登録シリアライザ"""

    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class InventoryAdjustmentSerializer(serializers.Serializer):
    """在庫調整シリアライザ（紛失・万引き用）"""

    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    transaction_type = serializers.ChoiceField(choices=["LOSS", "THEFT"])
    quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField()

    def validate_reason(self, value):
        """理由が空でないことを確認"""
        if not value.strip():
            raise serializers.ValidationError("Reason is required for loss/theft.")
        return value

    def validate(self, data):
        """在庫数を超えていないか確認"""
        book = data["book_id"]
        try:
            inventory = Inventory.objects.get(book=book)
            if inventory.quantity < data["quantity"]:
                raise serializers.ValidationError(
                    {"quantity": "Cannot exceed current inventory quantity."}
                )
        except Inventory.DoesNotExist:
            raise serializers.ValidationError({"book_id": "No inventory found for this book."})
        return data


class SaleCreateSerializer(serializers.Serializer):
    """売上記録シリアライザ"""

    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    sold_at = serializers.DateTimeField()

    def validate(self, data):
        """在庫数を超えていないか確認"""
        book = data["book_id"]
        try:
            inventory = Inventory.objects.get(book=book)
            if inventory.quantity < data["quantity"]:
                raise serializers.ValidationError(
                    {"quantity": "Cannot exceed current inventory quantity."}
                )
        except Inventory.DoesNotExist:
            raise serializers.ValidationError({"book_id": "No inventory found for this book."})
        return data


class TopSalesSerializer(serializers.Serializer):
    """売上上位シリアライザ"""

    book_id = serializers.IntegerField()
    title = serializers.CharField(source="book__title")
    author = serializers.CharField(source="book__author")
    total_quantity = serializers.IntegerField()


class InventoryTransactionSerializer(serializers.ModelSerializer):
    """在庫変動履歴シリアライザ"""

    class Meta:
        model = InventoryTransaction
        fields = ["id", "inventory", "transaction_type", "quantity", "reason", "created_at"]
        read_only_fields = ["id", "created_at"]
