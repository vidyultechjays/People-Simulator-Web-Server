"""
This module manages persona generation, emotional impact assessment, and response aggregation 
to analyze the influence of news items on diverse demographics.

**Features**:
1. **Persona Input and Generation**:
   - Captures city and population data to initialize persona generation.
   - Collects demographic categories and subcategories with percentages.
   - Creates persona generation tasks for specified cities and populations.

2. **Emotional Impact Assessment**:
   - Analyzes how news items affect personas' emotions (e.g., positive, negative, neutral).
   - Displays personas filtered by city and emotional responses to news items.

3. **Response Aggregation**:
   - Aggregates emotional responses across personas grouped by city and demographics.
   - Summarizes trends by categories (e.g., age, income, religion).

4. **Visualization and Results Summaries**:
   - Generates visualizations (e.g., pie charts, bar charts) of emotional responses.
   - Provides detailed summaries of emotional impact by demographics and city.

5. **Dynamic Data Access**:
   - Offers APIs to fetch real-time summaries, aggregated emotions, and sample personas.

**Key Views**:
- `persona_input`: Initializes persona generation with city and population inputs.
- `demographics_input`: Collects and validates demographic data for persona creation.
- `results_summary`: Displays emotional summaries with demographic breakdowns.
- `fetch_sample_profiles`: Retrieves sample personas and their responses by category.
- `aggregate_emotion`: Aggregates emotional responses for news items and cities.
"""

import logging
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import messages
from simulator.models import (
    Persona,Category, PersonaGenerationTask, PossibleUserResponses,
    SubCategory,
    PersonaSubCategoryMapping,
    EmotionalResponse,
    NewsItem,
    AggregateEmotion
)
from simulator.utils.results_visualization_helper import create_demographic_charts

logger = logging.getLogger(__name__)

def results_summary(request):
    """
    Display detailed emotional summary with demographic breakdowns and user responses
    """
    city_name = request.GET.get('city', request.session.get('city_name'))
    news_item_title = request.GET.get('news_item', request.session.get('news_item'))
    try:
        aggregate_emotion = AggregateEmotion.objects.get(
            city=city_name,
            news_item__title=news_item_title
        )

        possible_responses = PossibleUserResponses.objects.filter(
            news_item__title=news_item_title
        )

        charts = {}
        demographic_summary = aggregate_emotion.demographic_summary

        # Create charts for demographic summaries
        for category_type, categories in demographic_summary.items():
            charts.update(create_demographic_charts(category_type, categories))

    except AggregateEmotion.DoesNotExist:
        aggregate_emotion = None
        charts = {}
        possible_responses = []
        demographic_summary = {}

    return render(request, "results_summary.html", {
        "summary": aggregate_emotion.summary if aggregate_emotion else {},
        "demographic_summary": demographic_summary,
        "news_item": news_item_title,
        "city_name": city_name,
        "charts": charts,
        "possible_responses": possible_responses,
    })

# views.py

def persona_input(request):
    """
    Handles both CSV file upload and population-based persona generation options
    """
    if request.method == "POST":
        generation_type = request.POST.get("generation_type")
        city_name = request.POST.get("city_name")

        if not city_name:
            messages.error(request, "City name is required.")
            return redirect("persona_input")

        if generation_type == "csv":
            csv_file = request.FILES.get("csv_file")
            
            if not csv_file:
                messages.error(request, "Please upload a CSV file.")
                return redirect("persona_input")

            if not csv_file.name.endswith('.csv'):
                messages.error(request, "File must be a CSV.")
                return redirect("persona_input")

            try:
                task = PersonaGenerationTask.objects.create(
                    city_name=city_name,
                    status='pending',
                    csv_file=csv_file
                )
                
                messages.success(
                    request,
                    f"CSV file uploaded successfully. Processing will begin shortly for {city_name}."
                )
                return redirect("impact_assessment")
            
            except Exception as e:
                messages.error(request, f"Error processing upload: {str(e)}")
                return redirect("persona_input")

        elif generation_type == "demographics":
            try:
                population = int(request.POST.get("population"))
                if population <= 0:
                    messages.error(request, "Population must be a positive number.")
                    return redirect("persona_input")
                    
                request.session["city_name"] = city_name
                request.session["population"] = population
                return redirect("demographics_input")
            
            except (ValueError, TypeError):
                messages.error(request, "Please enter a valid population number.")
                return redirect("persona_input")
        
        else:
            messages.error(request, "Please select a generation type.")
            return redirect("persona_input")

    return render(request, "persona_input.html")

def demographics_input(request):
    """
    Handles the input for categories and subcategories, creates a persona generation task
    """
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
                    f"Subcategory percentages for '{category_data['name']}' must sum to 100."
                    f"Current total: {total_percentage}."
                )
                return redirect("demographics_input")

        saved_categories = []
        city_name = request.session.get("city_name")

        if not city_name:
            messages.error(request, "City name is required. Please start from the beginning.")
            return redirect("persona_input")

        for category_data in categories.values():
            category = Category.objects.create(
                name=category_data["name"],
                city=city_name
            )
            saved_categories.append(category)
            for subcategory_data in category_data["subcategories"]:
                SubCategory.objects.create(
                    name=subcategory_data["name"],
                    percentage=subcategory_data["percentage"],
                    category=category,
                    city=city_name
                )

        population = request.session.get("population")
        if not population:
            messages.error(request, "Population is required. Please start from the beginning.")
            return redirect("persona_input")

        # Create a persona generation task
        PersonaGenerationTask.objects.create(
            city_name=city_name,
            population=population,
            status='pending'
        )

        messages.success(request, f"Persona generation task for {city_name} created successfully.")
        return redirect("impact_assessment")
    return render(request, "demographics_input.html")

