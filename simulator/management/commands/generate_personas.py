import threading
import time
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from itertools import product
import pandas as pd

from simulator.models import (
    Category, LLMModelAndKey, PersonaGenerationTask, PromptModel,
    RawPersonaModel, SubCategory, Persona, PersonaSubCategoryMapping
)
from simulator.utils.ask_gemini import ask_gemini
from simulator.utils.ask_gpt import ask_gpt
from simulator.utils.ask_claude import ask_claude

class Command(BaseCommand):
    help = 'Processes both CSV and demographics-based persona generation'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_event = threading.Event()
        self.generation_thread = None

    def handle(self, *args, **options):
        """Main method to start the background persona generation thread"""
        self.stdout.write(self.style.SUCCESS('Starting Persona Generation Background Service'))
        
        self.generation_thread = threading.Thread(
            target=self.persona_generation_worker,
            daemon=True
        )
        self.generation_thread.start()

        try:
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_event.set()
            self.stdout.write(self.style.WARNING('Stopping Persona Generation Service'))

    def persona_generation_worker(self):
        """Worker method to process persona generation tasks from the queue"""
        while not self.stop_event.is_set():
            try:
                pending_task = PersonaGenerationTask.objects.filter(status='pending').first()
                if pending_task:
                    if pending_task.csv_file:
                        self.process_csv_for_task(pending_task)
                    else:
                        self.generate_personas_for_demographics(pending_task)
                time.sleep(1)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error in persona generation: {e}'))
                time.sleep(5)

    def process_csv_for_task(self, task):
        """Process CSV file for persona generation"""
        try:
            with transaction.atomic():
                task.status = 'in_progress'
                task.save()

            df = pd.read_csv(task.csv_file.path)
            
            if 'Name' not in df.columns:
                raise ValueError("CSV file must contain a 'Name' column")

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(
                        self.process_single_persona,
                        row.to_dict(),
                        task.city_name
                    ) for _, row in df.iterrows()
                ]

                personas = []
                for future in futures:
                    try:
                        persona = future.result()
                        if persona:
                            personas.append(persona)
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Error processing persona: {e}'))

            with transaction.atomic():
                task.status = 'completed'
                task.save()

            self.stdout.write(
                self.style.SUCCESS(f'Generated {len(personas)} personas for {task.city_name}')
            )

        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            self.stdout.write(self.style.ERROR(f'CSV processing failed: {e}'))

    def generate_personas_for_demographics(self, task):
        """Generate personas based on demographic inputs"""
        try:
            with transaction.atomic():
                task.status = 'in_progress'
                task.save()

            categories = Category.objects.filter(city=task.city_name)
            personas = self.parallel_generate_personas_with_weights(
                task.population,
                task.city_name,
                categories
            )

            with transaction.atomic():
                task.status = 'completed'
                task.save()
            self.stdout.write(
                self.style.SUCCESS(f'Generated {len(personas)} personas for {task.city_name}')
            )

        except Exception as e:
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            self.stdout.write(self.style.ERROR(f'Demographics-based generation failed: {e}'))

    def parallel_generate_personas_with_weights(self, population, city_name, saved_categories):
        """Generate weighted personas using parallel processing"""
        faker = Faker()

        def generate_all_subcategory_combinations(categories):
            category_subcategories = {}
            for category in categories:
                subcategories = list(category.subcategories.all())
                if subcategories:
                    category_subcategories[category.name] = subcategories

            if not category_subcategories:
                raise ValueError("No valid subcategories found for categories")

            keys = list(category_subcategories.keys())
            return list(product(*[category_subcategories[key] for key in keys]))

        subcategory_combinations = generate_all_subcategory_combinations(saved_categories)

        combination_weights = []
        for combination in subcategory_combinations:
            weight = population
            for subcategory in combination:
                weight *= (subcategory.percentage / 100)
            combination_weights.append({'combination': combination, 'weight': weight})

        combination_weights.sort(key=lambda x: x['weight'] % 1, reverse=True)

        chunk_size = max(1, population // 4)
        chunks = [
            combination_weights[i:i + chunk_size]
            for i in range(0, len(combination_weights), chunk_size)
        ]

        personas = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(
                    self.process_demographic_persona_chunk,
                    chunk, city_name, faker, population
                ) for chunk in chunks
            ]

            for future in futures:
                personas.extend(future.result())

        return personas

    def process_demographic_persona_chunk(self, chunk, city_name, faker, population):
        """Process a chunk of demographic-based persona generation"""
        personas = []
        total_assigned = 0

        for combo_data in chunk:
            combination = combo_data['combination']
            exact_count = round(combo_data['weight'])

            if total_assigned + exact_count > population:
                exact_count = population - total_assigned

            for _ in range(exact_count):
                persona = Persona(
                    name=faker.name(),
                    city=city_name
                )
                persona.save()

                for subcategory in combination:
                    PersonaSubCategoryMapping.objects.create(
                        persona=persona,
                        subcategory=subcategory
                    )

                description = self.generate_personality_description(
                    persona.name,
                    city_name,
                    self.get_demographic_context(combination)
                )
                persona.personality_description = description
                persona.save()

                personas.append(persona)
                self.stdout.write(
                    self.style.SUCCESS(f'Created persona: {persona.name}')
                )

                total_assigned += 1
                if total_assigned >= population:
                    break

            if total_assigned >= population:
                break

        return personas

    def process_single_persona(self, row_data, city_name):
        """Process a single CSV row to create a persona"""
        try:
            context_items = []
            for key, value in row_data.items():
                if key != 'Name' and pd.notna(value):
                    context_items.append(f"{key}: {value}")
            context_summary = "; ".join(context_items)

            with transaction.atomic():
                persona = Persona(
                    name=row_data['Name'],
                    city=city_name
                )
                
                description = self.generate_personality_description(
                    persona.name,
                    city_name,
                    context_summary
                )
                
                persona.personality_description = description
                persona.save()

                for column, value in row_data.items():
                    if column != 'Name' and pd.notna(value):
                        category, _ = Category.objects.get_or_create(
                            name=column,
                            city=city_name,
                            defaults={'description': f'Demographic category for {column}'}
                        )

                        subcategory, created = SubCategory.objects.get_or_create(
                            category=category,
                            name=str(value),
                            city=city_name,
                            defaults={
                                'percentage': 0.0,
                                'description': f'Subcategory {value} under {column}'
                            }
                        )

                        PersonaSubCategoryMapping.objects.create(
                            persona=persona,
                            subcategory=subcategory
                        )

                        if created:
                            self.update_subcategory_percentages(category, city_name)

                RawPersonaModel.objects.create(
                    row_data=row_data,
                    persona=persona,
                    city=city_name
                )

                return persona

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing persona {row_data.get("Name")}: {e}')
            )
            return None

    def get_demographic_context(self, subcategories):
        """Generate context summary from subcategories"""
        context_items = []
        for subcategory in subcategories:
            context_items.append(f"{subcategory.category.name}: {subcategory.name}")
        return "; ".join(context_items)

    def generate_personality_description(self, name, city, context_summary):
        """Generate personality description using LLM"""
        try:
            active_model = LLMModelAndKey.objects.filter(active=True).first()
            if not active_model:
                raise ValueError("No active LLM model found.")

            prompt_entry = PromptModel.objects.filter(task_name='personality_description').first()
            if not prompt_entry:
                raise ValueError("No prompt template found for personality description.")

            prompt = prompt_entry.prompt_template.format(
                name=name,
                city=city,
                context=context_summary,
                version=prompt_entry.version
            )

            if active_model.provider_name == 'anthropic':
                description = ask_claude(prompt, active_model.model_name)
            elif active_model.provider_name == 'openai':
                description = ask_gpt(prompt, active_model.model_name)
            elif active_model.provider_name == 'google':
                description = ask_gemini(prompt, active_model.model_name)
            else:
                raise ValueError(f"Unsupported provider: {active_model.provider_name}")

            return description.strip() if description else "A unique individual with diverse characteristics."

        except Exception as e:
            print(f"Error generating persona description: {e}")
            return "A unique individual with diverse characteristics."

    def update_subcategory_percentages(self, category, city_name):
        """Update percentages for subcategories within a category"""
        try:
            subcategories = SubCategory.objects.filter(
                category=category,
                city=city_name
            )
            
            total_personas = PersonaSubCategoryMapping.objects.filter(
                subcategory__category=category,
                subcategory__city=city_name
            ).count()
            
            if total_personas > 0:
                for subcategory in subcategories:
                    persona_count = PersonaSubCategoryMapping.objects.filter(
                        subcategory=subcategory
                    ).count()
                    
                    percentage = (persona_count / total_personas) * 100
                    subcategory.percentage = round(percentage, 2)
                    subcategory.save()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating subcategory percentages: {e}')
            )