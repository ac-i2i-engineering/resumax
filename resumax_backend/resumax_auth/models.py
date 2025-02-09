from django.db import models
from django.contrib.auth.models import User
import uuid

class PasswordReset(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    reset_id = models.UUIDField(default=uuid.uuid4, editable=False)
    creation_time = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Password reset for {self.user.username} at {self.creation_time}"