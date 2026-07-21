from django.urls import path,include
from farmer import views
from rest_framework.routers import DefaultRouter

router=DefaultRouter()
router.register('feedback',views.FeeedbackViewset,basename='feedback')
urlpatterns=[
    path('farmercollection',views.FarmerCollection.as_view()),
    path('dashboard',views.FarmerDashboard.as_view()),
    path('notices/',views.FarmerNoticeView.as_view()),
    path('',include(router.urls))
]