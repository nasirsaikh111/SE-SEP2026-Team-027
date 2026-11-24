Accounts API test summary
Run date: 2026-11-23T18:57:24
Total: 20 | Passed: 19 | Failed: 1 | Exit code: 1
Original case IDs: TC-01, TC-02, TC-03, TC-04, TC-05, TC-06, TC-07, TC-08, TC-09, TC-10, TC-11, TC-12, TC-13, TC-14, TC-15, TC-16, TC-17, TC-18, TC-19, TC-25
No test methods overlap with the other test set.

Run from this folder:
  python -m pytest -c pytest.ini test_api.py --junitxml=results.xml

Source: test_api.py
Pytest configuration: pytest.ini
Verbose output: output.txt
Machine-readable results: results.xml
Case inventory: cases.json
PDF: report.pdf

The PDF actual outputs summarize assertions verified by this fresh pytest run.
They are not raw captured response JSON. No response fields are invented.
Tests use an isolated SQLite database and in-memory email, not a deployed server.
Shared fixtures/helpers are repeated in each module so either suite runs alone.
The mentor import case checks the current stub response only.

Failure: TC-25 returns HTTP 500 for weak activation password; HTTP 400 expected.
Assertions following the failing status check were not reached. API code is unchanged.

Case results:
D1-01 / TC-01 | PASS | test_registration_creates_pending_student_and_hashes_password
D1-02 / TC-02 | PASS | test_registration_rejects_invalid_inputs_without_creating_users
D1-03 / TC-03 | PASS | test_registration_rejects_duplicate_email_case_insensitively
D1-04 / TC-04 | PASS | test_jwt_login_authenticated_me_and_refresh
D1-05 / TC-05 | PASS | test_login_rejects_wrong_password
D1-06 / TC-06 | PASS | test_protected_routes_reject_anonymous_requests
D1-07 / TC-07 | PASS | test_admin_routes_reject_student
D1-08 / TC-08 | PASS | test_student_reads_and_edits_own_profile
D1-09 / TC-09 | PASS | test_approved_student_records_are_locked
D1-10 / TC-10 | PASS | test_rejected_student_edit_resets_review
D1-11 / TC-11 | PASS | test_nonstudent_cannot_access_student_profile
D1-12 / TC-12 | PASS | test_admin_student_list_search_and_status_filter
D1-13 / TC-13 | PASS | test_student_approval_persists_audit_and_notification
D1-14 / TC-14 | PASS | test_student_review_rejects_missing_verification_or_reason
D1-15 / TC-15 | PASS | test_approval_rejects_incomplete_academic_records
D1-16 / TC-16 | PASS | test_student_rejection_records_reason
D1-17 / TC-17 | PASS | test_admin_creates_unverified_mentor_with_unusable_password
D1-18 / TC-18 | PASS | test_admin_mentor_list_filters
D1-19 / TC-19 | PASS | test_mentor_verification_requires_alumni_records
D1-20 / TC-25 | FAIL | test_activation_weak_password_returns_validation_error_not_server_error

The ZIP uses backend-relative paths. Extract it into an existing project backend,
then run the command above from this folder.
