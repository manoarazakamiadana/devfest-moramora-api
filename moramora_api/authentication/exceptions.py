from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data.get("detail")
    message = str(detail) if detail is not None else "Request validation failed."
    errors = None if detail is not None else response.data
    response.data = {
        "success": False,
        "message": message,
    }
    if errors is not None:
        response.data["errors"] = errors
    return response
