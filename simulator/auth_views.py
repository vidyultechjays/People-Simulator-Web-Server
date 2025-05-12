"""
Authentication views for the People Simulator application.
Includes a simple hardcoded login system and login_required decorator.
"""

from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse

# Hardcoded credential (in a real app, this would be in a database)
VALID_USERNAME = "admin"
VALID_PASSWORD = "simpass123"

def login_view(request):
    """
    Simple login view that validates against hardcoded credentials
    """
    # If user is already logged in, redirect to landing page
    if request.session.get('is_logged_in'):
        return redirect('landing_page')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Validate against hardcoded credentials
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            # Set session variables
            request.session['is_logged_in'] = True
            request.session['username'] = username
            
            # Redirect to the landing page or a next parameter if provided
            next_url = request.GET.get('next', 'landing_page')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'login.html')

def logout_view(request):
    """
    Simple logout view that clears the session
    """
    # Clear session variables
    request.session.flush()
    
    return render(request, 'logout.html')

def login_required(view_func):
    """
    Decorator for views that checks if the user is logged in.
    If not, redirects to the login page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('is_logged_in'):
            # Save the requested URL so we can redirect after login
            next_url = request.path
            login_url = f"{reverse('login')}?next={next_url}"
            return HttpResponseRedirect(login_url)
        return view_func(request, *args, **kwargs)
    return _wrapped_view 