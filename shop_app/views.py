from django.shortcuts import render
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Product, Cart, CartItem, Transaction, Invoice
from core.models import CustomUser, Profile, PasswordReset
from .serializers import (ProductSerializer, CartSerializer, DetailedProductSerializer, UserSerializer,
                          CartItemSerializer, SimpleCartSerializer, RegisterSerializer, ChangePasswordSerializer,
                          UpdateUserSerializer, ResetPasswordRequestSerializer, ResetPasswordSerializer)
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status

from django.core.mail import send_mail

from django.contrib.auth.tokens import PasswordResetTokenGenerator

from rest_framework.exceptions import ValidationError

from decimal import Decimal
import uuid
import requests
from django.conf import settings
import paypalrestsdk

import os
from django.conf import settings
from django.http import JsonResponse


# Create your views here.

BASE_URL = settings.REACT_BASE_URL

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # 'sandbox' or 'live'
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})


@api_view(["GET"])
def products(request):
    paginator = PageNumberPagination()
    paginator.page_size = 12  # Number of products per page
    products = Product.objects.all()

    # Filtering by category
    category = request.query_params.get('category', None)
    if category:
        products = products.filter(category__icontains=category)

    # Filtering by name
    name = request.query_params.get('search', None)
    if name:
        products = products.filter(name__icontains=name)

    result_page = paginator.paginate_queryset(products, request)
    serializer = ProductSerializer(result_page, many=True)

    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
def product_detail(request, slug):
    product = Product.objects.get(slug=slug)

    similar_products = Product.objects.filter(category=product.category).exclude(id=product.id)

    paginator = PageNumberPagination()
    paginator.page_size = 8

    paginated_similar_products = paginator.paginate_queryset(similar_products, request)

    serializer = DetailedProductSerializer(product)
    related_serializer = ProductSerializer(paginated_similar_products, many=True)

    return paginator.get_paginated_response({
        "product": serializer.data,
        "similar_products": related_serializer.data,
    })


