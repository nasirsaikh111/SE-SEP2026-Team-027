from rest_framework import serializers
from .models import MentoringRequest, AvailabilityCheck, Mentorship, Goal, Meeting, Feedback, Outcome, Notification

class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model=MentoringRequest
        fields=('id','student','pathway','domain','background','problem_statement','status','submitted_at','updated_at')
        read_only_fields=('student','status','submitted_at','updated_at')
    def validate_problem_statement(self,value):
        if len(value.strip())<80: raise serializers.ValidationError('Minimum 80 characters required.')
        return value

class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model=AvailabilityCheck
        fields=('id','request','mentor','status','sent_at','expires_at','responded_at','reason')
        read_only_fields=fields

class PairSerializer(serializers.ModelSerializer):
    student_contact=serializers.SerializerMethodField()
    mentor_contact=serializers.SerializerMethodField()
    class Meta:
        model=Mentorship
        fields=('id','request','student','mentor','status','started_at','closed_at','student_contact','mentor_contact')
    def get_student_contact(self,obj):
        u=self.context['request'].user
        return obj.student.email if (u.is_superuser or u.is_staff and u.role=='ADMIN' or u.pk in (obj.student_id,obj.mentor_id)) else None
    def get_mentor_contact(self,obj):
        u=self.context['request'].user
        return obj.mentor.email if (u.is_superuser or u.is_staff and u.role=='ADMIN' or u.pk in (obj.student_id,obj.mentor_id)) else None

class GoalSerializer(serializers.ModelSerializer):
    class Meta:
        model=Goal
        fields=('id','mentorship','slot','title','target_date','completed','completed_at')
        read_only_fields=('mentorship','completed_at')

class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model=Meeting
        fields=('id','mentorship','session_date','duration_minutes','status','logged_by','mentor_confirmed','created_at')
        read_only_fields=('mentorship','logged_by','mentor_confirmed','created_at')
    def validate_duration_minutes(self,v):
        if v<1 or v>720:raise serializers.ValidationError('Duration must be 1–720 minutes.')
        return v

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model=Feedback
        fields=('id','mentorship','author','kind','text','created_at')
        read_only_fields=('mentorship','author','created_at')
    def validate_text(self,v):
        if not v.strip():raise serializers.ValidationError('Written feedback is required.')
        return v

class OutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model=Outcome
        fields=('id','mentorship','kind','achieved_on','note','created_at')
        read_only_fields=('mentorship','created_at')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Notification
        fields=('id','title','message','is_read','created_at')
        read_only_fields=('id','title','message','created_at')
