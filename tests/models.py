from django.db import models
import uuid


class Entity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LEA(Entity):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class School(Entity):
    name = models.CharField(max_length=255)
    lea = models.ForeignKey(LEA, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Teacher(Entity):
    name = models.CharField(max_length=255)
    school = models.ForeignKey(School, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Subject(Entity):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Class(Entity):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Assignment(Entity):
    name = models.CharField(max_length=255)
    clasz = models.ForeignKey(Class, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class AssignmentStudent(Entity):
    is_complete = models.BooleanField(default=False)
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    student = models.ForeignKey('Student', on_delete=models.CASCADE)

    def __str__(self):
        return '%s for %s: %s' % (self.assignment, self.student, 'complete' if self.is_complete else 'not complete')


class Student(Entity):
    name = models.CharField(max_length=255)
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    classes = models.ManyToManyField(Class)
    assignments = models.ManyToManyField(Assignment, through=AssignmentStudent, related_name='assignees')

    def __str__(self):
        return self.name
