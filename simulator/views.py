"""
This module manages persona generation, emotional impact assessment, and response aggregation for analyzing the influence of news items on diverse demographics.

**Features:**
1. **Persona Generation**: 
   - Generates personas based on user-provided demographic inputs, such as age, religion, personality traits, and income levels.
   - Personas are weighted to match population distributions and are stored in the database for analysis.

2. **Emotional Impact Assessment**: 
   - Analyzes how news items affect personas' emotions (e.g., positive, negative, or neutral).
   - Generates emotional responses for each persona, including emotion type, intensity, and a contextual explanation.
   - Filters responses by city or selected personas.

3. **Response Aggregation**: 
   - Aggregates emotional responses by demographics (age, income, religion) and city.
   - Summarizes emotional trends across personas for a given news item.

4. **Results Visualization**: 
   - Provides detailed, user-friendly visualizations (pie charts, bar charts) of emotional distributions and intensities.
   - Displays summaries grouped by city and demographics.

5. **Dynamic Data Access**:
   - API endpoints for retrieving real-time summaries and sample persona profiles with their corresponding emotional responses.

**Primary Use Case**:
Enables city-specific and demographic-focused emotional analysis of user-provided news items, supporting detailed insights into the impact on different groups.
"""
import json
import logging
from urllib.parse import unquote
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count,Avg
from faker import Faker
from simulator.models import Persona,Category,SubCategory,PersonaSubCategoryMapping,EmotionalResponse,NewsItem,AggregateEmotion
from simulator.utils.persona_helper import (
    generate_persona_traits,
    validate_demographics,
    get_occupation_by_income,
)
from simulator.utils.impact_assesment_helper import generate_emotional_response
from simulator.utils.results_visualization_helper import (
    create_emotion_intensity_bar_chart,
    create_pie_chart
)
from simulator.tasks import aggregate_emotion_task


logger = logging.getLogger(__name__)

def results_summary(request):
    """
    Display detailed emotional summary with demographic breakdowns
    """
    news_item_title = request.session.get('news_item')
    city_name = request.session.get('city_name')

    try:
        aggregate_emotion = AggregateEmotion.objects.get(
            city=city_name,
            news_item__title=news_item_title
        )
        charts = {}

        if aggregate_emotion.summary and aggregate_emotion.summary.get('total', 0) > 0:
            overall_data = [
                {'emotion': 'Positive', 'count': aggregate_emotion.summary.get('positive_percentage', 0)},
                {'emotion': 'Negative', 'count': aggregate_emotion.summary.get('negative_percentage', 0)},
                {'emotion': 'Neutral', 'count': aggregate_emotion.summary.get('neutral_percentage', 0)}
            ]
            charts['overall'] = create_pie_chart(
                overall_data,
                f'Overall Emotion Distribution in {city_name}'
            )

        demographic_summary = aggregate_emotion.demographic_summary

        def create_demographic_charts(category_type, categories):
            category_charts = {}
            for category, data in categories.items():
                if data.get('total', 0) > 0:
                    chart_data = [
                        {'emotion': 'Positive', 'count': data.get('positive_percentage', 0)},
                        {'emotion': 'Negative', 'count': data.get('negative_percentage', 0)},
                        {'emotion': 'Neutral', 'count': data.get('neutral_percentage', 0)}
                    ]
                    category_charts[category] = create_pie_chart(
                        chart_data,
                        f'{category_type.replace("_", " ").title()} - {category}'
                    )
            return category_charts

        for category_type, categories in demographic_summary.items():
            charts.update(create_demographic_charts(category_type, categories))

        sample_personas = {}

        # def get_sample_personas(category_type, categories):
        #     """
        #     Retrieve sample personas for each demographic category
        #     """
        #     sample_personas_dict = {}
        #     for category, data in categories.items():
        #         if data.get('total', 0) > 0:
        #             # Use the relationship between Persona and Subcategory
        #             filter_kwargs = {
        #                 'city': city_name,
        #                 'subcategory_mappings__subcategory__category__name': category_type,  # Filter by category type
        #                 'subcategory_mappings__subcategory__name': category  # Filter by specific subcategory
        #             }

        #             personas = Persona.objects.filter(**filter_kwargs)

        #             sample_personas_dict[category] = list(personas[:10])  # Get a sample of 10 personas

        #     return sample_personas_dict 

    except AggregateEmotion.DoesNotExist:
        aggregate_emotion = None
        charts = {}
        sample_personas = {}

    print("Summary Data:", aggregate_emotion.summary)

    return render(request, "results_summary.html", {
        "summary": aggregate_emotion.summary if aggregate_emotion else {},
        "demographic_summary": aggregate_emotion.demographic_summary if aggregate_emotion else {},
        "news_item": news_item_title,
        "city_name": city_name,
        "charts": charts,
        "sample_personas": sample_personas,
    })

