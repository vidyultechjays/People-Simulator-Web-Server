import threading
import time
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db import transaction
from django.conf import settings
from faker import Faker
from itertools import product

from simulator.models import Category, PersonaGenerationTask, SubCategory, Persona, PersonaSubCategoryMapping
from simulator.utils.ask_gemini import ask_gemini

class Command(BaseCommand):
    help = 'Runs a background thread for persona generation'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stop_event = threading.Event()
        self.generation_thread = None

    def handle(self, *args, **options):
        """
        Main method to start the background persona generation thread
        """
        self.stdout.write(self.style.SUCCESS('Starting Persona Generation Background Service'))

        # Start the thread that monitors the persona generation queue
        self.generation_thread = threading.Thread(
            target=self.persona_generation_worker,
            daemon=True
        )
        self.generation_thread.start()

        try:
            # Keep the main thread running
            while not self.stop_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop_event.set()
            self.stdout.write(self.style.WARNING('Stopping Persona Generation Service'))

    def persona_generation_worker(self):
        """
        Worker method to process persona generation tasks from the queue
        """
        while not self.stop_event.is_set():
            try:
                # Check for pending persona generation tasks in the database
                pending_task = PersonaGenerationTask.objects.filter(status='pending').first()

                if pending_task:
                    self.generate_personas_for_task(pending_task)

                time.sleep(1)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error in persona generation: {e}'))
                time.sleep(5)

    def generate_personas_for_task(self, task):
        """
        Generate personas for a specific task
        """
        try:
            with transaction.atomic():
                # Mark task as in progress
                task.status = 'in_progress'
                task.save()

            # Retrieve categories for this task
            categories = Category.objects.filter(city=task.city_name)

            # Generate personas using parallel processing
            personas = self.parallel_generate_personas_with_weights(
                task.population,
                task.city_name,
                categories
            )

            with transaction.atomic():
                # Mark task as completed
                task.status = 'completed'
                task.save()

            self.stdout.write(
                self.style.SUCCESS(f'Generated {len(personas)} personas for {task.city_name}')
            )

        except Exception as e:
            # Mark task as failed
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            self.stdout.write(self.style.ERROR(f'Persona generation failed: {e}'))

    def parallel_generate_personas_with_weights(self, population, city_name, saved_categories):
        """
        Generate personas with weights using parallel processing
        """
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

        # Divide workload into chunks for parallel processing
        chunk_size = max(1, population // 4)  # Adjust number of threads if needed
        chunks = [
            combination_weights[i:i + chunk_size]
            for i in range(0, len(combination_weights), chunk_size)
        ]

        personas = []
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(
                    self.process_persona_chunk, chunk, city_name, faker, population
                ) for chunk in chunks
            ]

            for future in futures:
                personas.extend(future.result())

        return personas

    def process_persona_chunk(self, chunk, city_name, faker, population):
        """
        Process a chunk of persona generation in parallel
        """
        personas = []
        total_assigned = 0

        for combo_data in chunk:
            combination = combo_data['combination']
            exact_count = round(combo_data['weight'])

            if total_assigned + exact_count > population:
                exact_count = population - total_assigned

            for _ in range(exact_count):
                # Create persona and subcategory mappings
                persona = Persona(
                    name=faker.name(),
                    city=city_name
                )
                persona.save()

                # Create subcategory mappings
                for subcategory in combination:
                    PersonaSubCategoryMapping.objects.create(
                        persona=persona,
                        subcategory=subcategory
                    )

                # Generate personality description and save
                try:
                    description = self.generate_personality_description(persona)
                    persona.personality_description = description
                    persona.save()
                except Exception:
                    persona.personality_description = "A unique individual with diverse characteristics."
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

    def generate_personality_description(self, persona):
        """
        Simplified personality description generation
        """
        try:
            persona_subcategory_mappings = PersonaSubCategoryMapping.objects.filter(persona=persona)

            if not persona_subcategory_mappings.exists():
                return "A unique individual with diverse characteristics."

            related_subcategories = [
                mapping.subcategory for mapping in persona_subcategory_mappings
            ]

            related_categories = list(set(
                subcategory.category for subcategory in related_subcategories
            ))

            demographic_details = []
            for category in related_categories:
                category_subcategories = [
                    sub for sub in related_subcategories if sub.category == category
                ]

                if category_subcategories:
                    subcategory_names = ", ".join([
                        f"{sub.name} ({sub.percentage}%)" 
                        for sub in category_subcategories
                    ])
                    demographic_details.append(
                        f"{category.name}: {subcategory_names}"
                    )

            context_summary = "; ".join(demographic_details) if demographic_details else "Diverse background"

            prompt = (
                f"Generate a nuanced, concise 3-line personality description for a person with the following profile:\n\n"
                f"Name: {persona.name}\n"
                f"City: {persona.city}\n"
                f"Demographic Context: {context_summary}\n\n"
                f"Guidelines for description:\n"
                f"- Be specific and draw insights from the demographic context\n"
                f"- Include a potential profession or role based on categories\n"
                f"- Highlight key personality traits\n"
                f"- Provide a brief insight into their potential motivations or interests\n"
                f"- Create diverse personalities\n"
                f"- Use the format: '[Name] is a [role/profession] who is [key traits]. [Additional detail].'\n"
            )

            description = ask_gemini(prompt)
            return description.strip() if description else "A unique individual with diverse characteristics."

        except Exception as e:
            print(f"Error generating persona description: {e}")
            return "A unique individual with diverse characteristics."
