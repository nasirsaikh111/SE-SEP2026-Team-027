from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from .models import User, StudentProfile, MentorProfile

class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ('iitm_roll_number', 'level', 'courses', 'cgpa', 'approval_status','rejection_reason')
        read_only_fields = ('approval_status','rejection_reason')

class StudentRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    iitm_roll_number = serializers.CharField(max_length=50)
    level = serializers.ChoiceField(choices=StudentProfile.Level.choices)
    courses = serializers.ListField(child=serializers.CharField(max_length=120), allow_empty=False)
    cgpa = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10, required=False, allow_null=True)
    def validate_email(self, email):
        domain = email.lower().split('@')[-1]
        if domain != 'iitm.ac.in' and not domain.endswith('.iitm.ac.in'):
            raise serializers.ValidationError('Registration requires an IITM email address.')
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email is already registered.')
        return email.lower()
    def validate_password(self, password):
        validate_password(password)
        return password
    @transaction.atomic
    def create(self, validated_data):
        p = {key:validated_data.pop(key) for key in ('iitm_roll_number','level','courses','cgpa') if key in validated_data}
        user = User.objects.create_user(role='STUDENT', **validated_data)
        StudentProfile.objects.create(user=user, **p)
        return user

class MeSerializer(serializers.ModelSerializer):
    student_profile = StudentProfileSerializer(read_only=True)
    class Meta:
        model = User
        fields = ('id','email','first_name','last_name','role','student_profile')

class StudentReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['APPROVED','REJECTED'])
    reason = serializers.CharField(required=False, allow_blank=True)
    academic_verified = serializers.BooleanField(default=False)
    def validate(self,data):
        if data['decision'] == 'REJECTED' and not data.get('reason','').strip():
            raise serializers.ValidationError({'reason':'Reason required for rejection.'})
        if data['decision'] == 'APPROVED' and not data.get('academic_verified'):
            raise serializers.ValidationError({'academic_verified':'IIC must verify academic details from authorized records.'})
        return data

class MentorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorProfile
        fields = ('id','user','alumni_roll_number','graduation_year','domain','specialty','current_role','company',
                  'career_path','experience_years','is_verified','is_available')
        read_only_fields = ('user','is_verified')

class MentorCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    alumni_roll_number = serializers.CharField(max_length=50)
    graduation_year = serializers.IntegerField(min_value=1990, max_value=2100)
    domain = serializers.CharField(max_length=150)
    specialty = serializers.CharField(max_length=200)
    current_role = serializers.CharField(max_length=150)
    company = serializers.CharField(max_length=150, required=False, allow_blank=True)
    experience_years = serializers.IntegerField(min_value=0, max_value=80)
    def validate_email(self, email):
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email already exists.')
        return email.lower()
    @transaction.atomic
    def create(self,data):
        profile_keys = ('alumni_roll_number','graduation_year','domain','specialty','current_role','company','experience_years')
        profile = {k:data.pop(k) for k in profile_keys if k in data}
        user = User(email=data['email'],first_name=data['first_name'],last_name=data['last_name'],role='MENTOR')
        user.set_unusable_password()  # IIC creates mentor; activation is a separate secure workflow
        user.save()
        MentorProfile.objects.create(user=user, invited_by=self.context['request'].user, **profile)
        return user
