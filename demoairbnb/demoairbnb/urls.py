from django.contrib import admin
from django.urls import include, path
from apps.core.views import PersonalizedTokenObtainPairView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", PersonalizedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/", include("apps.core.urls")),
    path("api/", include("apps.inventory.urls")),
    path("api/", include("apps.crm.urls")),
    path("api/", include("apps.booking.urls")),
    path("api/", include("apps.finance.urls")),
    path("api/", include("apps.channels.urls")),
]
