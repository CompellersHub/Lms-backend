from .models import CustomUser
from rest_framework.permissions import BasePermission

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return ( 
        request.user.is_authenticated and 
        request.user.role == CustomUser.ROLE.ADMIN and
        request.user.has_perm('Assign_teaching_position', 'edit_course_notes', 'edit_course_notes',
                              'view_payments', 'add_students_to_course', 'edit_students_in-course',
                              'view_students_progress', 'view_attendance_records')
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == CustomUser.ROLE.TEACHER and
            request.user.has_perm('create_course_notes', 'create_course_videos', 'edit_course_notes',
                                   'make_assignments', 'add_students_to_course', 'view_students_in_course',
                                   'edit_students_in_course', 'view_student_progress', 'view_attendance_records',
                                   'view_course')
        )
    


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == CustomUser.ROLE.STUDENT and
            request.user.has_perm('view_course', 'view_student_progress', 'view_assignments', 'view_course')
        )
