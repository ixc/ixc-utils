from .time import wait_for_time_sync


class TimeSyncMiddleware:
    """
    If the value from `time.time()` and the PTP device differ, wait
    for the fly.io automation to bring them into synchronisation
    before processing the request.
    See https://github.com/ixc/ixc-tech/issues/212
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        wait_for_time_sync()
        response = self.get_response(request)
        return response
