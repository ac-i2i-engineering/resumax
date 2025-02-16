import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.test import Client
from unittest.mock import patch

@pytest.fixture
def client():
    return Client()

@pytest.mark.django_db
@patch("requests.get")
def test_register_successful(mock_get, client):
    """
    Test successful registration with valid details.
    """
    response = client.post(reverse("register"), {
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe",
        "email": "johndoe@example.com",
        "password": "SecurePass123",
        "confirm-password": "SecurePass123"
    })

    assert response.status_code == 302  # Redirect to login on success
    assert User.objects.filter(username="johndoe").exists()

@pytest.mark.django_db
@patch("requests.get")
def test_register_existing_username(mock_get,client):
    """
    Test registration fails when the username already exists.
    """
    User.objects.create_user(username="johndoe", password="SecurePass123")

    response = client.post(reverse("register"), {
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe",
        "email": "newemail@example.com",
        "password": "SecurePass123",
        "confirm-password": "SecurePass123"
    })

    assert response.status_code == 302  # Redirects back to register page
    assert User.objects.filter(email="newemail@example.com").exists() is False

@pytest.mark.django_db
@patch("requests.get")
def test_register_password_mismatch(mock_get,client):
    """
    Test registration fails when passwords do not match.
    """
    response = client.post(reverse("register"), {
        "first_name": "Sam",
        "last_name": "Smith",
        "username": "samsmith",
        "email": "samsmith@example.com",
        "password": "SecurePass123",
        "confirm-password": "WrongPass"
    })

    assert response.status_code == 302  # Redirects back to register page
    assert User.objects.filter(username="samsmith").exists() is False

@pytest.mark.django_db
@patch("requests.get")
def test_register_short_password(mock_get,client):
    """
    Test registration fails when password is too short.
    """
    response = client.post(reverse("register"), {
        "first_name": "Alex",
        "last_name": "Brown",
        "username": "alexbrown",
        "email": "alexbrown@example.com",
        "password": "short",
        "confirm-password": "short"
    })

    assert response.status_code == 302  # Redirects back to register page
    assert User.objects.filter(username="alexbrown").exists() is False