def persona_input(request):
    if request.method == "POST":
        city_name = request.POST.get("city_name")
        population = int(request.POST.get("population"))
        request.session["city_name"] = city_name
        request.session["population"] = population
        return redirect("demographics_input")
    return render(request, "persona_input.html")

def demographics_input(request):
    if request.method == "POST":
        data = request.POST.dict()
        categories = {}

        for key, value in data.items():
            if key.startswith("category_"):
                _, category_id = key.split("_", 1)
                if category_id not in categories:
                    categories[category_id] = {"name": value, "subcategories": []}

            elif key.startswith("subcategory_"):
                _, category_id, sub_id = key.split("_", 2)
                subcategory_name = value
                percentage_key = f"percentage_{category_id}_{sub_id}"
                percentage = float(data.get(percentage_key, 0))
                categories[category_id]["subcategories"].append(
                    {"name": subcategory_name, "percentage": percentage}
                )

        for category_id, category_data in categories.items():
            total_percentage = sum(sub["percentage"] for sub in category_data["subcategories"])
            if total_percentage != 100:
                messages.error(
                    request,
                    f"Subcategory percentages for '{category_data['name']}' must sum to 100. Current total: {total_percentage}."
                )
                return redirect("demographics_input")

        saved_categories = []
        city_name = request.session.get("city_name")

        if not city_name:
            messages.error(request, "City name is required. Please start from the beginning.")
            return redirect("persona_input")

        # Create and save categories with city
        for category_data in categories.values():
            category = Category.objects.create(
                name=category_data["name"],
                city=city_name  # Associate category with city
            )
            saved_categories.append(category)
            for subcategory_data in category_data["subcategories"]:
                SubCategory.objects.create(
                    name=subcategory_data["name"],
                    percentage=subcategory_data["percentage"],
                    category=category,
                )

        city_name = request.session.get("city_name")
        population = request.session.get("population")

        if not city_name or not population:
            messages.error(request, "City name and population are required. Please start from the beginning.")
            return redirect("persona_input")

        def generate_personas_with_weights(population, city_name, saved_categories):
            faker = Faker()
            personas = []
            all_combinations = []

            def generate_all_subcategory_combinations(categories):
                """Generate all possible subcategory combinations."""
                from itertools import product
                
                # Collect subcategories for each category
                category_subcategories = {}
                for category in categories:
                    category_subcategories[category.name] = list(category.subcategories.all())
                
                # Generate all possible combinations of subcategories
                keys = list(category_subcategories.keys())
                combinations = list(product(*[category_subcategories[key] for key in keys]))
                
                return combinations

            # Generate all possible subcategory combinations
            subcategory_combinations = generate_all_subcategory_combinations(saved_categories)

            # Calculate weights for each combination
            combination_weights = []
            for combination in subcategory_combinations:
                weight = population
                for subcategory in combination:
                    weight *= (subcategory.percentage / 100)
                combination_weights.append({
                    'combination': combination,
                    'weight': weight
                })

            # Sort combinations by fractional part of weight to distribute personas more evenly
            combination_weights.sort(key=lambda x: x['weight'] % 1, reverse=True)

            # Generate personas
            total_assigned = 0
            for combo_data in combination_weights:
                combination = combo_data['combination']
                exact_count = round(combo_data['weight'])
                
                if total_assigned + exact_count > population:
                    exact_count = population - total_assigned

                # Create personas for this combination
                for _ in range(exact_count):
                    persona = Persona(
                        name=faker.name(),
                        city=city_name,
                        personality_traits=generate_persona_traits()
                    )
                    personas.append(persona)
                    
                    # Prepare subcategory mappings for this persona
                    all_combinations.append({
                        'persona': persona,
                        'subcategories': combination
                    })
                
                total_assigned += exact_count

                if total_assigned >= population:
                    break

            # Bulk create personas
            Persona.objects.bulk_create(personas)

            # Create persona-subcategory mappings
            persona_subcategory_mappings = []
            for combo in all_combinations:
                persona = combo['persona']
                for subcategory in combo['subcategories']:
                    persona_subcategory_mappings.append(
                        PersonaSubCategoryMapping(
                            persona=persona, 
                            subcategory=subcategory
                        )
                    )

            # Bulk create mappings
            PersonaSubCategoryMapping.objects.bulk_create(persona_subcategory_mappings)

            return personas

        personas = generate_personas_with_weights(population, city_name, saved_categories)

        if personas:
            messages.success(request, f"Personas for {city_name} generated successfully.")
        else:
            messages.error(request, "Failed to generate personas. Please try again.")

        return redirect("impact_assessment")
    return render(request, "demographics_input.html")

