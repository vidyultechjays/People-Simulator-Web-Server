"""
This module registers the models with the Django admin site.
"""

from django.contrib import admin
from simulator.models import Persona,EmotionalResponse,NewsItem,AggregateEmotion,Category,SubCategory,PersonaSubCategoryMapping

admin.site.register(Persona)
admin.site.register(Category)
admin.site.register(SubCategory)
admin.site.register(PersonaSubCategoryMapping)
admin.site.register(EmotionalResponse)
admin.site.register(NewsItem)
admin.site.register(AggregateEmotion)

# class CategoryAdmin(admin.ModelAdmin):
#     list_display = ('id', 'name', 'city')  # Add 'id' to the list of displayed fields

# admin.site.register(Category, CategoryAdmin)