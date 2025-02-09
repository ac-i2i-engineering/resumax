from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.urls import reverse
from .models import *

def RegisterView(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        user_data_has_error = False

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            user_data_has_error = True

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            user_data_has_error = True

        if len(password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            user_data_has_error = True

        if user_data_has_error:
            return redirect('register')
        else:
            new_user = User.objects.create_user(
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
    if request.method == 'POST':
        # getting user inputs from frontend
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # authenticate credentials
        user = authenticate(request=request, username=username, password=password)
        if user is not None:
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

    logout(request)

    # redirect to login page after logout
    return redirect('login')

def ForgotPassword(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # create a new password reset id
            new_password_reset = PasswordReset(user=user)
            new_password_reset.save()
            # full_password_reset_url = request.build_absolute_uri(password_reset_url)
            password_reset_url = reverse('reset-password', kwargs={'reset_id':new_password_reset.reset_id})
            full_password_reset_url = f"{request.scheme}://{request.get_host()}{password_reset_url}"
            # send email to user
            email_subject = 'Password your Reset'
            template_name = "password_reset_email.html"
            context = {
                'full_password_reset_url':full_password_reset_url, 
                'username':user.username
            }
            convert_to_html_content = render_to_string(template_name=template_name, context=context)
            plain_message = strip_tags(convert_to_html_content)
            is_sent_successfully = send_mail(
              subject=email_subject,
              message=plain_message,
              from_email=settings.EMAIL_HOST_USER,
              recipient_list=[email,],   
              html_message=convert_to_html_content,
              fail_silently=True  
            )
            return redirect("password-reset-sent",reset_id=new_password_reset.reset_id)
        except User.DoesNotExist:
            messages.error(request, f"No user with email {email} found.")
            return redirect('forgot-password')
        
    return render(request, 'forgot_password.html')

def PasswordResetSent(request, reset_id):
    if PasswordReset.objects.filter(reset_id=reset_id).exists():
        return render(request, 'password_reset_sent.html')
    else:
        # redirect to forgot password page if code does not exist
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password')

def ResetPassword(request, reset_id):

    try:
        reset_id = PasswordReset.objects.get(reset_id=reset_id)
        if request.method == 'POST':
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

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
                messages.success(request, 'Password reset. Proceed to login')
                return redirect('login')

            else:
                # redirect back to password reset page and display errors
                return redirect('reset-password', reset_id=reset_id)
    except PasswordReset.DoesNotExist:
        
        # redirect to forgot password page if code does not exist
        messages.error(request, 'Invalid reset id')
        return redirect('forgot-password')

    return render(request, 'reset_password.html')