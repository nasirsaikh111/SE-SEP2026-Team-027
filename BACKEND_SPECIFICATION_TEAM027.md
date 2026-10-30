# Sangam · Backend Architecture & API Specification
**Prepared for:** Nasir (Backend Lead)  
**From:** Hemant (Frontend Lead / Tech Lead)  
**Project:** Sangam - Student Mentoring & Career Support Platform (IITM BS Degree SE Course - Team 027)  
**Live Frontend Prototype:** [https://sangam-step2.vercel.app](https://sangam-step2.vercel.app)  
**Frontend Stack:** Vue 3 + Pinia + Vue Router + Tailwind CSS  
**Target Backend Stack:** Django + Django REST Framework (DRF) + SQLite (as agreed in team architecture)

---

## 1. Executive Summary & Context

The frontend now has **Step 1, Step 2, and Step 3 fully operational and verified**.
- Step 1: Base setup, styling, shell.
- Step 2: Authentication simulation (Student, Mentor, Admin) & Student Dashboard with Pathway Compass.
- Step 3: Mentor Discovery with Match Scoring, Mentorship Request Submission (with 80-char min & max 3 limit), My Requests Tracking, and Student Mentorship Workspace (Goals, Sessions, Feedback).

All state is currently served via Pinia stores backed by deterministic mock data in `frontend/src/mock/data.js`.  
This document specifies the exact **Database Models**, **REST API Endpoints**, **JSON Payloads**, and **Business Logic Constraints** that the Django backend needs to implement so the frontend can seamlessly switch from mock stores to live Axios HTTP requests.

---

## 2. Relational Database Schema (SQLite / Django `models.py`)

Here is the exact schema design matching Nasir's High-Level Architecture Diagram:

### 2.1 Model: `User` (Extending AbstractUser or Custom User)
```python
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('mentor', 'Alumni Mentor'),
        ('admin', 'IIC Administrator'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    roll_number = models.CharField(max_length=30, blank=True, null=True, unique=True)
    graduation_year = models.IntegerField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

### 2.2 Model: `MentorProfile`
```python
# mentoring/models.py
from django.db import models
from django.conf import settings

class MentorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentor_profile')
    headline = models.CharField(max_length=255)
    company = models.CharField(max_length=120)
    job_role = models.CharField(max_length=120)
    domain = models.CharField(max_length=60) # e.g. "Data & ML", "Software", "Higher Studies", "Analytics"
    pathway = models.CharField(max_length=60) # e.g. "Industry", "Higher Studies", "Entrepreneurship"
    expertise = models.JSONField(default=list) # e.g. ["Python", "SQL", "Mock Interviews"]
    capacity = models.PositiveSmallIntegerField(default=2) # Max simultaneous mentees (typically 1 to 4)
    is_verified = models.BooleanField(default=False) # IIC Admin verification
    is_paused = models.BooleanField(default=False) # Mentor can pause incoming requests
    office_hours = models.JSONField(default=list) # e.g. ["Tue 6:30 PM", "Thu 6:30 PM"]
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    reviews_count = models.PositiveIntegerField(default=0)

    @property
    def active_mentees_count(self):
        return MentorshipPair.objects.filter(mentor=self.user, status='ACTIVE').count()

    @property
    def is_accepting_requests(self):
        return self.is_verified and not self.is_paused and (self.active_mentees_count < self.capacity)
```

### 2.3 Model: `MentorshipRequest`
```python
class MentorshipRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
        ('EXPIRED', 'Expired (7-Day Timeout)'),
    ]
    URGENCY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_requests')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_requests')
    domain = models.CharField(max_length=60)
    pathway = models.CharField(max_length=60)
    urgency = models.CharField(max_length=10, choices=URGENCY_CHOICES, default='Medium')
    question = models.TextField() # Min length validation rule: 80 chars
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    decline_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField() # Set to created_at + 7 days
```

### 2.4 Model: `MentorshipPair` & `Goal`
```python
class MentorshipPair(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active Mentorship'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_pairings')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentor_pairings')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    shared_notes = models.TextField(blank=True, default='')
    private_notes = models.TextField(blank=True, default='') # Only visible to mentor
    next_session_date = models.CharField(max_length=100, blank=True, null=True)
    next_session_link = models.URLField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)

