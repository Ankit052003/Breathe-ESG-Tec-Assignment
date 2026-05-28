from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def root_view(request):
    return JsonResponse(
        {
            "status": "ok",
            "message": "Breathe ESG API is running.",
            "health": "/api/health/",
        }
    )


urlpatterns = [
    path("", root_view, name="root"),
    path("admin/", admin.site.urls),
    path("api/", include("review.urls")),
]
