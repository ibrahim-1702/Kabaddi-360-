"""
CORS Middleware for Django
Handles Cross-Origin Resource Sharing for frontend integration
"""

class CorsMiddleware:
    """
    Simple CORS middleware to allow cross-origin requests
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            from django.http import HttpResponse
            response = HttpResponse()
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response['Access-Control-Max-Age'] = '3600'
            return response
        
        # Process normal request
        response = self.get_response(request)
        
        # Add CORS headers to response
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
