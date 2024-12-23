"""
This module registers the models with the Django admin site.
"""

from django.contrib import admin
from simulator.models import (
    Persona,
    EmotionalResponse,
    NewsItem,
    AggregateEmotion,
    Category,
    SubCategory,
    PersonaSubCategoryMapping,
    PersonaGenerationTask,
    PossibleUserResponses,
    LLMModelAndKey,
    PromptModel
)
admin.site.register(Persona)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(PersonaSubCategoryMapping)
admin.site.register(EmotionalResponse)
admin.site.register(NewsItem)
admin.site.register(AggregateEmotion)
admin.site.register(PersonaGenerationTask)
admin.site.register(PossibleUserResponses)
admin.site.register(LLMModelAndKey)
admin.site.register(PromptModel)


