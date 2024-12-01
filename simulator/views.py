"""
This module handles persona generation, emotional impact assessment, and response aggregation.

Features:
1. **Persona Generation**: Generates personas based on demographic inputs like age, 
    religion,personality traits and income distribution.
2. **Impact Assessment**: Analyzes the emotional impact of a news item on selected personas, 
    generating responses with emotion, intensity, and explanation.
3. **Response Aggregation**: Categorizes and summarizes emotional responses (positive,
     negative, neutral) across personas, grouped by city and news item.
4. **Result Presentation**: Displays individual emotional responses and aggregated summaries
     in a user-friendly format.

Primarily supports city-specific analysis of emotional responses to user-provided news items.
"""
import logging
from django.shortcuts import render,redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count,Avg
from faker import Faker
from simulator.models import Persona,EmotionalResponse,NewsItem,AggregateEmotion
from simulator.utils.persona_helper import (
    generate_persona_traits,
    validate_demographics,
    get_occupation_by_income,
    extract_demographics
)
from simulator.utils.impact_assesment_helper import generate_emotional_response
from simulator.utils.results_visualization_helper import (
    create_emotion_intensity_bar_chart,
    create_pie_chart
)
from simulator.tasks import aggregate_emotion_task

logger = logging.getLogger(__name__)

def results(request, news_item_id):
    """
    Display emotional responses with multiple visualizations:
    - Pie chart for emotion breakdown
    - Bar chart for emotion intensity
    """
    news_item = NewsItem.objects.get(id=news_item_id)

    emotion_breakdown = EmotionalResponse.objects.filter(
        news_item_id=news_item_id
    ).values('emotion').annotate(count=Count('emotion'))

    emotion_intensity = EmotionalResponse.objects.filter(
        news_item_id=news_item_id
    ).values('emotion').annotate(
        avg_intensity=Avg('intensity'),
        count=Count('emotion')
    )

    emotion_chart = create_pie_chart(emotion_breakdown, f'Pie chart for news - "{news_item.title}"')
    emotion_intensity_bar_chart = create_emotion_intensity_bar_chart(
        emotion_intensity,
        f'Bar chart for news - "{news_item.title}"'
    )
    assessment_results = EmotionalResponse.objects.filter(
        news_item_id=news_item_id
    ).select_related('persona', 'news_item')

    return render(request, "results.html", {
        "results": assessment_results,
        "news_item": news_item.title,
        "emotion_chart": emotion_chart,
        "emotion_intensity_bar_chart": emotion_intensity_bar_chart
    })

def results_summary(request):
    """
    Show aggregated emotional responses with visualizations.
    Displays a summary table and Plotly charts.
    """
    news_item_title = request.session.get('news_item')
    city_name = request.session.get('city_name')

    try:
        aggregate_emotion = AggregateEmotion.objects.get(
            city=city_name,
            news_item__title=news_item_title
        )
        summary = aggregate_emotion.summary
    except AggregateEmotion.DoesNotExist:
        summary = None

    emotion_pie_chart = None

    if summary and summary != "Processing...":
        emotion_data = [
            {'emotion': 'Positive', 'count': summary['positive']},
            {'emotion': 'Negative', 'count': summary['negative']},
            {'emotion': 'Neutral', 'count': summary['neutral']}
        ]

        emotion_pie_chart = create_pie_chart(emotion_data, f'Emotion Distribution in {city_name}')

    return render(request, "results_summary.html", {
        "summary": summary,
        "news_item": news_item_title,
        "city_name": city_name,
        "emotion_pie_chart": emotion_pie_chart,
    })

