from django.db import models
from django.contrib.auth.models import User
import uuid
class PasswordReset(models.Model):
    '''
    PasswordReset model to store password reset requests.
    
    This model provides the structure for storing password reset request ID that will be 
    used to verify if the user request exists or has no timed out.
    
    '''
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    reset_id = models.UUIDField(default=uuid.uuid4, editable=False)
    creation_time = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Password reset for {self.user.username} at {self.creation_time}"