class MentorshipGoal(models.Model):
    pair = models.ForeignKey(MentorshipPair, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    target_date = models.DateField(blank=True, null=True)
    is_completed = models.BooleanField(default=False)
```

### 2.5 Model: `MentorshipSession`
```python
class MentorshipSession(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('DONE', 'Completed'),
        ('NO_SHOW', 'No Show'),
        ('CANCELLED', 'Cancelled'),
    ]
    pair = models.ForeignKey(MentorshipPair, on_delete=models.CASCADE, related_name='sessions')
    scheduled_for = models.CharField(max_length=100) # e.g. "Thu, 31 Oct 2026, 6:30 PM"
    duration = models.CharField(max_length=30, default='45 mins')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DONE')
    notes = models.TextField(blank=True, default='')
    rating_given = models.PositiveSmallIntegerField(blank=True, null=True) # 1 to 5 stars
```

### 2.6 Model: `AuditLog`
```python
class AuditLog(models.Model):
    actor = models.CharField(max_length=100) # e.g. "admin", "system", username
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

---

## 3. Core REST API Endpoints Specification

Base URL: `/api/v1/`

### 3.1 Authentication & Profile
- `POST /api/v1/auth/login/`
  - **Body:** `{ "username": "...", "password": "..." }`
  - **Response (200):** `{ "token": "...", "user": { "id": 1, "username": "...", "name": "...", "role": "student|mentor|admin", "rollNo": "..." } }`
- `GET /api/v1/auth/me/`
  - Returns authenticated user details and profile.

### 3.2 Mentors & Discovery (For Students)
- `GET /api/v1/mentors/`
  - **Query Params:** `?domain=Data%20&%20ML&pathway=Industry&verified=true`
  - **Response (200):**
    ```json
    [
      {
        "id": "mentor-1",
        "name": "Arjun K.",
        "role": "Senior Data Scientist",
        "company": "Fractal Analytics",
        "domain": "Data & ML",
        "pathway": "Industry",
        "gradYear": 2024,
        "rollNo": "21f1001234",
        "headline": "Foundation → Analyst → Data Scientist at Fractal",
        "expertise": ["Data Science", "Machine Learning", "SQL", "Mock Interviews"],
        "rating": 4.8,
        "reviewsCount": 11,
        "capacity": 3,
        "activeMentees": 1,
        "verified": true,
        "paused": false,
        "officeHours": ["Tue 6:30 PM", "Thu 6:30 PM"],
        "matchScore": 92,
        "matchReason": "Direct match on Data & ML, Industry pathway"
      }
    ]
    ```

### 3.3 Mentorship Requests (Student & Mentor)
- `GET /api/v1/requests/`
  - Returns requests sent by student OR received by mentor.
  - Filterable by `?status=PENDING|ACCEPTED|DECLINED`.
- `POST /api/v1/requests/`
  - **Student creates a request.**
  - **Body:**
    ```json
    {
      "mentorId": "mentor-1",
      "domain": "Data & ML",
      "pathway": "Industry",
      "urgency": "High",
      "question": "Should I prioritize taking an entry-level data analyst internship right now, or finish all Diploma ML courses and build 2 full-stack capstones first?"
    }
    ```
  - **Validation Rules (Must return 400 if violated):**
    1. `question` length **must be $\ge$ 80 characters**.
    2. Student cannot have more than **3 active/pending requests** at a time.
    3. Mentor must be verified and not paused.
- `POST /api/v1/requests/{id}/accept/`
  - Mentor accepts request $\rightarrow$ Creates active `MentorshipPair`.
- `POST /api/v1/requests/{id}/decline/`
  - **Body:** `{ "reason": "At maximum capacity for this term" }`
  - Updates status to `DECLINED` and logs decline reason.

### 3.4 Active Workspace & Sessions
- `GET /api/v1/workspace/`
  - Returns current active pair, goals list, session history, and next scheduled session.
- `POST /api/v1/workspace/goals/`
  - **Body:** `{ "title": "Audit GitHub portfolio", "targetDate": "2026-11-15" }`
- `PATCH /api/v1/workspace/goals/{id}/`
  - **Body:** `{ "completed": true }`
- `POST /api/v1/workspace/sessions/`
  - Logs a completed session with date, duration, notes.

---

## 4. Key Business Logic Rules for Nasir

1. **Pathway Compass Validation:**
   - Mentoring requests **require at least 80 characters** explaining context, background, and specific dilemma. Reject anything shorter with an explicit validation error: `"Question must be at least 80 characters"`.
2. **Request Cap:**
   - A mentee is restricted to at most **3 concurrent pending requests** to prevent mass spamming alumni mentors.
3. **Auto-Expiry Window:**
   - Requests have a **7-day lifespan**. If a mentor does not respond within 7 days, a cron/celery task or query check should mark them as `EXPIRED`.
4. **Mentor Capacity & Privacy:**
   - Mentors specify a capacity (typically 1 to 3 concurrent students). Once filled, the mentor should be labeled as full or hidden from immediate discovery.
   - Private notes in the workspace must never be visible to the student.

---

## 5. Verification & Testing Instructions for Backend

1. Verify models with `python manage.py makemigrations && python manage.py migrate`.
2. Create superuser: `python manage.py createsuperuser` to access Django admin dashboard.
3. Test endpoints with `curl` or Postman, checking the exact JSON key names documented above.
4. Hemant can configure Axios in `src/api/client.js` with base URL `http://127.0.0.1:8000/api/v1/` to connect directly to Nasir's server.

---
