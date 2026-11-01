import re
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from .models import User, StudentProfile, MentorProfile, validate_linkedin_url
from .permissions import iic


def clean_linkedin(value):
    if value:
        try:
            validate_linkedin_url(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages[0])
    return value


def clean_skills(value):
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise serializers.ValidationError('Skills must be a list of strings.')
    cleaned = []
    for item in value:
        item = item.strip()[:60]
        if item and item.casefold() not in {c.casefold() for c in cleaned}:
            cleaned.append(item)
    if len(cleaned) > 15:
        raise serializers.ValidationError('At most 15 skills.')
    return cleaned


class StudentProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = ('iitm_roll_number', 'level', 'courses', 'cgpa', 'approval_status','rejection_reason')
        read_only_fields = ('approval_status','rejection_reason')

IITM_ROLL = re.compile(r'^\d{2}f\d{7}$', re.IGNORECASE)


def roll_from_email(email):
    """IITM BS student emails are <roll>@ds.study.iitm.ac.in (or es.study), e.g. 21f1000907."""
    local = (email or '').split('@')[0]
    return local.lower() if IITM_ROLL.match(local) else ''


class StudentRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    iitm_roll_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
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
    def validate(self, data):
        if not data.get('iitm_roll_number', '').strip():
            data['iitm_roll_number'] = roll_from_email(data.get('email'))
            if not data['iitm_roll_number']:
                raise serializers.ValidationError({'iitm_roll_number': 'Enter your IITM roll number.'})
        return data
    @transaction.atomic
    def create(self, validated_data):
        p = {key:validated_data.pop(key) for key in ('iitm_roll_number','level','courses','cgpa') if key in validated_data}
        user = User.objects.create_user(role='STUDENT', **validated_data)
        StudentProfile.objects.create(user=user, **p)
        return user

# What IIC confirms against IITM records before approving a registration.
REVIEW_CHECKLIST = ('iitm_email', 'roll_number', 'level', 'courses', 'cgpa')


class StudentReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=['APPROVED','REJECTED'])
    reason = serializers.CharField(required=False, allow_blank=True)
    academic_verified = serializers.BooleanField(default=False)
    checklist = serializers.DictField(child=serializers.BooleanField(), required=False,
                                      help_text=f'Each of {", ".join(REVIEW_CHECKLIST)} must be true to approve.')
    def validate(self,data):
        if data['decision'] == 'REJECTED' and not data.get('reason','').strip():
            raise serializers.ValidationError({'reason':'Reason required for rejection.'})
        if data['decision'] == 'APPROVED':
            if 'checklist' in data:
                missing = [item for item in REVIEW_CHECKLIST if not data['checklist'].get(item)]
                if missing:
                    raise serializers.ValidationError({'checklist': f'Confirm every checklist item before approving: {", ".join(missing)}.'})
                data['academic_verified'] = True
            if not data.get('academic_verified'):
                raise serializers.ValidationError({'academic_verified':'IIC must verify academic details from authorized records.'})
        return data

class MentorProfileSerializer(serializers.ModelSerializer):
    """Full mentor record for IIC staff and for the mentor's own profile."""
    name = serializers.SerializerMethodField()
    has_active_mentee = serializers.SerializerMethodField()
    class Meta:
        model = MentorProfile
        fields = ('id','user','name','alumni_roll_number','graduation_year','domain','specialty','current_role','company',
                  'career_path','experience_years','is_verified','is_available','bio','skills','linkedin_url',
                  'is_discoverable','verified_at','has_active_mentee')
        read_only_fields = ('user','is_verified','is_discoverable','verified_at')
    def get_name(self, obj) -> str:
        return obj.user.get_full_name()
    def get_has_active_mentee(self, obj) -> bool:
        value = getattr(obj, 'has_active_mentee', None)
        if value is None:
            value = obj.user.mentor_mentorships.filter(status='ACTIVE').exists()
        return bool(value)


class MentorSelfUpdateSerializer(serializers.ModelSerializer):
    """Fields a mentor may edit. Verification and directory publication remain IIC-controlled."""
    class Meta:
        model = MentorProfile
        fields = ('domain','specialty','current_role','company','career_path','experience_years','bio','skills','linkedin_url')
        extra_kwargs = {'experience_years': {'min_value': 0, 'max_value': 80}}
    def validate_linkedin_url(self, value):
        return clean_linkedin(value)
    def validate_skills(self, value):
        return clean_skills(value)