def impact_assessment(request):
    """
    Displays personas by city and processes emotional responses
    """
    city_name = request.GET.get('city', None)
    news_content = request.GET.get('news_item', '')

    cities = (
        Persona.objects.exclude(city__isnull=True)
        .exclude(city="")
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )

    if request.method == "GET":
        context = {
            "cities": cities,
            "selected_city": city_name,
            "news_item_content": news_content,
        }
        return render(request, "impact_assessment.html", context)


def aggregate_emotion(request):
    """
    Initiates the aggregation of emotional responses for a specific news item and city,
    while saving the possible user responses.
    """
    if request.method == "POST":
        city_name = request.POST.get('city')
        news_item_title = request.POST.get('news_item')
        possible_responses = [
            value for key, value in request.POST.items() if key.startswith("possible_response_")
        ]

        if not city_name or not news_item_title:
            messages.error(request, "Both 'city' and 'news_item' parameters are required.")
            return redirect('impact_assessment')

        try:
            news_item, _ = NewsItem.objects.get_or_create(
                title=news_item_title,
                defaults={"content": news_item_title}
            )

            # Loop through the possible responses and check for duplicates before saving
            for response_text in possible_responses:
                if PossibleUserResponses.objects.filter(news_item=news_item, response_text=response_text).exists():
                    messages.warning(request, f"Response '{response_text}' already exists for this news item.")
                else:
                    PossibleUserResponses.objects.create(news_item=news_item, response_text=response_text)

            categories = Category.objects.prefetch_related("subcategories")

            # Initialize initial summary in the desired format
            initial_summary = {
                "status": "Processing",
                "total_responses": 0,
                "response_summary": {}
            }

            # Add possible responses to the response_summary
            for response_text in possible_responses:
                initial_summary["response_summary"][response_text] = {
                    "count": 0,
                    "percentage": 0.0,
                    "response_text": response_text,
                }

            # Initialize the demographic summary in the desired format
            initial_demographic_summary = {
                category.name: {
                    subcategory.name.lower(): {
                        "count": 0,
                        "percentage": 0.0,
                        "response_text": "Default response text",
                    }
                    for subcategory in category.subcategories.filter(city=city_name)
                }
                for category in categories
            }

            # Create or update the AggregateEmotion object with the initial values
            aggregate_emotion_obj, _ = AggregateEmotion.objects.update_or_create(
                news_item=news_item,
                city=city_name,
                defaults={
                    "summary": initial_summary,
                    "demographic_summary": initial_demographic_summary,
                },
            )

            request.session["city_name"] = city_name
            request.session["news_item"] = news_item_title

            messages.success(request, "Emotion aggregation started. Please wait.")
            return redirect("results_summary")

        except Exception as e:
            messages.error(request, f"Error starting aggregation: {str(e)}")
            return redirect("impact_assessment")

    messages.error(request, "Invalid request method.")
    return redirect("impact_assessment")


def fetch_summary_api(request):
    """
    Fetches the emotional summary and demographic breakdown for a specific city and news item.
    Returns JSON response with the status, summary, and demographic details.
    """
    city = request.GET.get('city')
    news_item = request.GET.get('news_item')

    try:
        aggregate_emotion = AggregateEmotion.objects.get(
            city=city,
            news_item__title=news_item
        )

        if aggregate_emotion.summary.get('total_responses', 0) > 0:
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

def fetch_sample_profiles(request, category_type, category_name, city_name, news_item_title):
    """
    Fetch sample profiles for a given category, subcategory, and city 
    based on a specific news item, generating user responses as needed.
    """
    try:
        try:
            news_item = NewsItem.objects.get(title=news_item_title)
        except NewsItem.DoesNotExist:
            messages.error(request, "News item not found")
            return redirect('results_summary')

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

        try:
            subcategory = SubCategory.objects.get(
                category=category,
                name__iexact=category_name,
                city__iexact=city_name
            )
        except SubCategory.DoesNotExist:
            messages.error(
                request,
                f"Subcategory '{category_name}' not found for category '{category_type}' in city '{city_name}'."
            )
            return redirect('results_summary')

        persona_mappings = PersonaSubCategoryMapping.objects.filter(
            subcategory_id=subcategory.id
        ).select_related('persona')

        personas = [
            mapping.persona
            for mapping in persona_mappings
            if mapping.persona.city.lower() == city_name.lower()
        ][:10]

        personas_data = []
        for persona in personas:
            # Fetch the existing user response, if any
            existing_response = EmotionalResponse.objects.filter(
                persona_id=persona.id,
                news_item_id=news_item.id
            ).first()

            if existing_response:
                user_response = existing_response.user_response
                intensity = existing_response.intensity
                explanation = existing_response.explanation
            else:
                # No response for this persona; generate and save a placeholder or skip
                user_response = "No response recorded."
                intensity = None
                explanation = "No explanation available."

            # Collect persona data
            persona_info = {
                'name': persona.name,
                'city': persona.city,
                'personality_description': persona.personality_description,
                'user_response': user_response,
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
        logger.error("Error in fetch_sample_profiles: %s", str(e))
        messages.error(request, "An unexpected error occurred while fetching sample profiles")
        return redirect('results_summary')

def list_aggregate_emotions(request):
    """
    View to list all AggregateEmotion objects with links to their respective result summaries.
    """
    aggregate_emotions = AggregateEmotion.objects.select_related('news_item').order_by('-created_at')

    return render(request, 'list_aggregate_emotions.html', {
        'aggregate_emotions': aggregate_emotions
    })