def persona_generation(request):
    """
    Generate personas based on demographic inputs.
    Accepts city, population, and demographic data to create weighted personas.
    Saves generated personas to the database for future analysis.
    """
    if request.method == "POST":
        city_name = request.POST.get("city_name")
        population = int(request.POST.get("population"))
        demographics = extract_demographics(request)

        if not validate_demographics(demographics):
            messages.error(request, "Demographic percentages must sum up to 100.")
            return redirect("persona_generation")

        def generate_personas_with_weights(population):
            faker = Faker()
            personas = []
            combinations = []
            for age_group, age_pct in demographics["age_groups"].items():
                for religion, religion_pct in demographics["religions"].items():
                    for income_group, income_pct in demographics["income_groups"].items():
                        expected_count = (
                        population
                        * (age_pct / 100)
                        * (religion_pct / 100)
                        * (income_pct / 100)
                        )
                        combinations.append({
                            'age_group': age_group,
                            'religion': religion,
                            'income_group': income_group,
                            'expected_count': expected_count
                        })

            combinations.sort(key=lambda x: x['expected_count'] % 1, reverse=True)

            total_assigned = 0
            for combo in combinations:
                exact_count = round(combo['expected_count'])

                if total_assigned + exact_count > population:
                    exact_count = population - total_assigned

                for _ in range(exact_count):

                    personas.append(
                        Persona(
                            name=faker.name(),
                            age_group=combo['age_group'],
                            income_level=combo['income_group'],
                            religion=combo['religion'],
                            occupation=get_occupation_by_income(combo['income_group']),
                            personality_traits=generate_persona_traits(),
                            city=city_name
                        )
                    )
                total_assigned += exact_count

                if total_assigned >= population:
                    break

            remaining = population - len(personas)
            if remaining > 0:
                fractional_combinations = sorted(
                combinations,
                key=lambda x: x['expected_count'] % 1,
                reverse=True
                )
                for combo in fractional_combinations:
                    if remaining <= 0:
                        break

                    personas.append(
                        Persona(
                            name=faker.name(),
                            age_group=combo['age_group'],
                            income_level=combo['income_group'],
                            religion=combo['religion'],
                            occupation=get_occupation_by_income(combo['income_group']),
                            personality_traits=generate_persona_traits(),
                            city=city_name
                        )
                    )
                    remaining -= 1

            return personas

        personas = generate_personas_with_weights(population)

        if personas:
            Persona.objects.bulk_create(personas)

        messages.success(request, f"Personas for {city_name} generated successfully.")

        return redirect("impact_assessment")

    return render(request, "persona_generation.html")


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
    It triggers a background Celery task to process the emotional analysis and stores 
    the current status in the session.
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
        aggregate_emotion_obj, created = AggregateEmotion.objects.update_or_create(
            news_item=news_item,
            city=city_name,
            defaults={"summary": "Processing..."}
        )

        logger.info("Triggering Celery task for city: %s, news_item: %s",city_name, news_item_title)

        request.session['city_name'] = city_name
        request.session['news_item'] = news_item_title
        request.session['summary'] = aggregate_emotion_obj.summary

        aggregate_emotion_task.delay(city_name, news_item_title)
    except Exception as e:
        messages.error(request, f"Error initializing the aggregation process: {str(e)}")
        return redirect('impact_assessment')

    return redirect('results_summary')


def fetch_summary_api(request):
    """
    Fetches the emotional summary for a given city and news item.

    This function retrieves the 'city' and 'news_item' parameters from the request and 
    checks the status of the emotional aggregation for the corresponding `AggregateEmotion` object.
    If the summary is completed,it returns the summary data in a JSON response. If the summary is 
    still being processed, it returns a 'processing' status.
    """
    city = request.GET.get('city')
    news_item = request.GET.get('news_item')

    if not city or not news_item:
        return JsonResponse(
            {
                "status": "error",
                "message": "City and news item are required."
            },
            status=400
        )
    try:
        aggregate_emotion_record = AggregateEmotion.objects.filter(
            city=city,
            news_item__title=news_item
        ).first()
        if aggregate_emotion_record:
            summary = aggregate_emotion_record.summary
            if summary and summary != "Processing...":
                return JsonResponse({
                    "status": "completed",
                    "summary": summary,  
                    "city": city  
                })
        return JsonResponse({"status": "processing"})

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)
