from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .models import User, StudentProfile, MentorProfile
from .permissions import IsIIC, IsVerifiedMentor
from .serializers import StudentRegistrationSerializer, MeSerializer, StudentProfileSerializer, StudentReviewSerializer, MentorCreateSerializer, MentorProfileSerializer
from apps.mentoring.models import AuditLog, Notification

class RegisterView(generics.CreateAPIView):
    serializer_class = StudentRegistrationSerializer
    permission_classes = [AllowAny]
    def create(self,request,*args,**kwargs):
        s=self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        u=s.save()
        return Response({'id':u.pk,'approval_status':'PENDING','message':'IIC approval required.'},status=201)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(MeSerializer(request.user).data)

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

@api_view(['GET'])
@permission_classes([IsIIC])
def pending_students(request):
    state=request.query_params.get('status','PENDING')
    qs=StudentProfile.objects.select_related('user').filter(approval_status=state).order_by('created_at')
    return Response([{'id':p.pk,'user_id':p.user_id,'email':p.user.email,'name':p.user.get_full_name(),**StudentProfileSerializer(p).data} for p in qs[:200]])

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

@api_view(['GET','POST'])
@permission_classes([IsIIC])
def mentors(request):
    if request.method=='GET':
        qs=MentorProfile.objects.select_related('user').all().order_by('id')[:200]
        return Response([{'email':m.user.email,**MentorProfileSerializer(m).data} for m in qs])
    s=MentorCreateSerializer(data=request.data,context={'request':request})
    s.is_valid(raise_exception=True)
    u=s.save()
    AuditLog.objects.create(actor=request.user,action='MENTOR_ADDED',entity_type='MentorProfile',entity_id=u.mentor_profile.id)
    return Response({'id':u.id,'email':u.email,'is_verified':False,'activation':'IIC must invite mentor to set a password.'},status=201)

@api_view(['POST'])
@permission_classes([IsIIC])
def verify_mentor(request,pk):
    m=get_object_or_404(MentorProfile,user_id=pk)
    if not m.alumni_roll_number or not m.graduation_year:
        raise ValidationError('Verify alumni roll number and graduation year against authorized IIC records first.')
    m.is_verified=True;m.save(update_fields=['is_verified'])
    AuditLog.objects.create(actor=request.user,action='MENTOR_VERIFIED',entity_type='MentorProfile',entity_id=m.pk)
    return Response({'mentor_id':pk,'is_verified':True})

@api_view(['PATCH'])
@permission_classes([IsVerifiedMentor])
def mentor_availability(request):
    value=request.data.get('is_available')
    if not isinstance(value,bool): return Response({'detail':'is_available must be a boolean.'},status=400)
    MentorProfile.objects.filter(user=request.user).update(is_available=value)
    return Response({'is_available':value})

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
    return Response({'sent':True,'email':u.email,'activation_screen_required':True})

@api_view(['POST'])
@permission_classes([AllowAny])
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
    validate_password(pwd,user=u)
    u.set_password(pwd);u.save(update_fields=['password'])
    return Response({'activated':True})
