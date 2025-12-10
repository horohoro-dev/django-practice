"""
API ビュー定義
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Genre, Book, Inventory, InventoryTransaction, TransactionType, Sale
from .serializers import (
    GenreSerializer,
    BookSerializer,
    BookCreateSerializer,
    InventorySerializer,
    ArrivalSerializer,
    InventoryAdjustmentSerializer,
    SaleCreateSerializer,
)

# 期間のマッピング
PERIOD_MAPPING = {
    "1w": timedelta(weeks=1),
    "1m": timedelta(days=30),
    "3m": timedelta(days=90),
    "6m": timedelta(days=180),
    "1y": timedelta(days=365),
    "5y": timedelta(days=365 * 5),
    "all": None,
}


class GenreViewSet(viewsets.ModelViewSet):
    """ジャンル API"""

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class BookViewSet(viewsets.ModelViewSet):
    """書籍 API"""

    queryset = Book.objects.all()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return BookCreateSerializer
        return BookSerializer


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """在庫 API（読み取り専用）"""

    queryset = Inventory.objects.select_related("book", "book__genre").all()
    serializer_class = InventorySerializer


class ArrivalView(APIView):
    """入荷登録 API"""

    @transaction.atomic
    def post(self, request):
        serializer = ArrivalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book = serializer.validated_data["book_id"]
        quantity = serializer.validated_data["quantity"]

        # 在庫を取得または作成
        inventory, _ = Inventory.objects.get_or_create(book=book, defaults={"quantity": 0})
        inventory.quantity += quantity
        inventory.save()

        # 在庫変動履歴を作成
        InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type=TransactionType.ARRIVAL,
            quantity=quantity,
        )

        return Response(
            InventorySerializer(inventory).data,
            status=status.HTTP_201_CREATED,
        )


class InventoryAdjustmentView(APIView):
    """在庫調整 API（紛失・万引き）"""

    @transaction.atomic
    def post(self, request):
        serializer = InventoryAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book = serializer.validated_data["book_id"]
        tx_type = serializer.validated_data["transaction_type"]
        quantity = serializer.validated_data["quantity"]
        reason = serializer.validated_data["reason"]

        inventory = Inventory.objects.get(book=book)
        inventory.quantity -= quantity
        inventory.save()

        # 在庫変動履歴を作成
        InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type=tx_type,
            quantity=quantity,
            reason=reason,
        )

        return Response(
            {
                "id": inventory.id,
                "book": BookSerializer(book).data,
                "transaction_type": tx_type,
                "quantity": quantity,
                "reason": reason,
                "inventory_after": inventory.quantity,
            },
            status=status.HTTP_201_CREATED,
        )


class SaleView(APIView):
    """売上記録 API"""

    @transaction.atomic
    def post(self, request):
        serializer = SaleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book = serializer.validated_data["book_id"]
        quantity = serializer.validated_data["quantity"]
        sold_at = serializer.validated_data["sold_at"]

        # 売上を記録
        sale = Sale.objects.create(
            book=book,
            quantity=quantity,
            unit_price=book.price,
            sold_at=sold_at,
        )

        # 在庫を更新
        inventory = Inventory.objects.get(book=book)
        inventory.quantity -= quantity
        inventory.save()

        # 在庫変動履歴を作成
        InventoryTransaction.objects.create(
            inventory=inventory,
            transaction_type=TransactionType.SALE,
            quantity=quantity,
        )

        return Response(
            {
                "id": sale.id,
                "book": BookSerializer(book).data,
                "quantity": quantity,
                "unit_price": sale.unit_price,
                "sold_at": sold_at,
            },
            status=status.HTTP_201_CREATED,
        )


class TopSalesView(APIView):
    """売上上位 API"""

    def get(self, request):
        period = request.query_params.get("period")
        if not period or period not in PERIOD_MAPPING:
            return Response(
                {"error": "Valid period parameter is required (1w, 1m, 3m, 6m, 1y, 5y, all)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = int(request.query_params.get("limit", 10))
        delta = PERIOD_MAPPING[period]

        queryset = Sale.objects.all()
        if delta:
            start_date = timezone.now() - delta
            queryset = queryset.filter(sold_at__gte=start_date)

        top_sales = (
            queryset.values("book_id", "book__title", "book__author")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("-total_quantity")[:limit]
        )

        return Response(list(top_sales))


class TopSalesByGenreView(APIView):
    """ジャンル別売上上位 API"""

    def get(self, request):
        period = request.query_params.get("period")
        genre_id = request.query_params.get("genre_id")

        if not period or period not in PERIOD_MAPPING:
            return Response(
                {"error": "Valid period parameter is required (1w, 1m, 3m, 6m, 1y, 5y, all)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not genre_id:
            return Response(
                {"error": "genre_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = int(request.query_params.get("limit", 10))
        delta = PERIOD_MAPPING[period]

        queryset = Sale.objects.filter(book__genre_id=genre_id)
        if delta:
            start_date = timezone.now() - delta
            queryset = queryset.filter(sold_at__gte=start_date)

        top_sales = (
            queryset.values("book_id", "book__title", "book__author")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("-total_quantity")[:limit]
        )

        return Response(list(top_sales))
