from django.shortcuts import render
from django.http import HttpResponse
from faker import Faker
from simulator.models import Persona
from .utils.persona_helper import generate_persona_traits, validate_demographics

def persona_generation(request):
    if request.method == "POST":
        city_name = request.POST.get("city_name")
        population = int(request.POST.get("population"))
        demographics = {
            "age_groups": {
                "18-25": int(request.POST.get("demographics[age_groups][18-25]")),
                "26-40": int(request.POST.get("demographics[age_groups][26-40]")),
                "41-60": int(request.POST.get("demographics[age_groups][41-60]")),
                "60+": int(request.POST.get("demographics[age_groups][60+]")),
            },
            "religions": {
                "hindu": int(request.POST.get("demographics[religions][hindu]")),
                "muslim": int(request.POST.get("demographics[religions][muslim]")),
                "christian": int(request.POST.get("demographics[religions][christian]")),
                "others": int(request.POST.get("demographics[religions][others]"))
            },
            "income_groups": {
                "low": int(request.POST.get("demographics[income_groups][low]")),
                "medium": int(request.POST.get("demographics[income_groups][medium]")),
                "high": int(request.POST.get("demographics[income_groups][high]")),
            },
        }

        if not validate_demographics(demographics):
            return HttpResponse("Demographic percentages must sum up to 100.", status=400)

        def generate_personas_with_weights(population):
            faker = Faker()
            personas = []
            combinations = []
            for age_group, age_pct in demographics["age_groups"].items():
                for religion, religion_pct in demographics["religions"].items():
                    for income_group, income_pct in demographics["income_groups"].items():
                        expected_count = population * (age_pct / 100) * (religion_pct / 100) * (income_pct / 100)
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
                            occupation=faker.job(),
                            personality_traits=generate_persona_traits(),
                            city=city_name
                        )
                    )
                total_assigned += exact_count

                if total_assigned >= population:
                    break

            remaining = population - len(personas)
            if remaining > 0:
                fractional_combinations = sorted(combinations, key=lambda x: x['expected_count'] % 1, reverse=True)
                for combo in fractional_combinations:
                    if remaining <= 0:
                        break
                    personas.append(
                        Persona(
                            name=faker.name(),
                            age_group=combo['age_group'],
                            income_level=combo['income_group'],
                            religion=combo['religion'],
                            occupation=faker.job(),
                            personality_traits=generate_persona_traits(),
                            city=city_name
                        )
                    )
                    remaining -= 1

            return personas 

        personas = generate_personas_with_weights(population)

        Persona.objects.bulk_create(personas)

        return HttpResponse(f"Personas for {city_name} generated successfully.")

    return render(request, "persona_generation.html")

def impact_assessment(request):
    return render(request, "impact_assessment.html")
