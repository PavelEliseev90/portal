from django.shortcuts import render

# Create your views here.
def asp(request):
    
    params = {
        'type'          : 'asp'
    }
    
    return render(request, "asp/asp.html", {'params': params})  