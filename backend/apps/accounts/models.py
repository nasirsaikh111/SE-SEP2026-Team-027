from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("Superuser must have staff and superuser permissions")
        if extra_fields["role"] != "ADMIN":
            raise ValueError("Superuser must have the ADMIN role")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        MENTOR = "MENTOR", "Mentor"
        ADMIN = "ADMIN", "IIC Administrator"
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20,choices=Role.choices,default=Role.STUDENT)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()
    def __str__(self):
        return self.email


class StudentProfile(models.Model):
    class Level(models.TextChoices):
        DIPLOMA = "DIPLOMA", "Diploma"
        DEGREE = "DEGREE", "Degree"
    class ApprovalStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="student_profile")
    iitm_roll_number = models.CharField(max_length=50)
    level = models.CharField(max_length=20,choices=Level.choices)
    courses = models.JSONField(default=list, blank=True)
    cgpa = models.DecimalField(max_digits=4,decimal_places=2,null=True,blank=True,validators=[MinValueValidator(0),MaxValueValidator(10),])
    approval_status = models.CharField(max_length=20,choices=ApprovalStatus.choices,default=ApprovalStatus.PENDING)
    rejection_reason = models.TextField(blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="approved_students")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.user_id:
            if self.user.role != User.Role.STUDENT:
                raise ValidationError("User must have STUDENT role.")
            domain = self.user.email.lower().rsplit("@", 1)[-1]
            if domain != "iitm.ac.in" and not domain.endswith(".iitm.ac.in"):
                raise ValidationError("An IITM email address is required.")
    def __str__(self):
        return self.user.email

class MentorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="mentor_profile")
    alumni_roll_number = models.CharField(max_length=50,blank=True)
    graduation_year = models.PositiveIntegerField(null=True,blank=True)
    domain = models.CharField(max_length=150)
    specialty = models.CharField(max_length=200)
    current_role = models.CharField(max_length=150)
    company = models.CharField(max_length=150, blank=True)
    career_path = models.CharField(max_length=150, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name="invited_mentors")
    created_at = models.DateTimeField(auto_now_add=True)
    def clean(self):
        if self.user_id and self.user.role != User.Role.MENTOR:
            raise ValidationError("User must have MENTOR role.")
    def __str__(self):
        return self.user.email