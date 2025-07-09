from django.urls import path
from . import views


urlpatterns = [
    path("products", views.products, name="products"),
    path("products/", views.products, name="search-list"),
    path("product_detail/<slug:slug>", views.product_detail, name="product_detail"),
    path("add_item/", views.add_item, name="add_item"),
    path("product_in_cart", views.product_in_cart, name="product_in_cart"),
    path("get_cart_stat", views.get_cart_stat, name="get_cart_stat"),
    path("get_cart", views.get_cart, name="get_cart"),
    path("update_quantity/", views.update_quantity, name="update_quantity"),
    path("delete_cartitem/", views.delete_cartitem, name="delete_cartitem"),
    path("get_username", views.get_username, name="get_username"),
    path("get_user_id", views.get_user_id, name="get_user_id"),
    path("user_info", views.user_info, name="user_info"),
    path("initiate_payment/", views.initiate_payment, name="initiate_payment"),
    path("payment_callback/", views.payment_callback, name="payment_callback"),
    path("initiate_paypal_payment/", views.initiate_paypal_payment, name="initiate_paypal_payment"),
    path("paypal_payment_callback/", views.paypal_payment_callback, name="paypal_payment_callback"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path('update_profile/<int:pk>/', views.UpdateProfileView.as_view(), name='update_profile'),
    path('change_password/<int:id>/', views.ChangePasswordView.as_view(), name='change_password'),
    path('request_password_reset/', views.RequestPasswordReset.as_view(), name='request_password_reset'),
    path('reset_password/<str:token>', views.ResetPassword.as_view(), name='reset_password'),
    path('get_invoice/<str:invoice_ref>', views.get_invoice, name='get_invoice'),
    path('generate_invoice/', views.generate_invoice, name='generate_invoice'),
    path('confirm_payment/', views.confirm_payment, name='confirm_payment'),
    path('cancel_invoice/', views.cancel_invoice, name='cancel_invoice'),
    path('completed_page/', views.completed_page, name='completed_page'),
    path('cancelled_page/', views.cancelled_page, name='cancelled_page'),
]

# fetching all_products: http://127.0.0.1:8001/products/

