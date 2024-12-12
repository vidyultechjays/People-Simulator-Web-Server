"""
This module defines the models for the simulator application.

It includes:
- Persona: Represents an individual with demographic and personality traits.
- NewsItem: Represents news articles that can elicit emotional responses.
- EmotionalResponse: Links personas to news items with emotional reactions.
- AggregateEmotion: Summarizes emotional responses for a news item.
"""
from django.db import models

class Category(models.Model):
    """
    Represents a demographic category.
    """
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    """
    Represents a demographic subcategory under a category.
    """
    category = models.ForeignKey(Category, related_name='subcategories', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.category})"

class Persona(models.Model):
    """
    Represents a persona with demographic attributes.
    """
    name = models.CharField(max_length=100)
    city = models.CharField(max_length=255,blank=True, null=True)
    personality_traits = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.name} ({self.city})"

class PersonaSubCategoryMapping(models.Model):
    """
    Maps personas to their specific subcategories.
    """
    persona = models.ForeignKey(Persona, related_name='subcategory_mappings', on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, related_name='personas', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.persona.name} - {self.subcategory.name}"


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
    Model to store aggregate emotional responses with demographic breakdown
    """
    news_item = models.ForeignKey('NewsItem', on_delete=models.CASCADE)
    city = models.CharField(max_length=255,blank=True, null=True)
    summary = models.JSONField(default=dict)  # Overall summary
    demographic_summary = models.JSONField(default=dict,blank=True, null=True)  # Detailed demographic breakdown
    created_at = models.DateTimeField(auto_now_add=True,blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True,blank=True, null=True)

    def __str__(self):
        return f"{self.city} - {self.news_item}"
 