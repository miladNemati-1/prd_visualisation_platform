from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def iupac_charts(request):
    return render(request, "graph.html")



# @login_required
# def home(request):
#     return render(request, "home.html")