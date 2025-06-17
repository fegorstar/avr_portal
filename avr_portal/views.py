from django.shortcuts import render
from django.http import HttpResponse


def handle_not_found(request, exception):
    return render(request, '404.html')

