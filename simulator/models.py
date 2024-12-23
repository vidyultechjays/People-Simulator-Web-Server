"""
This module defines the models for the simulator application, which simulates the emotional impact of news items on various personas.

Models included:
1. **Category**: 
   - Represents a demographic category (e.g., Age, Income, Religion).
   - Includes optional city-specific information.

2. **SubCategory**: 
   - Represents a demographic subcategory under a specific category.
   - Includes percentage distribution and optional city-specific information.

3. **Persona**: 
   - Represents an individual persona with attributes such as name, city, and a description of their personality traits.

4. **PersonaSubCategoryMapping**: 
   - Maps personas to their associated subcategories for demographic alignment.

5. **NewsItem**: 
   - Represents a news article with attributes like title, content, and upload date.

6. **AggregateEmotion**: 
   - Stores aggregated emotional responses to a news item, broken down by city and demographics.
   - Includes timestamps and JSON fields for detailed summaries.

7. **PersonaGenerationTask**: 
   - Tracks the status of persona generation tasks for a city based on its population.
   - Supports statuses like pending, in-progress, completed, and failed.

8. **PossibleUserResponses**: 
   - Represents predefined possible user responses to a specific news item.

9. **EmotionalResponse**: 
   - Represents an emotional response or user reaction by a Persona to a specific NewsItem.
   - Links to PossibleUserResponses for predefined reactions and includes intensity and explanations.

Each model has descriptive methods for string representation to ensure clarity when interacting with instances in the admin interface or during debugging.
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
    # personality_traits = models.JSONField(default=dict)
    personality_description = models.TextField(blank=True, null=True)

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

class AggregateEmotion(models.Model):
    """
    Model to store aggregate emotional responses with demographic breakdown
    """
    news_item = models.ForeignKey('NewsItem', on_delete=models.CASCADE)
    city = models.CharField(max_length=255,blank=True, null=True)
    summary = models.JSONField(default=dict)
    demographic_summary = models.JSONField(default=dict,blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True,blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True,blank=True, null=True)

    def __str__(self):
        return f"{self.city} - {self.news_item}"

class PersonaGenerationTask(models.Model):
    """
    Model to track persona generation tasks
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ]

    city_name = models.CharField(max_length=100)
    population = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.city_name} - {self.status}"

class PossibleUserResponses(models.Model):
    """
    Represents possible user responses for a specific news item.
    """
    news_item = models.ForeignKey(NewsItem, on_delete=models.CASCADE, related_name='possible_responses')
    response_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.response_text[:50]}"

class EmotionalResponse(models.Model):
    """
    Represents a response by a Persona to a specific NewsItem.
    Now includes user response selection instead of emotion.
    """
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    news_item = models.ForeignKey(NewsItem, on_delete=models.CASCADE)
    user_response = models.ForeignKey(PossibleUserResponses, on_delete=models.CASCADE,blank=True, null=True)
    intensity = models.FloatField()
    explanation = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Response of {self.persona} to {self.news_item}: {self.user_response} ({self.intensity})"

class LLMModelAndKey(models.Model):
    """
    Represents an LLM model and its API key, with additional details.
    """
    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('google', 'Google Generative AI'),
    ]

    model_name = models.CharField(max_length=100)
    active = models.BooleanField(choices=[(True, 'True'), (False, 'False')], default=False)
    provider_name = models.CharField(max_length=50, choices=PROVIDER_CHOICES)

    def __str__(self):
        return f"{self.provider_name} ({self.model_name}) - {'Active' if self.active else 'Inactive'}"
    
    def save(self, *args, **kwargs):
        if self.active:
            LLMModelAndKey.objects.exclude(id=self.id).update(active=False)

        super().save(*args, **kwargs)

class PromptModel(models.Model):
    """
    Represents a reusable prompt template for various tasks.
    """
    TASK_CHOICES = [
        ('personality_description', 'Personality Description'),
        ('generate_user_response', 'Generate User Response'),
        # Add more tasks here if needed
    ]

    task_name = models.CharField(
        max_length=50,
        choices=TASK_CHOICES,
        default='personality_description',
        unique=True
    )
    prompt_template = models.TextField(
        help_text="Enter the prompt with placeholders for dynamic fields like {name}, {city}, and {context}."
    )
    version = models.CharField(
        max_length=50,
        help_text="Enter a version identifier (e.g., 'Elaborate', 'Concise', '3 lines')."
    )

    def __str__(self):
        return f"{self.task_name} (Version: {self.version})"
