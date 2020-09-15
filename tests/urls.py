from django.conf.urls import url
from tests import views

urlpatterns = [
    url(r'^teachers/(?P<id>[0-9a-f-]+)/$', view=views.TeacherDetailView.as_view(), name='teacher-detail'),
    url(r'^teachers/$', view=views.TeacherListView.as_view(), name='teacher-list'),
    url(r'^students/(?P<id>[0-9a-f-]+)/$', view=views.StudentDetailView.as_view(), name='student-detail'),
    url(r'^classes/(?P<id>[0-9a-f-]+)/$', view=views.ClassDetailView.as_view(), name='class-detail'),
    url(r'^subjects/(?P<id>[0-9a-f-]+)/$', view=views.SubjectDetailView.as_view(), name='subject-detail'),
    url(r'^schools/(?P<id>[0-9a-f-]+)/$', view=views.SchoolDetailView.as_view(), name='school-detail'),
    url(r'^students-detail/(?P<id>[0-9a-f-]+)/$', view=views.StudentWithAssignmentsDetailView.as_view(), name='student-with-assignments-detail'),
    url(r'^assignments/(?P<id>[0-9a-f-]+)/$', view=views.AssignmentDetailView.as_view(), name='assignment-detail'),
    url(r'^students-with-classes-and-assignments/(?P<id>[0-9a-f-]+)/$', view=views.StudentWithClassesAndAssignmentsDetailView.as_view(), name='student-with-classes-and-assignments-detail'),
    url(r'^misconfigured/$', view=views.MisconfiguredView.as_view(), name='misconfigured'),
]
