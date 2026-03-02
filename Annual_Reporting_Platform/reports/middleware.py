import time

class TimeMiddleware:
    def __init__(self,get_response):
        self.get_response = get_response

    def __call__(self,request):
        start = time.time()
        response = self.get_response(request)
        duration = time.time() - start
        print(f"Response took {duration:.2f} seconds to get completed")
        return response