class MentorAdminUpdateSerializer(MentorSelfUpdateSerializer):
    class Meta(MentorSelfUpdateSerializer.Meta):
        fields = MentorSelfUpdateSerializer.Meta.fields + ('is_discoverable','is_available','alumni_roll_number','graduation_year')
    def validate(self, data):
        verified = self.instance.is_verified if self.instance else False
        if data.get('is_discoverable') and not verified:
            raise serializers.ValidationError({'is_discoverable': 'Only verified mentors can be published to the directory.'})
        return data


class MentorDirectorySerializer(serializers.ModelSerializer):
    """Directory card for approved students. Never includes email, phone or roll numbers."""
    id = serializers.IntegerField(source='user_id', read_only=True)
    name = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    class Meta:
        model = MentorProfile
        fields = ('id','name','current_role','company','domain','specialty','career_path','experience_years',
                  'skills','bio','linkedin_url','graduation_year','availability')
    def get_name(self, obj) -> str:
        return obj.user.get_full_name() or 'IITM alumni mentor'
    def get_availability(self, obj) -> dict:
        busy = getattr(obj, 'has_active_mentee', None)
        if busy is None:
            busy = obj.user.mentor_mentorships.filter(status='ACTIVE').exists()
        accepting = obj.is_available and not busy
        return {'is_available': obj.is_available, 'has_capacity': not busy, 'accepting_requests': accepting,
                'label': 'Available' if accepting else 'Currently mentoring' if busy else 'Unavailable'}


class MeSerializer(serializers.ModelSerializer):
    """The single source of the signed-in user's role for the frontend.

    ``effective_role`` is ADMIN only for real IIC staff (role ADMIN + is_staff, or superuser),
    matching the backend IsIIC permission; navigation must be derived from it.
    """
    student_profile = StudentProfileSerializer(read_only=True)
    mentor_profile = serializers.SerializerMethodField()
    is_iic = serializers.SerializerMethodField()
    effective_role = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    calendar = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id','email','first_name','last_name','role','student_profile','mentor_profile','is_iic',
                  'effective_role','display_name','calendar')
        read_only_fields = ('id','email','role')
    def get_mentor_profile(self, obj) -> dict | None:
        profile = getattr(obj, 'mentor_profile', None) if obj.role == 'MENTOR' else None
        return MentorProfileSerializer(profile).data if profile else None
    def get_is_iic(self, obj) -> bool:
        return iic(obj)
    def get_effective_role(self, obj) -> str | None:
        if iic(obj):
            return 'ADMIN'
        return obj.role if obj.role in ('STUDENT', 'MENTOR') else None
    def get_display_name(self, obj) -> str:
        return obj.get_full_name() or obj.email.split('@')[0]
    def get_calendar(self, obj) -> dict | None:
        if obj.role != 'MENTOR':
            return None
        from apps.mentoring.google_calendar import connection_status
        return connection_status(obj)

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
    career_path = serializers.CharField(max_length=150, required=False, allow_blank=True)
    bio = serializers.CharField(max_length=500, required=False, allow_blank=True)
    skills = serializers.ListField(child=serializers.CharField(max_length=60), required=False)
    linkedin_url = serializers.URLField(max_length=300, required=False, allow_blank=True)
    def validate_email(self, email):
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError('Email already exists.')
        return email.lower()
    def validate_linkedin_url(self, value):
        return clean_linkedin(value)
    def validate_skills(self, value):
        return clean_skills(value)
    @transaction.atomic
    def create(self,data):
        profile_keys = ('alumni_roll_number','graduation_year','domain','specialty','current_role','company','experience_years',
                        'career_path','bio','skills','linkedin_url')
        profile = {k:data.pop(k) for k in profile_keys if k in data}
        user = User(email=data['email'],first_name=data['first_name'],last_name=data['last_name'],role='MENTOR')
        user.set_unusable_password()  # IIC creates mentor; activation is a separate secure workflow
        user.save()
        MentorProfile.objects.create(user=user, invited_by=self.context['request'].user, **profile)
        return user
