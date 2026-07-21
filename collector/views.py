from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from django.shortcuts import render
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from collector.serializers import MilkCollectionSerializer, RecentCollectionsSerializer
from cooperative.serializers import NoticeSerializer
from core.models import Notice, PorterProfile , FarmerProfile, MilkCollection
from rest_framework.response import Response
from rest_framework import generics
# Create your views here.

# porter dashboard
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def PorterDashboard(request):
    # get the logged in porter/user from the token 
    try:
        porter=request.user.porter_profile
    except PorterProfile.DoesNotExist:
        return Response ({"error":"Only porters can access this dashboard"})
    
    # time settings 
    today=timezone.now().date()
    week_start=today-timedelta(days=7)
    month_start=today.replace(day=1)

    # today collections
    today_collections=MilkCollection.objects.filter(porter=porter, collection_date__gte=today)
    total_collection_today=today_collections.count()
    total_litres_today=today_collections.aggregate(total=Sum('litres'))
    total_amount_today=today_collections.aggregate(total=Sum('total_amount'))['total'] or 0

    # weekly/monthly collections 
    week_collection=MilkCollection.objects.filter(porter=porter, collection_date__gte=week_start)
    total_litres_week=week_collection.aggregate(total=Sum('litres'))['total'] or 0

    monthly_collections=MilkCollection.objects.filter(porter=porter,collection_date__gte=month_start)
    total_litres_month=monthly_collections.aggregate(total=Sum('litres'))['total'] or 0

    # current 5 collections 
    last_collections=MilkCollection.objects.filter(porter=porter).order_by("created_at")[:5]

    # serialize the multiple milk collection record since last_collection is a query set-multiple objects
    last_collections_list=RecentCollectionsSerializer(last_collections,many=True).data #DRF Serializes each collection individually.without it we treat  it as a single object object. Data returns the serialized JSON-ready representatopn of the query

    response_data={
        'date':today,
        'assigned_farmers':porter.assigned_farmers.count(),
        'total_collections_today':total_litres_today,
        'total_amount_today':total_amount_today,
        'total_litres_week':total_litres_week,
        'total_litres_month':total_litres_month,
        'last_collections':last_collections_list,
        'porter_name':f"{porter.first_name} {porter.last_name}",
        "route_name":porter.route_name,
        "employee_id":porter.employee_id
    }  
    return Response(response_data)

@api_view(['POST'])
@permission_classes( [IsAuthenticated])
def AddMilkCollection(request):
    # get the logged in user- porter
    try:
        porter=request.user.porter_profile
    except PorterProfile.DoesNotExist:
        return Response({"error":"Only porter can add milk collection"})
    
    # check if the farmer exists 
    try:
        national_id=request.data.get("national_id")
        farmer=FarmerProfile.objects.get(national_id=national_id)
    except FarmerProfile.DoesNotExist:
        return Response({"error":"farmer not found"})

    collection=MilkCollection.objects.create(
        farmer=farmer,
        porter=porter,
        litres=request.data.get("litres"),
        session=request.data.get("session")
    )
    return Response({
        "message":"Milk_collection recorded succesfully",
        "collection_id":collection.id,
        "farmer":f"{farmer.first_name} {farmer.last_name}",
        "porter":f"{porter.first_name} {porter.last_name}",
        "litres":collection.litres
    })

# view porter collection 
class MyCollections(generics.ListAPIView):
    serializer_class=MilkCollectionSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        porter=self.request.user.porter_profile
        collection=(
            MilkCollection.objects
            .filter(porter=porter)
            .order_by('created_at')
        )
        return collection
    
class PorterNoticeView(generics.ListAPIView):
    serializer_class=NoticeSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        notices=(
            Notice.objects.filter(target__in=['ALL','PORTERS'])
            .order_by('created_at')
        )
        return notices
    
    