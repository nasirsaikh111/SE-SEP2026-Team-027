from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
import django_filters
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import generics, serializers, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .models import User, StudentProfile, MentorProfile
from .pagination import list_response
from .permissions import IsIIC, IsVerifiedMentor, IsMentor, IsApprovedStudentOrIIC
from .serializers import (StudentRegistrationSerializer, MeSerializer, StudentProfileSerializer, StudentReviewSerializer,
                          MentorCreateSerializer, MentorProfileSerializer, MentorSelfUpdateSerializer,
                          MentorAdminUpdateSerializer, MentorDirectorySerializer)
from apps.mentoring.models import AuditLog, Notification, Mentorship


class AuthThrottle(ScopedRateThrottle):
    scope = 'sangam_auth'
    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


@extend_schema(tags=['auth'], summary='Obtain JWT access/refresh tokens (email + password)')
class SangamTokenObtainView(TokenObtainPairView):
    throttle_classes = [AuthThrottle]


@extend_schema(tags=['auth'], summary='Refresh a JWT access token')
class SangamTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthThrottle]


@extend_schema(tags=['auth'], summary='Register a student (IITM email); account then awaits IIC approval',
               responses={201: inline_serializer('RegisterResult', {'id': serializers.IntegerField(),
                          'approval_status': serializers.CharField(), 'message': serializers.CharField()})})
class RegisterView(generics.CreateAPIView):
    serializer_class = StudentRegistrationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AuthThrottle]
    def create(self,request,*args,**kwargs):
        s=self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        u=s.save()
        return Response({'id':u.pk,'approval_status':'PENDING','message':'IIC approval required.'},status=201)

