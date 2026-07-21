from rest_framework import serializers
from core.models import Feedback, MilkCollection

class MilkCollectionSerializer(serializers.ModelSerializer):
    porter_name=serializers.SerializerMethodField()
    class Meta:
        model=MilkCollection
        fields=['id','litres','session','price_per_litre','total_amount','collection_date','porter_name']

    # method to just join the first name and last name of the porter to be one name use it when you want to alter the field on how it look like in the model 
    def get_porter_name(self,obj):
        return f"{obj.porter.first_name} {obj.porter.last_name}"
    
# feedback serializer
class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model=Feedback
        fields=['id','title','description','status','created_at',"updated_at"]
        read_only_fields=['status','created_at','updated_at']