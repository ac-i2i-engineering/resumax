import pytest
from django.contrib.auth.models import User
from django.urls import reverse

INDEX_VIEW_NAME = 'home'
@pytest.mark.django_db
def test_login_required_redirect(client):
    """Test that an unauthenticated user is redirected to the login page."""
    response = client.get(reverse(INDEX_VIEW_NAME))  # Assuming 'home' is the URL name
    assert response.status_code == 302
    assert "/auth/login/" in response.url  # Default Django login redirect

@pytest.mark.django_db
def test_authenticated_user_access(client, django_user_model):
    """Test that an authenticated user can access the index view."""
    user = django_user_model.objects.create_user(username="testuser", password="password123")
    client.login(username="testuser", password="password123")  # Log in
    response = client.get(reverse(INDEX_VIEW_NAME))
    assert response.status_code == 200
    assert b'testuser' in response.content  # Checks if the username is in the response

