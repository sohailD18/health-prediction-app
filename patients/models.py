from django.db import models


class Patient(models.Model):
    """One patient record with blood test values and the AI-generated remarks."""

    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    email = models.EmailField(unique=True)
    glucose = models.FloatField()
    haemoglobin = models.FloatField()
    cholesterol = models.FloatField()
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.email})"