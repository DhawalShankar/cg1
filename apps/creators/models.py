import uuid
from django.db import models

class Creator(models.Model):
    id         = models.UUIDField(primary_key=True)
    profile_id = models.CharField(max_length=255)

    class Meta:
        db_table = "creators"
        managed  = False