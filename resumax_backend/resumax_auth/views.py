from django.contrib.auth import authenticate, login, logout
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
        user = User.objects.get(email=email)
        # check if the user exists
        if not user:
            messages.error(request, f"No user with email {email} found.")
            return redirect('forgot-password')            
        # create a new password reset id
        new_password_reset = PasswordReset(user=user)
        new_password_reset.save()
        password_reset_url = reverse('reset-password', kwargs={'reset_id':new_password_reset.reset_id})
        full_password_reset_url = f"{request.scheme}://{request.get_host()}{password_reset_url}"
        # send reset link email to the user for confirmation
        email_subject = 'Password your Reset'
        template_name = "password_reset_email.html"
        context = {
            'full_password_reset_url':full_password_reset_url, 
            'username':user.username
        }
        convert_to_html_content = render_to_string(template_name=template_name, context=context)
        plain_message = strip_tags(convert_to_html_content)
        send_mail(
          subject=email_subject,
          message=plain_message,
          from_email=settings.EMAIL_HOST_USER,
          recipient_list=[email,],   
          html_message=convert_to_html_content,
          fail_silently=True  
        )
        return redirect("password-reset-sent",reset_id=new_password_reset.reset_id)
       
    return render(request, 'forgot_password.html')

def PasswordResetSent(request, reset_id):
    '''
    PasswordResetSent function to notify the user if reset email sent
    '''
    if PasswordReset.objects.filter(reset_id=reset_id).exists():
        return render(request, 'password_reset_sent.html')
    # redirect to forgot password page if code does not exist
    messages.error(request, 'Invalid reset id')
    return redirect('forgot-password')

def ResetPassword(request, reset_id):
    '''
    ResetPassword function to handle verify user password and complete reset
    '''
    try:
        reset_id = PasswordReset.objects.get(reset_id=reset_id)
        if request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm-password')

            passwords_have_error = False

            if password != confirm_password:
                passwords_have_error = True
                messages.error(request, 'Passwords do not match')

            if len(password) < 8:
                passwords_have_error = True
                reset_id.delete()
                messages.error(request, 'Password must be at least 8 characters long')

            expiration_time = reset_id.creation_time + timezone.timedelta(minutes=30)

            if timezone.now() > expiration_time:
            
                # delete reset id if expired
                reset_id.delete()

                passwords_have_error = True
                messages.error(request, 'Reset link has expired')

            # reset password
            if not passwords_have_error:
                user = reset_id.user
                user.set_password(password)
                user.save()

                # delete reset id after use
                reset_id.delete()

                # redirect to login
                messages.success(request, 'Password reset, login to continue')
                return redirect('login')

            else:
                # redirect back to password reset page and display errors
                return redirect('reset-password', reset_id=reset_id)
    except PasswordReset.DoesNotExist:
        
        # redirect to forgot password page if code does not exist
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password')

    return render(request, 'reset_password.html')