from django.http import JsonResponse

def routing_index(request):
    """Routing app index"""
    return JsonResponse({
        'message': 'Routing API',
        'version': '1.0',
        'status': 'Coming soon'
    })
