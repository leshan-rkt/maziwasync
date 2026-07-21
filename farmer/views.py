from django.shortcuts import render
from cooperative.serializers import NoticeSerializer
from core.models import FarmerProfile, Feedback, MilkCollection, Notice
from rest_framework import generics, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from collector.serializers import MilkCollectionSerializer
from farmer.serializers import FeedbackSerializer
from django.db.models import Sum
from datetime import date
from django.utils import timezone
from rest_framework.response import Response

# Create your views here.

# farmer dashboard 
class FarmerDashboard(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        farmer=self.request.user.farmer_profile
        collection=MilkCollection.objects.filter(farmer=farmer)
        total_collections=collection.count()
        total_litres=collection.aggregate(total=Sum('litres'))['total'] or 0
        total_amount=collection.aggregate(total=Sum('total_amount'))['total'] or 0

        today_collection=collection.filter(collection_date=date.today()).aggregate(total=Sum('litres'))['total'] or 0

        monthly_litres=collection.filter(
            collection_date__month=timezone.now().month
        ).aggregate(total=Sum('litres'))['total'] or 0

        monthly_earnings=collection.filter(
            collection_date__month=timezone.now().month
        ).aggregate(total=Sum('litres'))['total'] or 0

        return Response({
            'total_collections':total_collections,
            'total_litres':total_litres,
            'total_amount':total_amount,
            "today_collection":today_collection,
            'monthly_earnings':monthly_earnings,
            'monthly_litres':monthly_litres
        })
        

# farmers milk collection 
class FarmerCollection(generics.ListAPIView):
    serializer_class=MilkCollectionSerializer
    permission_classes=[IsAuthenticated]

    # queryset- we fetch data from the model in a class
    def get_queryset(self):
        try:
            farmer=self.request.user.farmer_profile
        except FarmerProfile.DoesNotExist:
            raise PermissionDenied(
                "Only farmers can access this endpoint"
            )
        collections=MilkCollection.objects.filter(farmer=farmer).select_related("porter").order_by("created_at")

        return collections
    
# feedback CRUD- viewsets
class FeeedbackViewset(viewsets.ModelViewSet):
    serializer_class=FeedbackSerializer
    permission_classes=[IsAuthenticated]
    def get_queryset(self):
        try:
            farmer= self.request.user.farmer_profile
        except:
            raise PermissionDenied("Only farmers can access this endpoint")
        feedback=(
            Feedback.objects
            .filter(farmer=farmer)
            .order_by('created_at')
        )
        return feedback
    
    # post by the farmer token
    def perform_create(self,serializer):
        try:
            farmer=self.request.user.farmer_profile
        except:
            raise PermissionDenied("Only farmers can create feedback")
        
        serializer.save(farmer=farmer)

# view notices
class FarmerNoticeView(generics.ListAPIView):
    serializer_class=NoticeSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        notices=(
            Notice.objects.filter(target__in=['ALL','FARMERS'])
            .order_by('created_at')
        )
        return notices
    