from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.template.loader import render_to_string
from django.shortcuts import render, redirect
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from .models import *
import requests
import re

def RegisterView(request):
    '''
    RegisterView function to handle user registration.
    '''
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm-password")
        signup_data_has_error = False
        # check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            signup_data_has_error = True
        # check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            signup_data_has_error = True
        # check if password and confirm password match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            signup_data_has_error = True
        # check if password is at least 8 characters
        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            signup_data_has_error = True
        # if any error is found, redirect back to the register page
        if signup_data_has_error:
            return redirect('register')
        else:
            User.objects.create_user(
                first_name=first_name, 
                last_name=last_name, 
                username=username, 
                email=email, 
                password=password
                )
            messages.success(request, "Account created successfully. Login now")
            return redirect('login')
        
    return render(request, "register.html")


def LoginView(request):
    '''
    LoginView function to handle user login.
    '''
    if request.method == 'POST':
        # get user inputs from frontend
        username = request.POST.get('username')
        password = request.POST.get('password')
        # check is logging in with email
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(pattern,username):
            username = User.objects.get(email=username).username
        user = authenticate(request=request, username=username, password=password)
        # authenticate credentials
        if user:
            # login user if login credentials are correct
            login(request, user)

            # redirect to home page
            return redirect('home')
        else:
            # redirect back to the login page if credentials are wrong
            messages.error(request, 'Invalid username or password')
            return redirect('login')
    return render(request, "login.html")

def LogoutView(request):
    '''
    LogoutView function to handle user logout.
    '''
    logout(request)

    # redirect to login page after logout
    return redirect('login')

def ForgotPassword(request):
    '''
    ForgotPassword function to handle password reset requests.
    '''
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            
            # Delete any existing password reset tokens for this user
            PasswordReset.objects.filter(user=user).delete()
            
            # Create a new password reset token
            new_password_reset = PasswordReset(user=user)
            new_password_reset.save()
            
            # For development, just show the reset link in messages
            # In production, you would send this via email
            reset_url = reverse('reset-password', kwargs={'reset_id': new_password_reset.reset_id})
            full_reset_url = f"{request.scheme}://{request.get_host()}{reset_url}"
            
            # For now, show the reset link in a success message (development only)
            messages.success(
                request, 
                f"Password reset link: {full_reset_url} (Check your email in production)"
            )
            
            return redirect('password-reset-sent', reset_id=new_password_reset.reset_id)
            
        except User.DoesNotExist:
            # For security, don't reveal if email exists or not
            messages.success(
                request, 
                "If an account with that email exists, a password reset link has been sent."
            )
            return redirect('forgot-password')
    
    return render(request, 'forgot_password.html')

def PasswordResetSent(request, reset_id):
    '''
    PasswordResetSent function to show confirmation that reset email was sent
    '''
    try:
        # Verify the reset_id exists (but don't show it to user for security)
        PasswordReset.objects.get(reset_id=reset_id)
        return render(request, 'password_reset_sent.html')
    except PasswordReset.DoesNotExist:
        # Even if invalid, show the sent page for security
        # (Don't reveal whether the reset ID was valid or not)
        return render(request, 'password_reset_sent.html')

def ResetPassword(request, reset_id):
    '''
    ResetPassword function to handle password reset completion
    '''
    try:
        password_reset = PasswordReset.objects.get(reset_id=reset_id)
        
        # Check if reset link has expired (30 minutes)
        expiration_time = password_reset.creation_time + timezone.timedelta(minutes=30)
        if timezone.now() > expiration_time:
            password_reset.delete()
            messages.error(request, 'Reset link has expired. Please request a new one.')
            return redirect('forgot-password')
        
        if request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            # Validate passwords
            if password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'reset_password.html', {'reset_id': reset_id})
            
            if len(password) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return render(request, 'reset_password.html', {'reset_id': reset_id})
            
            # Reset password
            user = password_reset.user
            user.set_password(password)
            user.save()
            
            # Delete the reset token
            password_reset.delete()
            
            messages.success(request, 'Password reset successfully! You can now log in.')
            return redirect('login')
        
        # GET request - show the reset form
        return render(request, 'reset_password.html', {'reset_id': reset_id})
        
    except PasswordReset.DoesNotExist:
        messages.error(request, 'Invalid or expired reset link.')
        return redirect('forgot-password')

def ChangePassword(request):
    '''
    ChangePassword function to handle password changes for logged-in users.
    '''
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        # Validate current password
        if not request.user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change-password')
        
        # Validate new password
        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change-password')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
            return redirect('change-password')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Keep user logged in after password change
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Password changed successfully.')
        return redirect('home')  # or wherever you want to redirect
    
    return render(request, 'change_password.html')