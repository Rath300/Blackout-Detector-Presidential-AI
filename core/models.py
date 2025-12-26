from django.db import models
from django.contrib.auth.models import User


class UploadedFile(models.Model):
    """Store uploaded CSV file metadata"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    file = models.FileField(upload_to='uploads/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.IntegerField(help_text="File size in bytes")
    rows_count = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.filename} - {self.uploaded_at}"
    
    class Meta:
        ordering = ['-uploaded_at']


class AnalysisSession(models.Model):
    """Store analysis parameters and results"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, unique=True)
    uploaded_file = models.ForeignKey(UploadedFile, on_delete=models.CASCADE, null=True, blank=True)
    contamination = models.FloatField(default=0.02)
    forecast_model = models.CharField(max_length=50, default='gradient_boosting')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session {self.session_key} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']
