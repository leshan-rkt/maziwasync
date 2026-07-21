from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from numpy import generic
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, generics
from rest_framework.permissions import IsAdminUser, AllowAny
from  rest_framework.views import APIView, Response
from cooperative.services import MpesaPayment
from core.models import FarmerProfile, MilkCollection, Notice, Payment, PorterProfile, Feedback
from collector.serializers import MilkCollectionSerializer
from farmer.serializers import FeedbackSerializer
from django.db.models import Sum
from  .serializers import FarmerSerializer, NoticeSerializer, PorterSerializer
# Create your views here.

class AdminDashboardView(APIView):

    # Only administrators can access cooperative analytics
    permission_classes = [IsAdminUser]

    def get(self, request):

        # Get today's date according to Django timezone settings
        # Used for daily, weekly and monthly calculations
        today = timezone.localdate()

        # Calculate the starting date of the last 7 days
        # Used for weekly statistics
        week_start = today - timedelta(days=7)
        total_farmers = FarmerProfile.objects.count()

        total_porters = PorterProfile.objects.count()

    
        collections = MilkCollection.objects.all()

        # Total litres collected since the system started
        total_litres = collections.aggregate(
            total=Sum('litres')
        )['total'] or 0

        # Total litres collected today only
        today_litres = collections.filter(
            collection_date=today
        ).aggregate(
            total=Sum('litres')
        )['total'] or 0

        # Total litres collected during the last 7 days
        weekly_litres = collections.filter(
            collection_date__gte=week_start
        ).aggregate(
            total=Sum('litres')
        )['total'] or 0

        # Total litres collected during the current month
        monthly_litres = collections.filter(
            collection_date__year=today.year,
            collection_date__month=today.month
        ).aggregate(
            total=Sum('litres')
        )['total'] or 0

        
        # Total money generated from all milk collections
        total_revenue = collections.aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        # Revenue generated today
        today_revenue = collections.filter(
            collection_date=today
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        # Revenue generated in the last 7 days
        weekly_revenue = collections.filter(
            collection_date__gte=week_start
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        # Revenue generated in the current month
        monthly_revenue = collections.filter(
            collection_date__year=today.year,
            collection_date__month=today.month
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0

      
        # Number of complaints/feedback not yet resolved
        pending_feedback = Feedback.objects.filter(
            status='PENDING'
        ).count()

        # Number of complaints already resolved
        resolved_feedback = Feedback.objects.filter(
            status='RESOLVED'
        ).count()

     
        # Retrieve farmers with highest milk delivery
        # Limit to top 5 farmers only
        top_farmers = FarmerProfile.objects.order_by(
            '-total_milk_delivered'
        )[:5]

        # Convert FarmerProfile objects into JSON
        # Response() cannot directly return Django model objects
        top_farmers_data = FarmerSerializer(
            top_farmers,
            many=True
        ).data


        recent_collections = MilkCollection.objects.select_related(
            'farmer',
            'porter'
        ).order_by('-created_at')[:10]

        # Convert collection objects into JSON
        recent_collections_data = MilkCollectionSerializer(
            recent_collections,
            many=True
        ).data

     
        return Response({

            "farmers": total_farmers,
            "porters": total_porters,
            "total_liters": total_litres,
            "today_liters": today_litres,
            "weekly_liters": weekly_litres,
            "monthly_liters": monthly_litres,
            "total_revenue": total_revenue,
            "today_revenue": today_revenue,
            "weekly_revenue": weekly_revenue,
            "monthly_revenue": monthly_revenue,
            "pending_feedback": pending_feedback,
            "resolved_feedback": resolved_feedback,
            "top_farmers": top_farmers_data,
            "recent_collections": recent_collections_data
        })


# view farmer feedback
class ViewFeedback(generics.ListAPIView):
    serializer_class=FeedbackSerializer
    permission_classes=[IsAdminUser]
     
    def get_queryset(self):
        feedback=Feedback.objects.order_by('created_at')
        return feedback


class FarmerViewSet(viewsets.ModelViewSet):
    queryset=FarmerProfile.objects.all()
    serializer_class=FarmerSerializer
    permission_classes=[IsAdminUser]
    http_method_names=['get','put','patch','delete']

class PorterViewSet(viewsets.ModelViewSet):
    queryset=PorterProfile.objects.all()
    serializer_class=PorterSerializer
    permission_classes=[IsAdminUser]
    http_method_names=['get','put','patch','delete']

class MilkCollectionViewSet(viewsets.ModelViewSet):
    queryset=MilkCollection.objects.select_related(
        'farmer',
        'porter'
    )
    serializer_class=MilkCollectionSerializer
    permission_classes=[IsAdminUser]
    http_method_names=['get','put','patch','delete']



    
# notices board 
class NoticeViewSet(viewsets.ModelViewSet):
    queryset=Notice.objects.all()
    serializer_class=NoticeSerializer
    permission_classes=[IsAdminUser]

    def perform_create(self, serializer):
       serializer.save(created_by=self.request.user)

# farmers with bal 
@api_view(['GET'])
@permission_classes([IsAdminUser])
def farmersbalance(request):

    farmers = FarmerProfile.objects.all()

    data = []

    for farmer in farmers:
        earned = MilkCollection.objects.filter(
            farmer=farmer
        ).aggregate(
            total=Sum('total_amount')
        )['total'] or 0


        paid = Payment.objects.filter(
            farmer=farmer,
            status="COMPLETED"
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0

        balance = earned - paid
        if balance > 0:
            data.append({
                "farmer_id": farmer.id,
                "farmer": farmer.first_name,
                "phone": farmer.mpesa_number,
                "earned": earned,
                "paid": paid,
                "balance": balance
            })

    return Response(data)


# initiate disbursement to the farmer 
@api_view(['POST'])
@permission_classes([IsAdminUser])
def pay_farmer(request):
    farmer_id=request.data["farmer_id"]
    amount = request.data["amount"]

    farmer = FarmerProfile.objects.get(id=farmer_id)
    earned = MilkCollection.objects.filter(farmer=farmer).aggregate(total=Sum('total_amount'))['total'] or 0
    paid = Payment.objects.filter(farmer=farmer, status="COMPLETED").aggregate(total=Sum('amount'))['total'] or 0
    balance = earned - paid
    if balance <= 0:
        return Response({"message":"No pending payment"})
    
    payment=MpesaPayment()
    result = payment.pay_farmer(farmer.mpesa_number,amount)
    # Store payment attempt
    Payment.objects.create(
        farmer=farmer,
        amount=amount,
        payment_method="MPESA",
        status="COMPLETED",
        originator_conversation_id =result["OriginatorConversationID"],
        transaction_ref=result.get("ConversationID"),
        payment_date=timezone.now()
    )

    return Response({"farmer": farmer.first_name, "balance": balance, "mpesa_response": result })

# ansynchronous call back processing webhook
@api_view(["POST"])
@permission_classes([AllowAny])
def MpesaCallback(request):
    print ("=======CALL BACK HIT===========")
    data=request.data
    print ("Data",data)
    result=data['Result']

    originator_conversation_id=result["OriginatorConversationID"]

    # retrieve the matching payment record with the originator conversation id
    payment=Payment.objects.get(originator_conversation_id=originator_conversation_id)

    # check if the transaction was succesful
    if result["ResultCode"]==0:
        payment.status="COMPLETED"
        payment.transaction_ref=result["TransactionID"]
    else:
        payment.status="FAILED"

    payment.save()
    return Response({"received":True})

