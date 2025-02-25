from rest_framework import serializers
from .models import Product, Cart, CartItem
from django.contrib.auth.models import AbstractUser, User
from django.contrib.auth import get_user_model
from core.models import CustomUser, Profile
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image", "description", "category", "price"]


class DetailedProductSerializer(serializers.ModelSerializer):
    similar_products = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "price", "slug", "image", "description", "similar_products"]

    def get_similar_products(self, product):
        products = Product.objects.filter(category=product.category).exclude(id=product.id)
        serializer = ProductSerializer(products, many=True)
        return serializer.data


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "quantity", "product", "total"]

    def get_total(self, cartitem):
        price = cartitem.product.price * cartitem.quantity
        return price


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(read_only=True, many=True)
    sum_total = serializers.SerializerMethodField()
    num_of_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "cart_code", "items", "sum_total", "num_of_items", "created_at", "modified_at"]

    def get_sum_total(self, cart):
        items = cart.items.all()
        total = sum([item.product.price * item.quantity for item in items])
        return total

    def get_num_of_items(self, cart):
        items = cart.items.all()
        total = sum([item.quantity for item in items])
        return total


class SimpleCartSerializer(serializers.ModelSerializer):

    num_of_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ["id", "cart_code", "num_of_items"]

    def get_num_of_items(self, cart):
        num_of_items = sum([item.quantity for item in cart.items.all()])
        return num_of_items


class NewCartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    order_id = serializers.SerializerMethodField()
    order_date = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "order_id", "order_date"]

    def get_order_id(self, cartitem):
        order_id = cartitem.cart.cart_code
        return order_id

    def get_order_date(self, cartitem):
        order_date = cartitem.cart.modified_at
        return order_date


class ProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = Profile
        fields = ["profile_pic", "verified"]


class UserSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ["id", "username", "first_name", "last_name", "email", "city", "state", "country", "address",
                  "address2", "phone", "items", "date_joined", "profile_pic"]

    def get_items(self, user):
        cartitems = CartItem.objects.filter(cart__user=user, cart__paid=True)[:10]
        serializer = NewCartItemSerializer(cartitems, many=True)
        return serializer.data

    def get_profile_pic(self, user):
        profile_pic = Profile.objects.get(user=user)
        serializer = ProfileSerializer(profile_pic)
        return serializer.data['profile_pic']

#  Destiny's guide codes


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ["username", "email", "password", "password2", "first_name", "last_name", "address", "address2",
                  "city", "state", "country", "phone"]

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields do not match⚠"}
            )
        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            address=validated_data['address'],
            address2=validated_data['address2'],
            city=validated_data['city'],
            state=validated_data['state'],
            country=validated_data['country'],
            phone=validated_data['phone']
        )

        user.set_password(validated_data['password'])
        user.save()

        return user


class ChangePasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    old_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('old_password', 'password', 'password2')

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError({"old_password": "Old password is not correct"})
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def update(self, instance, validated_data):
        user = self.context['request'].user
        user.set_password(validated_data['password'])
        user.save()

        return instance
    

class UpdateUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    profile_pic = serializers.ImageField(source='profile.profile_pic', required=False)

    class Meta:
        model = CustomUser
        fields = ("username", "email", "first_name", "last_name", "address", "address2", "city", "state",
                  "country", "phone", "profile_pic")
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate_email(self, value):
        user = self.context['request'].user
        if CustomUser.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError({"email": "This email is already in use."})
        return value

    def validate_username(self, value):
        user = self.context['request'].user
        if CustomUser.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError({"username": "This username is already in use."})
        return value

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.username = validated_data.get('username', instance.username)
        instance.address = validated_data.get('address', instance.address)
        instance.address2 = validated_data.get('address2', instance.address2)
        instance.city = validated_data.get('city', instance.city)
        instance.state = validated_data.get('state', instance.state)
        instance.country = validated_data.get('country', instance.country)
        instance.phone = validated_data.get('phone', instance.phone)

        profile_pic = self.context.get('request').FILES.get('profile_pic')
        profile = instance.profile
        if profile_pic:
            profile.profile_pic = profile_pic
        profile.save()

        instance.save()
        return instance


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ("email",)

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            return value
        else:
            raise serializers.ValidationError({"email": "This email does not exist."})


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.RegexField(
        regex=r'^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
        write_only=True,
        error_messages={'invalid': 'Password must be at least 8 characters long with at least one capital letter and symbol'})

    confirm_password = serializers.CharField(write_only=True, required=True)

