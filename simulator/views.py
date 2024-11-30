"""
This module contains views for the Persona Simulator application.

Views:
    - `persona_generation`: Handles persona generation based on demographic inputs.
    - `impact_assessment`: Displays the impact assessment interface.
"""
from django.shortcuts import render
from django.http import HttpResponse,JsonResponse
from faker import Faker
from .models import Persona,EmotionalResponse,NewsItem
from .utils.persona_helper import (
    generate_persona_traits,
    validate_demographics,
    get_occupation_by_income,
    extract_demographics
)
from .utils.impact_assesment_helper import generate_emotional_response

def persona_generation(request):
    """
    Handle the generation of personas based on user-defined demographic inputs.

    Inputs:
        - City name
        - Population size
        - Demographic distribution (age groups, religions, and income groups)

    Outputs:
        - Generates personas and saves them to the database.
    """
    if request.method == "POST":
        city_name = request.POST.get("city_name")
        population = int(request.POST.get("population"))
        demographics = extract_demographics(request)

        if not validate_demographics(demographics):
            return HttpResponse("Demographic percentages must sum up to 100.", status=400)

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

        return HttpResponse(f"Personas for {city_name} generated successfully.")

    return render(request, "persona_generation.html")


def impact_assessment(request):
    """
    Handle the assessment of the emotional impact of news items on personas.

    Generates an emotional response for each selected persona based on the news item.
    The response includes:
        - Emotion: The emotional response of the persona (e.g., joy, sadness, anger, etc.).
        - Intensity: A numeric value representing the intensity of the emotion (0 to 1).
        - Explanation: A brief explanation of why the persona reacts emotionally in that way.
    """
    city_name = request.GET.get('city', None)
    news_content = request.GET.get('news_item', '')

    if city_name:
        personas = Persona.objects.filter(city=city_name)
        print(f"Filtered City: {city_name}")
        print(f"Filtered Personas: {list(personas)}")
    else:
        personas = Persona.objects.all()
        print("No city selected. Showing all personas.")

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
        # Fetch inputs
        news_content = request.POST.get("news_item", "")
        persona_ids = request.POST.getlist("persona_ids[]")  # IDs as a list

        print("News Content:", news_content)
        print("Persona IDs:", persona_ids)

        if not news_content or not persona_ids:
            return JsonResponse({"error": "Both news content and persona selection are required."},
                                status=400
                                )
        responses = []
        news_item, created = NewsItem.objects.get_or_create(
        title=news_content,
        content=news_content
        )

        print("News Item created:", news_item)
        personas = Persona.objects.filter(id__in=persona_ids)
        for persona in personas:
            emotion, intensity, explanation = generate_emotional_response(persona, news_content)

            # Append the response
            if emotion:
                responses.append({
                    "persona_id": persona.id,
                    "persona_name": persona.name,
                    "emotion": emotion,
                    "intensity": intensity,
                    "explanation": explanation,
                })

                EmotionalResponse.objects.create(
                    persona=persona,
                    news_item=news_item,
                    emotion=emotion,
                    intensity=intensity,
                    explanation=explanation,
                )

        return JsonResponse({"responses": responses})

    personas = Persona.objects.all()
    return render(request, "impact_assessment.html", {"personas": personas})