@extend_schema(tags=['auth'], summary='Current user, role, profiles and calendar status', request=MeSerializer, responses=MeSerializer)
@api_view(['GET','PATCH'])
@permission_classes([IsAuthenticated])
def me(request):
    if request.method == 'PATCH':
        s = MeSerializer(request.user, data={k: v for k, v in request.data.items() if k in ('first_name', 'last_name')}, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
    return Response(MeSerializer(request.user).data)

@extend_schema(tags=['students'], summary="Student's own academic profile (editable until approved)",
               request=StudentProfileSerializer, responses=StudentProfileSerializer)
@api_view(['GET','PATCH'])
@permission_classes([IsAuthenticated])
def student_profile(request):
    if request.user.role != 'STUDENT': return Response({'detail':'Students only.'}, status=403)
    p=get_object_or_404(StudentProfile,user=request.user)
    if request.method=='GET': return Response(StudentProfileSerializer(p).data)
    if p.approval_status=='APPROVED': return Response({'detail':'Approved academic records are locked.'},status=403)
    serializer=StudentProfileSerializer(p,data=request.data,partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save(approval_status='PENDING',approved_by=None,approved_at=None,rejection_reason='')
    return Response(serializer.data)

@extend_schema(tags=['students'], summary='IIC: list student registrations by status', responses=OpenApiTypes.OBJECT,
               parameters=[OpenApiParameter('status', str, description='PENDING (default), APPROVED, REJECTED or ALL'),
                           OpenApiParameter('search', str, description='Name, email or roll number')])
@api_view(['GET'])
@permission_classes([IsIIC])
def pending_students(request):
    state=request.query_params.get('status','PENDING').upper()
    qs=StudentProfile.objects.select_related('user').order_by('created_at')
    if state != 'ALL':
        qs=qs.filter(approval_status=state)
    term=request.query_params.get('search','').strip()
    if term:
        qs=qs.filter(Q(user__email__icontains=term)|Q(user__first_name__icontains=term)|Q(user__last_name__icontains=term)|Q(iitm_roll_number__icontains=term))
    serialize=lambda rows: [{'id':p.pk,'user_id':p.user_id,'email':p.user.email,'name':p.user.get_full_name(),
                             'submitted_at':p.created_at,'approved_at':p.approved_at,**StudentProfileSerializer(p).data} for p in rows]
    return list_response(request, qs, serialize)

@extend_schema(tags=['students'], summary='IIC: approve or reject a student registration (pk = user id)',
               request=StudentReviewSerializer, responses=StudentProfileSerializer)
@api_view(['POST'])
@permission_classes([IsIIC])
@transaction.atomic
def review_student(request,pk):
    serializer=StudentReviewSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    p=get_object_or_404(StudentProfile.objects.select_for_update(),user_id=pk)
    if serializer.validated_data['decision']=='APPROVED' and (not p.iitm_roll_number or not p.level or not p.courses or p.cgpa is None):
        raise ValidationError('IITM ID, level, courses, and CGPA must be verified before approving.')
    p.approval_status=serializer.validated_data['decision']
    p.rejection_reason=serializer.validated_data.get('reason','')
    p.approved_at=timezone.now() if p.approval_status=='APPROVED' else None
    p.approved_by=request.user if p.approval_status=='APPROVED' else None
    p.save()
    AuditLog.objects.create(actor=request.user,action='STUDENT_REVIEW',entity_type='StudentProfile',entity_id=p.pk,details={'status':p.approval_status})
    Notification.objects.create(recipient=p.user,title='Student registration',message=f'Registration status: {p.approval_status}. {p.rejection_reason}')
    return Response(StudentProfileSerializer(p).data)


def mentor_queryset():
    busy = Mentorship.objects.filter(mentor=OuterRef('user_id'), status='ACTIVE')
    return MentorProfile.objects.select_related('user').annotate(has_active_mentee=Exists(busy))


@extend_schema(tags=['mentors'], summary='IIC: mentor repository (GET) or add an alumni mentor (POST)',
               request=MentorCreateSerializer, responses=MentorProfileSerializer(many=True),
               parameters=[OpenApiParameter('verified', bool), OpenApiParameter('discoverable', bool),
                           OpenApiParameter('search', str), OpenApiParameter('domain', str)])
@api_view(['GET','POST'])
@permission_classes([IsIIC])
def mentors(request):
    if request.method=='GET':
        qs=mentor_queryset().order_by('id')
        flags={'verified':'is_verified','discoverable':'is_discoverable','available':'is_available'}
        for param,field in flags.items():
            value=request.query_params.get(param)
            if value in ('true','false'):
                qs=qs.filter(**{field:value=='true'})
        if request.query_params.get('domain'):
            qs=qs.filter(domain__icontains=request.query_params['domain'])
        term=request.query_params.get('search','').strip()
        if term:
            qs=qs.filter(Q(user__email__icontains=term)|Q(user__first_name__icontains=term)|Q(user__last_name__icontains=term)|
                         Q(company__icontains=term)|Q(specialty__icontains=term)|Q(alumni_roll_number__icontains=term))
        return list_response(request, qs, lambda rows: [{'email':m.user.email,**MentorProfileSerializer(m).data} for m in rows])
    s=MentorCreateSerializer(data=request.data,context={'request':request})
    s.is_valid(raise_exception=True)
    u=s.save()
    AuditLog.objects.create(actor=request.user,action='MENTOR_ADDED',entity_type='MentorProfile',entity_id=u.mentor_profile.id)
    return Response({'id':u.id,'email':u.email,'is_verified':False,'activation':'IIC must invite mentor to set a password.'},status=201)


@extend_schema(tags=['mentors'], summary='IIC: update a mentor profile or directory publication (pk = user id)',
               request=MentorAdminUpdateSerializer, responses=MentorProfileSerializer)
@api_view(['PATCH'])
@permission_classes([IsIIC])
def mentor_admin_update(request, pk):
    m=get_object_or_404(mentor_queryset(),user_id=pk)
    s=MentorAdminUpdateSerializer(m,data=request.data,partial=True)
    s.is_valid(raise_exception=True)
    s.save()
    AuditLog.objects.create(actor=request.user,action='MENTOR_UPDATED',entity_type='MentorProfile',entity_id=m.pk,
                            details={'fields':sorted(s.validated_data.keys())})
    return Response({'email':m.user.email,**MentorProfileSerializer(get_object_or_404(mentor_queryset(),pk=m.pk)).data})


@extend_schema(tags=['mentors'], summary='IIC: verify an alumni mentor (pk = user id); publishes to the directory unless discoverable=false',
               request=inline_serializer('VerifyMentor', {'discoverable': serializers.BooleanField(required=False, default=True)}),
               responses=inline_serializer('VerifyMentorResult', {'mentor_id': serializers.IntegerField(),
                          'is_verified': serializers.BooleanField(), 'is_discoverable': serializers.BooleanField()}))
@api_view(['POST'])
@permission_classes([IsIIC])
def verify_mentor(request,pk):
    m=get_object_or_404(MentorProfile,user_id=pk)
    if not m.alumni_roll_number or not m.graduation_year:
        raise ValidationError('Verify alumni roll number and graduation year against authorized IIC records first.')
    discoverable=request.data.get('discoverable',True)
    if not isinstance(discoverable,bool): raise ValidationError({'discoverable':'Must be a boolean.'})
    m.is_verified=True;m.is_discoverable=discoverable;m.verified_by=request.user;m.verified_at=timezone.now()
    m.save(update_fields=['is_verified','is_discoverable','verified_by','verified_at'])
    AuditLog.objects.create(actor=request.user,action='MENTOR_VERIFIED',entity_type='MentorProfile',entity_id=m.pk,details={'discoverable':discoverable})
    Notification.objects.create(recipient=m.user,title='Mentor profile verified',message='IIC has verified your alumni mentor profile.')
    return Response({'mentor_id':pk,'is_verified':True,'is_discoverable':discoverable})

@extend_schema(tags=['mentors'], summary='Verified mentor: toggle availability for new mentoring requests',
               request=inline_serializer('AvailabilityToggle', {'is_available': serializers.BooleanField()}),
               responses=inline_serializer('AvailabilityToggleResult', {'is_available': serializers.BooleanField()}))
@api_view(['PATCH'])
@permission_classes([IsVerifiedMentor])
def mentor_availability(request):
    value=request.data.get('is_available')
    if not isinstance(value,bool): return Response({'detail':'is_available must be a boolean.'},status=400)
    MentorProfile.objects.filter(user=request.user).update(is_available=value)
    return Response({'is_available':value})


@extend_schema(tags=['mentors'], summary="Mentor: own professional profile (verification fields are read-only)",
               request=MentorSelfUpdateSerializer, responses=MentorProfileSerializer)
@api_view(['GET','PATCH'])
@permission_classes([IsMentor])
def mentor_profile(request):
    m=get_object_or_404(mentor_queryset(),user=request.user)
    if request.method=='PATCH':
        s=MentorSelfUpdateSerializer(m,data=request.data,partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        m=get_object_or_404(mentor_queryset(),pk=m.pk)
    return Response(MentorProfileSerializer(m).data)


class MentorDirectoryFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Name, role, company, specialty or skill')
    domain = django_filters.CharFilter(field_name='domain', lookup_expr='icontains')
    specialty = django_filters.CharFilter(field_name='specialty', lookup_expr='icontains')
    career_path = django_filters.CharFilter(field_name='career_path', lookup_expr='icontains')
    skill = django_filters.CharFilter(field_name='skills', lookup_expr='icontains')
    min_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='gte')
    max_experience = django_filters.NumberFilter(field_name='experience_years', lookup_expr='lte')
    available = django_filters.BooleanFilter(method='filter_available', label='Only mentors accepting requests')
    class Meta:
        model = MentorProfile
        fields = []
    def filter_search(self, qs, name, value):
        value = value.strip()
        if not value:
            return qs
        return qs.filter(Q(user__first_name__icontains=value)|Q(user__last_name__icontains=value)|Q(current_role__icontains=value)|
                         Q(company__icontains=value)|Q(specialty__icontains=value)|Q(domain__icontains=value)|Q(skills__icontains=value))
    def filter_available(self, qs, name, value):
        if value is None:
            return qs
        return qs.filter(is_available=True, has_active_mentee=False) if value else qs.exclude(is_available=True, has_active_mentee=False)


def directory_queryset():
    return mentor_queryset().filter(is_verified=True, is_discoverable=True, user__is_active=True, user__role='MENTOR')


@extend_schema(tags=['mentors'], summary='Discover Mentors: IIC-verified, published profiles only (paginated). '
               'A preference expressed from here never creates or confirms a mentorship.')
class MentorDirectoryView(generics.ListAPIView):
    serializer_class = MentorDirectorySerializer
    permission_classes = [IsApprovedStudentOrIIC]
    filterset_class = MentorDirectoryFilter
    def get_queryset(self):
        return directory_queryset().order_by('-is_available', 'has_active_mentee', '-experience_years', 'user_id')


@extend_schema(tags=['mentors'], summary='Directory facets: distinct domains, specialties, career paths and skills', responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([IsApprovedStudentOrIIC])
def mentor_facets(request):
    rows = list(directory_queryset().values('domain', 'specialty', 'career_path', 'skills'))
    collect = lambda key: sorted({r[key].strip() for r in rows if r[key] and r[key].strip()}, key=str.casefold)
    skills = sorted({s.strip() for r in rows for s in (r['skills'] or []) if isinstance(s, str) and s.strip()}, key=str.casefold)
    return Response({'domains': collect('domain'), 'specialties': collect('specialty'),
                     'career_paths': collect('career_path'), 'skills': skills})


@extend_schema(tags=['mentors'], summary='Discover Mentors: one directory profile (pk = user id)', responses=MentorDirectorySerializer)
@api_view(['GET'])
@permission_classes([IsApprovedStudentOrIIC])
def mentor_directory_detail(request, pk):
    return Response(MentorDirectorySerializer(get_object_or_404(directory_queryset(), user_id=pk)).data)


@extend_schema(tags=['mentors'], summary='IIC: email an activation invitation to a mentor (pk = user id)', request=None, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([IsIIC])
def invite_mentor(request,pk):
    """Email-only invitation, does not reveal activation token in API response."""
    from django.conf import settings
    from django.contrib.auth.tokens import default_token_generator
    from django.core.mail import send_mail
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode
    u=get_object_or_404(User,pk=pk,role='MENTOR')
    uid=urlsafe_base64_encode(force_bytes(u.pk))
    token=default_token_generator.make_token(u)
    link=f'{settings.SANGAM_FRONTEND_URL}/mentor/activate?uid={uid}&token={token}'
    send_mail('Sangam alumni mentor invitation',f'Activate your account: {link}',settings.DEFAULT_FROM_EMAIL,[u.email],fail_silently=False)
    AuditLog.objects.create(actor=request.user,action='MENTOR_INVITED',entity_type='User',entity_id=u.pk)
    return Response({'sent':True,'email':u.email,'activation_screen_required':True})

@extend_schema(tags=['auth'], summary='Mentor: activate an invited account by setting a password',
               request=inline_serializer('ActivateMentor', {'uid': serializers.CharField(), 'token': serializers.CharField(),
                                                             'password': serializers.CharField()}), responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AuthThrottle])
def activate_mentor(request):
    from django.contrib.auth.tokens import default_token_generator
    from django.contrib.auth.password_validation import validate_password
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    from rest_framework.exceptions import ValidationError
    try:
        uid=force_str(urlsafe_base64_decode(request.data.get('uid','')))
        u=User.objects.get(pk=uid,role='MENTOR')
    except (ValueError,TypeError,OverflowError,User.DoesNotExist):
        raise ValidationError('Invalid invitation.')
    if not default_token_generator.check_token(u,str(request.data.get('token',''))):
        raise ValidationError('Expired or invalid invitation.')
    pwd=request.data.get('password','')
    try:
        validate_password(pwd,user=u)
    except Exception as exc:
        raise ValidationError({'password': list(getattr(exc, 'messages', [str(exc)]))})
    u.set_password(pwd);u.save(update_fields=['password'])
    return Response({'activated':True})