@api_view(["POST"])
def add_item(request):
    try:
        cart_code = request.data.get("cart_code")
        product_id = request.data.get("product_id")

        cart, created = Cart.objects.get_or_create(cart_code=cart_code)
        product = Product.objects.get(id=product_id)

        cartitem, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cartitem.quantity = 1
        cartitem.save()

        serializer = CartItemSerializer(cartitem)

        return Response({"data": serializer.data, "message": "Cart item created successfully"}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(["GET"])
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")

    cart = Cart.objects.get(cart_code=cart_code)
    product = Product.objects.get(id=product_id)

    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()

    return Response({'product_in_cart': product_exists_in_cart})


@api_view(["GET"])
def get_cart_stat(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = SimpleCartSerializer(cart)

    return Response(serializer.data)


@api_view(["GET"])
def get_cart(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = CartSerializer(cart)

    return Response(serializer.data)


@api_view(["PATCH"])
def update_quantity(request):
    try:
        cartitem_id = request.data.get("item_id")
        quantity = request.data.get("quantity")
        quantity = int(quantity)
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()
        serializer  = CartItemSerializer(cartitem)
        return Response({"data":serializer.data, "message": "Cart item updated successfully!"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


@api_view(['POST'])
def delete_cartitem(request):
    cartitem_id = request.data.get("item_id")
    cartitem = CartItem.objects.get(id=cartitem_id)
    cartitem.delete()
    return Response({"message": "Item deleted successfully!"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_username(request):
    user = request.user
    return Response({"username": user.username})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_id(request):
    user = request.user
    return Response({"id": user.id})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)


@api_view(["POST"])
def initiate_payment(request):
    if request.user:
        try:
            # Generate a unique transaction reference

            tx_ref = str(uuid.uuid4())
            cart_code = request.data.get("cart_code")
            cart = Cart.objects.get(cart_code=cart_code)
            user = request.user

            amount = sum([item.quantity * item.product.price for item in cart.items.all()])
            delivery = Decimal("2400.00")
            total_amount = amount + delivery
            currency = "NGN"
            redirect_url = f"{BASE_URL}/payment-status"

            transaction = Transaction.objects.create(
                ref=tx_ref,
                cart=cart,
                amount=total_amount,
                currency=currency,
                user=user,
                status='pending'
            )

            flutterwave_payload = {
                "tx_ref": tx_ref,
                "amount": str(total_amount),  # Convert to string
                "currency": currency,
                "redirect_url": redirect_url,
                "customer": {
                    "email": user.email,
                    "name": user.username,
                    "phonenumber": user.phone
                },
                "customizations": {
                    "title": "Stud-and-Shine Payment"
                }
            }

            # Set up the headers for the request

            headers = {
                "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
                "Content-Type": "application/json"
            }

            # Make the API request to flutterwave
            response = requests.post(
                "https://api.flutterwave.com/v3/payments",
                json=flutterwave_payload,
                headers=headers
            )

            # Check if the request was successful

            if response.status_code == 200:
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                return Response(response.json(), status=response.status_code)

        except requests.exceptions.RequestException as e:
            # Log the error and return an error response
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def payment_callback(request):
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')

    user = request.user

    if status == 'successful':
        #  Verify the transaction using Flutterwave's api
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
        }

        response = requests.get(f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify", headers=headers)
        response_data = response.json()

        if response_data['status'] == 'success':
            transaction = Transaction.objects.get(ref=tx_ref)

            #  Confirm the transaction details
            if (response_data['data']['status'] == "successful"
                    and float(response_data['data']['amount']) == float(transaction.amount)
                    and response_data['data']['currency'] == transaction.currency):
                #  Update transaction and cart status to paid
                transaction.status = 'completed'
                transaction.save()

                cart = transaction.cart
                cart.paid = True
                cart.user = user
                cart.save()

                return Response({'message': 'Payment Successful!', 'subMessage': 'You have successfully made payment for your the items you purchased 😍'})
            else:
                #  Payment verification failed
                return Response({'message': 'Payment verification failed.', 'subMessage': 'Your payment verification...'})
        else:
            return Response({'message': 'Failed to verify transaction with Flutterwave.', 'subMessage': 'We could...'})
    else:
        #  Payment was not successful
        return Response({'message': 'Payment was not successful.'}, status=400)


@api_view(["POST"])
def initiate_paypal_payment(request):
    if request.method == 'POST' and request.user.is_authenticated:
        # Fetch the cart and calculate total amount
        tx_ref = str(uuid.uuid4())
        user = request.user
        cart_code = request.data.get("cart_code")
        cart = Cart.objects.get(cart_code=cart_code)
        amount = sum(item.product.price * item.quantity for item in cart.items.all())
        delivery = Decimal("2400.00")
        total_amount = amount + delivery

        # Create a paypal payment object

        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                # Use a single redirect url for both success and cancel
                "return_url": f"{BASE_URL}/payment-status?paymentStatus=success&ref={tx_ref}",
                "cancel_url": f"{BASE_URL}/payment-status?paymentStatus=cancel"
            },
            "transactions": [{
                "items_list": {
                    "items": [{
                        "name": "Cart Items",
                        "sku": "cart",
                        "price": str(total_amount),
                        "currency": "USD",
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": str(total_amount),
                    "currency": "USD"
                },
                "description": "Payment for cart items"
            }]
        })

        print("pay_id", payment)

        transaction, created = Transaction.objects.get_or_create(
            ref=tx_ref,
            cart=cart,
            amount=total_amount,
            user=user,
            status='pending'
        )

        if payment.create():
            # print(payment.links)
            # Extract paypal approval URL to redirect the user
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = str(link.href)
                    return Response({"approval_url": approval_url})

        else:
            return Response({"error": payment.error}, status=400)

    return Response({'error': "Invalid reuest"}, status=400)


@api_view(['POST'])
def paypal_payment_callback(request):
    payment_id = request.query_params.get('paymentId')
    payer_id = request.query_params.get('PayerID')
    ref = request.query_params.get('ref')

    user = request.user

    print("refff", ref)

    transaction = Transaction.objects.get(ref=ref)

    if payment_id and payer_id:
        # Fetch payment object using PayPal SDK
        payment = paypalrestsdk.Payment.find(payment_id)

        transaction.status = 'completed'
        transaction.save()
        cart = transaction.cart
        cart.paid = True
        cart.user = user
        cart.save()

        return Response({'message': 'Payment successful!', 'subMessage': 'You have successfully made payment for the items you purchased 😍'})

    else:
        return Response({'error': "Invalid payment details."}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_invoice(request):
    try:
        invoice_ref = str(uuid.uuid4())
        cart_code = request.data.get("cart_code")
        cart = Cart.objects.get(cart_code=cart_code)
        user = request.user

        subtotal = sum([item.quantity * item.product.price for item in cart.items.all()])
        tax = Decimal("600.00")
        delivery_fee = Decimal("2400.00")
        total_amount = subtotal + tax + delivery_fee
        currency = "NGN"

        invoice = Invoice.objects.create(
            ref=invoice_ref,
            cart=cart,
            subtotal=subtotal,
            tax=tax,
            delivery_fee=delivery_fee,
            total_amount=total_amount,
            currency=currency,
            user=user,
            status="pending"
        )

        # Return the URL in a JSON response
        invoice_url = f"{BASE_URL}/invoice_page/{invoice_ref}"
        return Response({'success': True, 'invoice_link': invoice_url}, status=status.HTTP_200_OK)

    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_invoice(request, invoice_ref):
    try:
        invoice = Invoice.objects.get(ref=invoice_ref, user=request.user)

        # Format invoice payload for frontend consumption
        invoice_payload = {
            "invoice_ref": invoice.ref,
            "subtotal": str(invoice.subtotal),
            "tax": str(invoice.tax),
            "delivery_fee": str(invoice.delivery_fee),
            "total_amount": str(invoice.total_amount),
            "currency": invoice.currency,
            "status": invoice.status,
            "customer": {
                "email": invoice.user.email,
                "name": invoice.user.username,
                "phonenumber": invoice.user.phone
            },
            "details": [
                {
                    "product": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": str(item.product.price),
                    "total_price": str(item.quantity * item.product.price)
                } for item in invoice.cart.items.all()
            ]
        }

        return Response(invoice_payload, status=status.HTTP_200_OK)

    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_payment(request):
    try:
        user = request.user  # Ensure the authenticated user is used
        cart_code = request.data.get("cart_code")
        invoice_ref = request.data.get("invoice_ref")

        # Validate that the invoice belongs to the logged-in user
        invoice = Invoice.objects.get(ref=invoice_ref, user=user)
        if invoice.status == "paid":
            return Response({"error": "Invoice already marked as paid"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            invoice.status = "paid"
            invoice.save()

            # Validate that the cart belongs to the logged-in user
            cart = Cart.objects.get(cart_code=cart_code, paid=False)
            cart.paid = True
            cart.user = user
            cart.save()

        return Response({'message': 'Payment completed!', "status": invoice.status, "ref": invoice_ref}, status=status.HTTP_200_OK)

    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found or already paid'}, status=status.HTTP_404_NOT_FOUND)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_invoice(request):
    try:
        user = request.user  # Ensure the authenticated user is used
        cart_code = request.data.get("cart_code")
        invoice_ref = request.data.get("invoice_ref")

        invoice = Invoice.objects.get(ref=invoice_ref, user=user)

        invoice.status = "cancelled"
        invoice.save()
        print("Checkpoint")
        cart = Cart.objects.get(cart_code=cart_code)
        cart.paid = False
        cart.save()
        return Response({'message': 'Payment cancelled.', 'subMessage': 'You have cancelled the payent for this invoice. If you wish to continue with this payment, use the navigation button and go back to the generated invoice, make the payment and then click on "I have made the payment".', "status": invoice.status, "ref": invoice_ref})

    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def completed_page(request):
    status = request.query_params.get('status')
    ref = request.query_params.get('ref')

    if ref and status:

        return Response({'message': 'Payment completed!', 'subMessage': 'You have completed the payment process for the items you purchased 😍'})

    else:
        return Response({'error': "Invalid payment details."}, status=400)


@api_view(['POST'])
def cancelled_page(request):
    status = request.query_params.get('status')
    ref = request.query_params.get('ref')

    if ref and status:

        return Response({'message': 'Payment cancelled.', 'subMessage': 'You have cancelled the payent for this invoice. If you wish to continue with this payment, use the navigation button and go back to the generated invoice, make the payment and then click on "I have made the payment".', "status": status, "ref": ref})

    else:
        return Response({'error': "Invalid action, try again."}, status=400)


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': 'User registered successfully'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer
    lookup_field = 'pk'
    lookup_url_kwarg = 'id'


class UpdateProfileView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = UpdateUserSerializer

    def get_object(self):
        # Get the specific user profile based on the provided pk
        pk = self.kwargs.get("pk")
        try:
            return CustomUser.objects.get(pk=pk)
        except CustomUser.DoesNotExist:
            raise ValidationError("User profile not found")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        if 'profile_pic' in request.data and isinstance(request.data['profile_pic'], str):
            raise ValidationError("The submitted data was not a file. Check the encoding type on the form.")

        try:
            updated_profile = serializer.save()
        except AssertionError as e:
            # Log the error or handle it as needed
            print(f"AssertionError: {str(e)}")
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(UpdateUserSerializer(updated_profile).data)


    # lookup_field = 'pk'


class RequestPasswordReset(generics.GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)  # This validates the input data
        email = serializer.validated_data['email']  # Access validated email data

        user = CustomUser.objects.filter(email__iexact=email).first()

        if user:
            token_generator = PasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            reset = PasswordReset(email=email, token=token)
            reset.save()

            reset_url = f"{os.environ['PASSWORD_RESET_BASE_URL']}/{token}"

            # Sending reset link via email (commented out for clarity)
            send_mail(
                subject='Password Reset Request',
                message=f'Click the link to reset your password: {reset_url}',
                from_email=os.environ['DEFAULT_FROM_EMAIL'],
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({'success': 'We have sent you a link to reset your password'}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "User with credentials not found"}, status=status.HTTP_404_NOT_FOUND)


class ResetPassword(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = []

    def post(self, request, token):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_password = data['new_password']
        confirm_password = data['confirm_password']

        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=400)

        reset_obj = PasswordReset.objects.filter(token=token).first()

        if not reset_obj:
            return Response({'error': 'Invalid token'}, status=400)

        user = CustomUser.objects.filter(email=reset_obj.email).first()

        if user:
            user.set_password(request.data['new_password'])
            user.save()

            reset_obj.delete()

            return Response({'success': 'Password updated'})
        else:
            return Response({'error': 'No user found'}, status=404)


def send_test_email(request,):
    if request.method == 'POST':
        message = request.POST['message']
        email = request.POST['email']
        name = request.POST['name']
        send_mail(
            name,  # title
            message,  # title
            'settings.EMAIL_HOST_USER',
            (email,), fail_silently=False
        )
    return render(request, 'test_message.html')

