from django.shortcuts import render

def persona_generation(request):
    return render(request, 'persona_generation.html')

def impact_assessment(request):
    return render(request, 'impact_assessment.html')
