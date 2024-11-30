"""
This module defines the models for the simulator application.

It includes:
- Persona: Represents an individual with demographic and personality traits.
- NewsItem: Represents news articles that can elicit emotional responses.
- EmotionalResponse: Links personas to news items with emotional reactions.
- AggregateEmotion: Summarizes emotional responses for a news item.
"""
from django.db import models

class Persona(models.Model):
    """
    Represents an individual with demographic details and personality traits.
    """
    AGE_GROUP_CHOICES = [
        ('18-25', '18-25'),
        ('26-40', '26-40'),
        ('41-60', '41-60'),
        ('60+', '60+'),
    ]
    INCOME_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    RELIGION_CHOICES = [
        ('hindu', 'Hindu'),
        ('muslim', 'Muslim'),
        ('christian', 'Christian'),
        ('others', 'Others'),
    ]
    name = models.CharField(max_length=100)
    age_group = models.CharField(max_length=10, choices=AGE_GROUP_CHOICES)
    city = models.CharField(max_length=255,blank=True, null=True)
    income_level = models.CharField(max_length=10, choices=INCOME_LEVEL_CHOICES)
    religion = models.CharField(max_length=20, choices=RELIGION_CHOICES)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    personality_traits = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} ({self.city}, {self.age_group}, {self.income_level}, {self.religion})"

class NewsItem(models.Model):
    """
    Represents a news article with a title, content, and upload date.
    """
    title = models.CharField(max_length=255)
    content = models.TextField()
    upload_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(f"News about {self.title}")

class EmotionalResponse(models.Model):
    """
    Represents an emotional response by a Persona to a specific NewsItem.
    Includes the type and intensity of emotion, as well as an optional explanation.
    """
    EMOTION_CHOICES = [
        ('joy', 'Joy'),
        ('sadness', 'Sadness'),
        ('anger', 'Anger'),
        ('fear', 'Fear'),
        ('disgust', 'Disgust'),
        ('surprise', 'Surprise'),
        ('optimism', 'Optimism'),
        ('anxiety', 'Anxiety'),
        ('compassion', 'Compassion'),
        ('outrage', 'Outrage'),
    ]
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    news_item = models.ForeignKey(NewsItem, on_delete=models.CASCADE)
    emotion = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    intensity = models.FloatField()
    explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Response of {self.persona} to {self.news_item}: {self.emotion} ({self.intensity})"

class AggregateEmotion(models.Model):
    """
    Represents a summary of emotional responses for a specific NewsItem.
    Stores a JSON representation of aggregated emotions.
    """
    news_item = models.ForeignKey(NewsItem, on_delete=models.CASCADE)
    summary = models.JSONField(default=dict)

    def __str__(self):
        return f"Aggregate Emotion for {self.news_item}"
