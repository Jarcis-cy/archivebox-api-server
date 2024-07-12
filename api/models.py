from django.db import models
import uuid


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Target(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField(max_length=2000)
    domain = models.CharField(max_length=100)
    timestamp = models.FloatField()


class Result(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.FloatField()
    start_ts = models.DateTimeField()
    end_ts = models.DateTimeField()
    status = models.BooleanField(default=False)
    output = models.TextField()
    target_id = models.ForeignKey(Target, on_delete=models.CASCADE)
    extractor = models.CharField(max_length=100)


class Tag(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)


class TargetTag(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tag_id = models.ForeignKey(Tag, on_delete=models.CASCADE)
    target_id = models.ForeignKey(Target, on_delete=models.CASCADE)