def impact_assessment(request):
    """
    Assess the emotional impact of a news item on personas.
    Filters personas by city, generates emotional responses, and stores results.
    Redirects to the results page after processing.
    """
    city_name = request.GET.get('city', None)
    news_content = request.GET.get('news_item', '')

    if city_name:
        personas = Persona.objects.filter(city=city_name)
    else:
        personas = Persona.objects.all()

    cities = (
        Persona.objects.exclude(city__isnull=True)
        .exclude(city="")
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
    if request.method == "GET":
        context = {
            "personas": personas,
            "cities": cities,
            "selected_city": city_name,
            "news_item_content": news_content,
        }
        return render(request, "impact_assessment.html", context)

    if request.method == "POST":
        news_content = request.POST.get("news_item", "")
        persona_ids = request.POST.getlist("persona_ids[]")

        if not news_content or not persona_ids:
            messages.error(request, "Both news content and persona selection are required.")
            return redirect('impact_assessment')

        responses = []
        news_item, created = NewsItem.objects.get_or_create(
        title=news_content,
        content=news_content
        )

        personas = Persona.objects.filter(id__in=persona_ids)
        for persona in personas:
            if EmotionalResponse.objects.filter(news_item=news_item, persona=persona).exists():
                continue

            emotion, intensity, explanation = generate_emotional_response(persona, news_content)

            if emotion:
                response=EmotionalResponse.objects.create(
                    persona=persona,
                    news_item=news_item,
                    emotion=emotion,
                    intensity=intensity,
                    explanation=explanation,
                )
                responses.append(response)

        request.session['news_item'] = news_content
        return redirect('results', news_item_id=news_item.id)

def aggregate_emotion(request):
    """
    Initiates the aggregation of emotional responses for a specific news item and city.
    """
    city_name = request.GET.get('city', None)
    news_item_title = request.GET.get('news_item', None)

    if not city_name or not news_item_title:
        messages.error(request, "Both 'city' and 'news_item' parameters are required.")
        return redirect('impact_assessment')

    try:
        news_item, _ = NewsItem.objects.get_or_create(
            title=news_item_title,
            content=news_item_title
        )

        categories = Category.objects.prefetch_related('subcategories')
        initial_demographic_summary = {
            category.name: {subcategory.name: {"positive": 0, "negative": 0, "neutral": 0, "total": 0} 
                            for subcategory in category.subcategories.all()}
            for category in categories
        }

        aggregate_emotion_obj, _ = AggregateEmotion.objects.update_or_create(
            news_item=news_item,
            city=city_name,
            defaults={
                "summary": {"status": "Processing"},
                "demographic_summary": initial_demographic_summary
            }
        )

        aggregate_emotion_task.delay(
            city_name,
            news_item_title,
            aggregate_emotion_obj.id
        )

        request.session['city_name'] = city_name
        request.session['news_item'] = news_item_title

        messages.success(request, "Emotion aggregation started. Please wait.")
        return redirect('results_summary')

    except Exception as e:
        messages.error(request, f"Error starting aggregation: {str(e)}")
        return redirect('impact_assessment')

def fetch_summary_api(request):
    """
    API to fetch the latest summary and demographic data for charts and tables.
    """
    city = request.GET.get('city')
    news_item = request.GET.get('news_item')

    try:
        aggregate_emotion = AggregateEmotion.objects.get(
            city=city,
            news_item__title=news_item
        )

        if aggregate_emotion.summary.get('total', 0) > 0:
            return JsonResponse({
                "status": "completed",
                "summary": aggregate_emotion.summary,
                "demographic_summary": aggregate_emotion.demographic_summary,
                "city": city,
                "news_item": news_item
            })

        return JsonResponse({"status": "processing"})

    except AggregateEmotion.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Summary not found"}, status=404)

# def fetch_sample_profiles(request, category_type, category_name, city_name, news_item_title):
#     try:
#         # Fetch the NewsItem object
#         try:
#             news_item = NewsItem.objects.get(title=news_item_title)
#         except NewsItem.DoesNotExist:
#             messages.error(request, "News item not found")
#             return redirect('results_summary')
        
#         # Case-insensitive category lookup, ensuring the city matches
#         try:
#             category = Category.objects.filter(
#                 name__iexact=category_type,
#                 city__iexact=city_name
#             ).first()
#             if not category:
#                 raise Category.DoesNotExist
#         except Category.DoesNotExist:
#             messages.error(
#                 request,
#                 f"Category '{category_type}' not found for city '{city_name}'."
#             )
#             return redirect('results_summary')
        
#         # Case-insensitive subcategory lookup with multiple strategies
#         try:
#             # Strategy 1: Exact case-insensitive match
#             subcategory = SubCategory.objects.filter(
#                 category=category,
#                 name__iexact=category_name
#             ).first()

#             # Strategy 2: Partial match if exact match fails
#             if not subcategory:
#                 subcategory = SubCategory.objects.filter(
#                     category=category,
#                     name__icontains=category_name.lower()
#                 ).first()

#             # Strategy 3: Match without parenthetical city information
#             if not subcategory:
#                 clean_category_name = category_name.split('(')[0].strip().lower()
#                 subcategory = SubCategory.objects.filter(
#                     category=category,
#                     name__icontains=clean_category_name
#                 ).first()

#             if not subcategory:
#                 raise SubCategory.DoesNotExist
#         except SubCategory.DoesNotExist:
#             messages.error(
#                 request,
#                 f"Subcategory '{category_name}' not found for category '{category_type}' in city '{city_name}'."
#             )
#             return redirect('results_summary')
        
#         # Filter personas based on the city and subcategory
#         persona_mappings = PersonaSubCategoryMapping.objects.filter(
#             subcategory=subcategory
#         ).select_related('persona')
        
#         # Limit to 10 personas and filter by city
#         personas = [
#             mapping.persona
#             for mapping in persona_mappings
#             if mapping.persona.city.lower() == city_name.lower()
#         ][:10]
        
#         # Prepare personas data with emotional responses
#         personas_data = []
#         for persona in personas:
#             existing_response = EmotionalResponse.objects.filter(
#                 persona=persona,
#                 news_item=news_item
#             ).first()

#             # Generate or use existing emotional response
#             if existing_response:
#                 emotion = existing_response.emotion
#                 intensity = existing_response.intensity
#                 explanation = existing_response.explanation
#             else:
#                 # Generate emotional response using your existing function
#                 emotion, intensity, explanation = generate_emotional_response(
#                     persona,
#                     news_item.content  # Using full news content
#                 )
                
#                 # Save the newly generated emotional response
#                 EmotionalResponse.objects.create(
#                     persona=persona,
#                     news_item=news_item,
#                     emotion=emotion,
#                     intensity=intensity,
#                     explanation=explanation
#                 )
            
#             # Prepare persona data for template
#             persona_info = {
#                 'name': persona.name,
#                 'city': persona.city,
#                 'personality_traits': _parse_personality_traits(persona.personality_traits),
#                 'emotion': emotion,
#                 'intensity': round(intensity, 2) if intensity is not None else None,
#                 'explanation': explanation
#             }
#             personas_data.append(persona_info)
        
#         # If no personas found, add a helpful message
#         if not personas_data:
#             messages.warning(
#                 request,
#                 f"No personas found for {category_name} in {city_name}. "
#                 "This might be due to limited data or specific filtering."
#             )
        
#         # Render the sample profiles template
#         return render(request, 'sample_profiles.html', {
#             'category_type': category_type,
#             'category_name': category_name,
#             'personas_data': personas_data,
#             'city_name': city_name,
#             'news_item_title': news_item_title
#         })
    
#     except Exception as e:
#         # Log the error and redirect with a generic message
#         logger.error(f"Error in fetch_sample_profiles: {str(e)}")
#         messages.error(request, "An unexpected error occurred while fetching sample profiles")
#         return redirect('results_summary')

def fetch_sample_profiles(request, category_type, category_name, city_name, news_item_title):
    try:
        # Fetch the NewsItem object by title
        try:
            news_item = NewsItem.objects.get(title=news_item_title)
        except NewsItem.DoesNotExist:
            messages.error(request, "News item not found")
            return redirect('results_summary')
        
        # Fetch the Category object by its primary key or other unique identifier
        try:
            category = Category.objects.get(
                name__iexact=category_type,
                city__iexact=city_name
            )
        except Category.DoesNotExist:
            messages.error(
                request,
                f"Category '{category_type}' not found for city '{city_name}'."
            )
            return redirect('results_summary')

        # Fetch the SubCategory object by primary key
        try:
            subcategory = SubCategory.objects.filter(category=category).get(
                name__iexact=category_name
            )
        except SubCategory.DoesNotExist:
            messages.error(
                request,
                f"Subcategory '{category_name}' not found for category '{category_type}' in city '{city_name}'."
            )
            return redirect('results_summary')

        # Filter PersonaSubCategoryMapping by subcategory's primary key
        persona_mappings = PersonaSubCategoryMapping.objects.filter(
            subcategory_id=subcategory.id
        ).select_related('persona')

        # Limit to 10 personas and filter by city
        personas = [
            mapping.persona
            for mapping in persona_mappings
            if mapping.persona.city.lower() == city_name.lower()
        ][:10]

        # Prepare personas data with emotional responses
        personas_data = []
        for persona in personas:
            existing_response = EmotionalResponse.objects.filter(
                persona_id=persona.id,
                news_item_id=news_item.id
            ).first()

            # Generate or use existing emotional response
            if existing_response:
                emotion = existing_response.emotion
                intensity = existing_response.intensity
                explanation = existing_response.explanation
            else:
                # Generate emotional response using your existing function
                emotion, intensity, explanation = generate_emotional_response(
                    persona,
                    news_item.content  # Using full news content
                )

                # Save the newly generated emotional response
                EmotionalResponse.objects.create(
                    persona=persona,
                    news_item=news_item,
                    emotion=emotion,
                    intensity=intensity,
                    explanation=explanation
                )

            # Prepare persona data for template
            persona_info = {
                'name': persona.name,
                'city': persona.city,
                'personality_traits': _parse_personality_traits(persona.personality_traits),
                'emotion': emotion,
                'intensity': round(intensity, 2) if intensity is not None else None,
                'explanation': explanation
            }
            personas_data.append(persona_info)

        if not personas_data:
            messages.warning(
                request,
                f"No personas found for {category_name} in {city_name}. "
                "This might be due to limited data or specific filtering."
            )

        return render(request, 'sample_profiles.html', {
            'category_type': category_type,
            'category_name': category_name,
            'personas_data': personas_data,
            'city_name': city_name,
            'news_item_title': news_item_title
        })

    except Exception as e:
        logger.error(f"Error in fetch_sample_profiles: {str(e)}")
        messages.error(request, "An unexpected error occurred while fetching sample profiles")
        return redirect('results_summary')

def _parse_personality_traits(traits_dict):
    """
    Parse and format personality traits for display.
    """
    if not traits_dict:
        return {}
    
    formatted_traits = {}
    for key, value in traits_dict.items():
        if isinstance(value, list):
            formatted_traits[key] = ", ".join(map(str, value))
        elif isinstance(value, dict):
            formatted_traits[key] = ", ".join(f"{k}: {v}" for k, v in value.items())
        else:
            formatted_traits[key] = value
    
    return formatted_traits
