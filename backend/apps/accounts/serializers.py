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
    # Sangam is open to IITM BS Degree-level students only
    def validate_level(self, level):
        if level != StudentProfile.Level.DEGREE:
            raise serializers.ValidationError('Sangam is open to IITM BS Degree-level students only.')
        return level
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
    mentor_profile = serializers.SerializerMethodField()
    is_iic = serializers.SerializerMethodField()
    effective_role = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    calendar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'role',
            'student_profile', 'mentor_profile', 'is_iic',
            'effective_role', 'display_name', 'calendar'
        )
        read_only_fields = ('id', 'email', 'role')

    def get_mentor_profile(self, obj):
        profile = getattr(obj, 'mentor_profile', None) if obj.role == 'MENTOR' else None
        if not profile:
            return None
        return MentorProfileSerializer(profile).data

    def get_is_iic(self, obj):
        return bool(obj.is_authenticated and (obj.is_superuser or obj.role == 'ADMIN' or obj.is_staff))

    def get_effective_role(self, obj):
        if obj.role == 'ADMIN' or obj.is_superuser or obj.is_staff:
            return 'ADMIN'
        return obj.role if obj.role in ('STUDENT', 'MENTOR') else None

    def get_display_name(self, obj):
        return obj.get_full_name() or obj.email.split('@')[0]

    def get_calendar(self, obj):
        return {'configured': False, 'status': 'DISCONNECTED', 'google_email': '', 'connected_at': None}

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
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    linkedin_url = serializers.SerializerMethodField()
    has_active_mentee = serializers.SerializerMethodField()

    class Meta:
        model = MentorProfile
        fields = ('id','user','name','email','alumni_roll_number','graduation_year','domain','specialty','current_role','company',
                  'career_path','experience_years','is_verified','is_available','is_discoverable','bio','skills','linkedin_url','has_active_mentee')
        read_only_fields = ('user','is_verified')

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.email.split('@')[0]

    def get_email(self, obj):
        return obj.user.email

    def get_linkedin_url(self, obj):
        return ''

    def get_has_active_mentee(self, obj):
        busy = getattr(obj, 'has_active_mentee', None)
        if busy is None:
            busy = obj.user.mentor_mentorships.filter(status='ACTIVE').exists()
        return bool(busy)

class MentorSelfUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorProfile
        fields = ('domain','specialty','current_role','company','career_path','experience_years','bio','skills')
        extra_kwargs = {'experience_years': {'min_value': 0, 'max_value': 80}}

class MentorAdminUpdateSerializer(MentorSelfUpdateSerializer):
    class Meta(MentorSelfUpdateSerializer.Meta):
        fields = MentorSelfUpdateSerializer.Meta.fields + ('is_discoverable','is_available','alumni_roll_number','graduation_year')

class MentorDirectorySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user_id', read_only=True)
    name = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    linkedin_url = serializers.SerializerMethodField()

    class Meta:
        model = MentorProfile
        fields = ('id','name','current_role','company','domain','specialty','career_path','experience_years',
                  'skills','bio','linkedin_url','graduation_year','availability')

    def get_name(self, obj):
        return obj.user.get_full_name() or 'IITM alumni mentor'

    def get_linkedin_url(self, obj):
        return ''

    def get_availability(self, obj):
        busy = getattr(obj, 'has_active_mentee', None)
        if busy is None:
            busy = obj.user.mentor_mentorships.filter(status='ACTIVE').exists()
        accepting = obj.is_available and not busy
        return {'is_available': obj.is_available, 'has_capacity': not busy, 'accepting_requests': accepting,
                'label': 'Available' if accepting else 'Currently mentoring' if busy else 'Unavailable'}

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
