"""
inventory アプリの URL 設定
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GenreViewSet,
    BookViewSet,
    InventoryViewSet,
    ArrivalView,
    InventoryAdjustmentView,
    SaleView,
    TopSalesView,
    TopSalesByGenreView,
)

router = DefaultRouter()
router.register(r"genres", GenreViewSet)
router.register(r"books", BookViewSet)
router.register(r"inventory", InventoryViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("arrivals/", ArrivalView.as_view(), name="arrivals"),
    path("inventory-adjustments/", InventoryAdjustmentView.as_view(), name="inventory-adjustments"),
    path("sales/", SaleView.as_view(), name="sales"),
    path("sales/top/", TopSalesView.as_view(), name="sales-top"),
    path("sales/top/by-genre/", TopSalesByGenreView.as_view(), name="sales-top-by-genre"),
]
