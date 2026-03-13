from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("product/<uuid:pk>/", views.product_detail, name="product_detail"),
    path("login/", views.user_login, name="login"),
    path("register/", views.register, name="register"),
    path("logout/", views.user_logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("hardware/add-product/", views.add_product, name="add_product"),
    path(
        "hardware/order/<int:order_id>/<str:action>/",
        views.manage_order,
        name="manage_order",
    ),
    path(
        "hardware/product/<uuid:product_id>/delete/",
        views.delete_product,
        name="delete_product",
    ),
    path("manage/", views.manage_page, name="manage_page"),
    path("checkout/", views.checkout, name="checkout"),
    path(
        "payment/initiate/<int:order_id>/",
        views.initiate_payment,
        name="initiate_payment",
    ),
    path(
        "payment/status/<uuid:payment_id>/", views.payment_status, name="payment_status"
    ),
    path("map/", views.map_view, name="map_view"),
]
