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
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from simulator.models import (
    Persona,Category, PersonaGenerationTask, PossibleUserResponses,
    SubCategory,
    PersonaSubCategoryMapping,
    EmotionalResponse,
    NewsItem,
    AggregateEmotion,
    OptimizedResponse
)
from simulator.utils.results_visualization_helper import create_demographic_charts
from simulator.utils.impact_assesment_helper import generate_optimal_response
from simulator.auth_views import login_required
import time
from django.urls import reverse
from urllib.parse import urlencode
logger = logging.getLogger(__name__)

@login_required
def landing_page(request):
    """
    Landing page for the simulator
    """
    city_name = request.GET.get('city', None)
    cities = (
        Persona.objects.exclude(city__isnull=True)
        .exclude(city="")
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
    context = {
        'cities': cities,
        'selected_city': city_name
    }
    return render(request, 'landing.html', context)
    # return render(request, 'landing.html')

@login_required
def impact_assessment_new(request):
    """
    Enhanced landing page showing news items analyzed for a specific city
    """
    city_name = request.GET.get('city', None)
    print(f"city_name: {city_name}")
    # Get aggregate emotions for the selected city
    aggregate_emotions = None
    if city_name:
        aggregate_emotions = AggregateEmotion.objects.filter(city=city_name).select_related('news_item').order_by('-created_at')
    
    # Get list of all cities for dropdown selection
    cities = (
        Persona.objects.exclude(city__isnull=True)
        .exclude(city="")
        .exclude(city__icontains=city_name)
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
    
    persona_in_cities = Persona.objects.filter(city__contains=city_name)
    
    categories = Category.objects.filter(city=city_name)
    demographic_details = []
    for category in categories:
        subcategories_for_category = SubCategory.objects.filter(category=category)
        demographic_details.append({
            'category': category.name,
            'subcategories': [
                {
                    'name': subcategory.name,
                    'percentage': subcategory.percentage
                }
                for subcategory in subcategories_for_category
            ]
        })
    
    print(f"demographic_details: {demographic_details}")
    
    
    
    
    return render(request, 'impact_assessment_new.html', {
        'selected_city': city_name,
        'cities': cities,
        'aggregate_emotions': aggregate_emotions,
        'population_count': persona_in_cities.count(),
        'demographic_details': demographic_details,
        'categories_count': categories.count(),
    })

@login_required
def results_summary(request):
    """
    Display detailed emotional summary with demographic breakdowns and user responses
    """
    city_name = request.GET.get('city', request.session.get('city_name'))
    news_item_title = request.GET.get('news_item', request.session.get('news_item'))
    print(f"city_name: {city_name}")
    try:
        cities = (
        Persona.objects.exclude(city__isnull=True)
        .exclude(city="")
        .exclude(city__icontains=city_name)
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
        
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
    
    categories = Category.objects.filter(city=city_name)

    demographic_details = []
    for category in categories:
        subcategories_for_category = SubCategory.objects.filter(category=category)
        demographic_details.append({
            'category': category.name,
            'subcategories': [
                {
                    'name': subcategory.name,
                    'percentage': subcategory.percentage
                }
                for subcategory in subcategories_for_category
            ]
        })
    
    persona_in_cities = Persona.objects.filter(city__contains=city_name)
    
    return render(request, "results_summary.html", {
        "summary": aggregate_emotion.summary if aggregate_emotion else {},
        "demographic_summary": demographic_summary,
        "demographic_details": demographic_details,
        "news_item": news_item_title,
        "city_name": city_name,
        "charts": charts,
        "possible_responses": possible_responses,
        "cities": cities,
        "population_count": persona_in_cities.count(),
        "categories_count": categories.count(),
    })

# views.py

@login_required
def persona_input(request):
    """
    Handles both CSV file upload and population-based persona generation options
    """
    if request.method == "POST":
        logger.info("POST request received")
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
                base_url = reverse("impact_assessment_new")
                query_string = urlencode({"city": city_name})
                url = f"{base_url}?{query_string}"
                return redirect(url)
            
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

@login_required
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
        
        time.sleep(2)

        messages.success(request, f"Persona generation task for {city_name} created successfully.")
        base_url = reverse("impact_assessment_new")
        query_string = urlencode({"city": city_name})
        url = f"{base_url}?{query_string}"
        return redirect(url)
    return render(request, "demographics_input.html")

@login_required
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


@login_required
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
        print(f"city_name: {city_name} :: news_item_title: {news_item_title} :: possible_responses: {possible_responses}")

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
            persona_in_cities = Persona.objects.filter(city__contains=city_name)

            # Create or update the AggregateEmotion object with the initial values
            aggregate_emotion_obj, _ = AggregateEmotion.objects.update_or_create(
                news_item=news_item,
                city=city_name,
                defaults={
                    "summary": initial_summary,
                    "demographic_summary": initial_demographic_summary,
                    "total_responses": persona_in_cities.count(),
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


@login_required
def fetch_summary_api(request):
    """
    Fetches the emotional summary and demographic breakdown for a specific city and news item.
    Returns JSON response with the status, summary, and demographic details.
    """
    logger.info("Fetch summary API request received")
    city = request.GET.get('city')
    news_item = request.GET.get('news_item')

    try:
        aggregate_emotion = AggregateEmotion.objects.get(
            city=city,
            news_item__title__icontains=news_item.strip()
        )
        
        if aggregate_emotion.summary.get('total_responses', 0) > 0:
            return JsonResponse({
                "status": "completed",
                "summary": aggregate_emotion.summary,
                "demographic_summary": aggregate_emotion.demographic_summary,
                "city": city,
                "news_item": news_item
            })

        total_responses = aggregate_emotion.total_responses
        processed_responses = aggregate_emotion.processed_responses
        context = {
            "status": "processing",
            "total_responses": total_responses,
            "processed_responses": processed_responses
        }
        return JsonResponse(context)

    # except AggregateEmotion.DoesNotExist:
    #     return JsonResponse({"status": "error", "message": "Summary not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in fetch_summary_api: {str(e)}")
        return JsonResponse({"status": "error", "message": "An unexpected error occurred"}, status=500)

@login_required
def fetch_sample_profiles(request, category_type, category_name, city_name, news_item_title):
    """
    Fetch sample profiles for a given category, subcategory, and city 
    based on a specific news item, generating user responses as needed.
    """
    try:
        try:
            cities = (
                Persona.objects.exclude(city__isnull=True)
                .exclude(city="")
                .exclude(city__icontains=city_name)
                .values_list("city", flat=True)
                .distinct()
                .order_by("city")
            )
        except Persona.DoesNotExist:
            messages.error(request, "City not found")
            return redirect('results_summary')
        
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
        categories = Category.objects.filter(city=city_name)
        
        demographic_details = []
        for category in categories:
            subcategories_for_category = SubCategory.objects.filter(category=category)
            demographic_details.append({
                'category': category.name,
                'subcategories': [
                    {
                        'name': subcategory.name,
                        'percentage': subcategory.percentage
                    }
                    for subcategory in subcategories_for_category
                ]
            })

        persona_in_cities = Persona.objects.filter(city__contains=city_name)

        return render(request, 'sample_profiles.html', {
            'category_type': category_type,
            'category_name': category_name,
            'personas_data': personas_data,
            'city_name': city_name,
            'news_item_title': news_item_title,
            'cities': cities,
            'demographic_details': demographic_details,
            "population_count": persona_in_cities.count(),
            "categories_count": categories.count(),
        })
        
        for city in cities:
            print(f"city: {city}")

    except Exception as e:
        logger.error("Error in fetch_sample_profiles: %s", str(e))
        messages.error(request, "An unexpected error occurred while fetching sample profiles")
        return redirect('results_summary')

@login_required
def list_aggregate_emotions(request):
    """
    View to list all AggregateEmotion objects with links to their respective result summaries.
    """
    aggregate_emotions = AggregateEmotion.objects.select_related('news_item').order_by('-created_at')

    return render(request, 'list_aggregate_emotions.html', {
        'aggregate_emotions': aggregate_emotions
    })


@login_required
def optimize_content(request):
    """
    Generates and returns optimized content for a news item
    """
    logger.info("optimize_content request received")
    if request.method == "POST":
        city_name = request.POST.get('city')
        news_item_title = request.POST.get('news_item')
        demographic_focus = request.POST.getlist('demographic_focus')
        print(f"demographic_focus: {demographic_focus}")
        
        if not city_name or not news_item_title:
            return JsonResponse({'error': 'City name and news item title are required'}, status=400)
            
        # Get or generate optimized content
        print('before')
        existing_optimization = OptimizedResponse.objects.filter(
            city=city_name,
            news_item__title=news_item_title,
            demographic_focus=demographic_focus
        ).first()
        print('after')
        
        if existing_optimization:
            try:
                # Try to parse the optimized_content as JSON if it's a string
                optimized_content = existing_optimization.optimized_content
                if isinstance(optimized_content, str):
                    try:
                        optimized_content = json.loads(optimized_content)
                    except json.JSONDecodeError:
                        # If it's not valid JSON, use it as is
                        pass
                
                response_data = {
                    'optimized_content': optimized_content,
                    'optimization_metrics': existing_optimization.optimization_metrics,
                    'success': True,
                    'cached': True
                }
            except Exception as e:
                logger.error(f"Error processing existing optimization: {str(e)}")
                return JsonResponse({'error': f'Error processing optimization: {str(e)}'}, status=500)
        else:
            # Get the news item content
            print('inside else statement')
            news_item = NewsItem.objects.get(title__icontains=news_item_title)
            
            
            # Get demographic breakdown for the city
            categories = Category.objects.filter(city=city_name)
            subcategories = SubCategory.objects.filter(city=city_name)
            
            
            
            
            # Generate new optimization
            print('before response data')
            response_data = generate_optimal_response(city_name, news_item , demographic_focus)
        
        return JsonResponse(response_data)
    
    return JsonResponse({'error': 'Only POST requests allowed'}, status=405)

@login_required
def optimize_content_two(request):
    """
    View to handle the optimization strategy form submission and processing
    """
    
    city_name = request.GET.get('city')
    news_item_title = request.GET.get('news_item')
    
    logger.info(f"city_name: {city_name} :: news_item_title: {news_item_title}")
    print(f"city_name: {city_name} :: news_item_title: {news_item_title}")
    
    if request.method == "POST":
            
        news_item = request.POST.get('news_item')
        city_name = request.POST.get('city')
        demographic_focus = request.POST.getlist('demographic_focus')

        if not city_name or not news_item:
            return JsonResponse({'error': 'City name and news item title are required'}, status=400)
        
        print(f"demographic_focus: {demographic_focus}")
        
    cities = (
        Persona.objects.exclude(city__isnull=True)
        .exclude(city="")
        .exclude(city__icontains=city_name)
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
        # Get demographic breakdown for the city
    categories = Category.objects.filter(city=city_name)
    subcategories = SubCategory.objects.filter(city=city_name)
    
    categories = Category.objects.filter(city=city_name)
    demographic_details = []
    for category in categories:
        subcategories_for_category = SubCategory.objects.filter(category=category)
        demographic_details.append({
            'category': category.name,
            'subcategories': [
                {
                    'name': subcategory.name,
                    'percentage': subcategory.percentage
                }
                for subcategory in subcategories_for_category
            ]
        })
    
    persona_in_cities = Persona.objects.filter(city__contains=city_name)
    
    return render(request, 'optimization_strategy.html', {
        'messages': None,
        'city_name': city_name,
        'news_item': news_item_title,
        'categories': categories,
        'subcategories': subcategories,
        'optimization_strategy': None,
        'cities': cities,
        'demographic_details': demographic_details,
        "population_count": persona_in_cities.count(),
        "categories_count": categories.count(),
    })
    
    
        
        
