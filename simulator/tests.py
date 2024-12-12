"""
This module contains unit tests for the simulator application, focusing on persona 
generation, demographic input validation, and emotion aggregation workflows.

Classes:
    - PersonaGenerationTestCase: Tests for persona generation, input validation, 
      and session handling.
    - AggregateEmotionTestCase: Tests for emotion aggregation, task processing, 
      result summary views, and command-line argument parsing.

The tests ensure correct session handling, persona creation, demographic validation, 
emotion aggregation task execution, and integration with models and views.

Dependencies:
    - Django's test framework for client simulation and view testing.
    - unittest.mock for mocking functions and external dependencies.
    - Simulator models and utilities for handling personas and emotional responses.
"""

from unittest.mock import patch
from django.test import Client, TestCase
from django.urls import reverse
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib import messages
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from simulator.models import (
    AggregateEmotion,
    NewsItem,
    Persona,
    Category,
    SubCategory,
    PersonaSubCategoryMapping
)
from simulator.management.commands.aggregate_emotions import (
    Command as EmotionAggregationCommand,
    aggregate_emotion_task
)

class PersonaGenerationTestCase(TestCase):
    """
    Unit tests for persona generation workflows in the simulator application.
    This class tests various aspects of persona creation, including:
    - Validation of city name and population inputs.
    - Handling invalid demographic subcategory percentages.
    - End-to-end workflow for persona generation with mocked dependencies.
    - Error handling for missing required session data (e.g., city name).
    """
    def setUp(self):
        """
        Set up test data and a test client session
        """
        self.client.session['city_name'] = 'TestCity'
        self.client.session['population'] = 1000
        self.session = self.client.session
        self.session.save()

    def test_persona_input_valid_data(self):
        """
        Test successful submission of city and population
        """
        response = self.client.post(reverse('persona_input'), {
            'city_name': 'TestCity',
            'population': 1000
        })

        # Check redirect to demographics input
        self.assertRedirects(response, reverse('demographics_input'))

        # Verify session data
        self.assertEqual(self.client.session['city_name'], 'TestCity')
        self.assertEqual(self.client.session['population'], 1000)

    def test_demographics_input_invalid_percentages(self):
        """
        Test validation of subcategory percentages
        """
        session = self.client.session
        session['city_name'] = 'TestCity'
        session['population'] = 1000
        session.save()

        response = self.client.post(reverse('demographics_input'), {
            'category_1': 'Age Group',
            'subcategory_1_1': 'Young Adult',
            'percentage_1_1': 60,
            'subcategory_1_2': 'Middle Aged',
            'percentage_1_2': 30  # Does not sum to 100%
        })

        # Check for error message
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any('must sum to 100' in str(message) for message in messages_list))

    @patch('simulator.views.generate_persona_traits')
    @patch('simulator.views.Faker')
    def test_persona_generation_complete_workflow(self, mock_faker, mock_traits):
        """
        Test complete persona generation workflow
        """
        mock_faker.return_value.name.return_value = 'John Doe'

        mock_traits.return_value = {'trait1': 'value1', 'trait2': 'value2'}

        session = self.client.session
        session['city_name'] = 'TestCity'
        session['population'] = 100
        session.save()

        response = self.client.post(reverse('demographics_input'), {
            'category_1': 'Age Group',
            'subcategory_1_1': 'Young Adult',
            'percentage_1_1': 50,
            'subcategory_1_2': 'Middle Aged',
            'percentage_1_2': 50
        })

        self.assertRedirects(response, reverse('impact_assessment'))

        personas = Persona.objects.filter(city='TestCity')
        self.assertEqual(personas.count(), 100)

        self.assertTrue(PersonaSubCategoryMapping.objects.exists())

    def test_missing_city_name(self):
        """
        Test error handling when city name is missing
        """
        # Clear city name from session
        session = self.client.session
        session['city_name'] = None
        session['population'] = 1000
        session.save()

        response = self.client.post(reverse('demographics_input'), {
            'category_1': 'Age Group',
            'subcategory_1_1': 'Young Adult',
            'percentage_1_1': 100
        })

        # Check for error message about missing city name
        messages_list = list(messages.get_messages(response.wsgi_request))
        self.assertTrue(any('City name is required' in str(message) for message in messages_list))


class AggregateEmotionTestCase(TestCase):
    """
    Unit tests for the aggregation of emotional responses in the simulator application.
    This test case validates the functionality of emotion aggregation workflows, including:
    - Proper setup of test data for cities, categories, subcategories, personas, and news items.
    - Processing and aggregation of emotional responses through tasks.
    - Validation of the results summary view and its context data.
    - Parsing of command-line arguments for emotion aggregation commands.
    """
    def setUp(self):
        """
        Set up test data for emotion aggregation tests
        """
        # Create a test city
        self.city_name = 'TestCity'

        # Create categories and subcategories
        self.age_category = Category.objects.create(
            name='Age Group',
            city=self.city_name
        )
        self.young_adult_subcategory = SubCategory.objects.create(
            name='Young Adult',
            category=self.age_category,
            city=self.city_name,
            percentage=50
        )
        self.middle_aged_subcategory = SubCategory.objects.create(
            name='Middle Aged',
            category=self.age_category,
            city=self.city_name,
            percentage=50
        )

        # Create test personas
        self.personas = []
        for i in range(10):
            persona = Persona.objects.create(
                name=f'Persona {i}',
                city=self.city_name,
                personality_traits={}
            )
            self.personas.append(persona)

            # Assign subcategories
            if i < 5:
                PersonaSubCategoryMapping.objects.create(
                    persona=persona,
                    subcategory=self.young_adult_subcategory
                )
            else:
                PersonaSubCategoryMapping.objects.create(
                    persona=persona,
                    subcategory=self.middle_aged_subcategory
                )

        # Create a test news item
        self.news_item = NewsItem.objects.create(
            title='Test News Item',
            content='Test news content'
        )

        # Create a test client
        self.client = Client()

    def _setup_request_with_middleware(self, request):
        """
        Add session and message middleware to the request
        """
        middleware = SessionMiddleware(get_response=lambda x: None)
        middleware.process_request(request)
        request.session.save()

        message_middleware = MessageMiddleware(get_response=lambda x: None)
        message_middleware.process_request(request)
        setattr(request, 'session', request.session)
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        return request

    @patch('simulator.utils.impact_assesment_helper.generate_emotional_response')
    def test_aggregate_emotion_task_processing(self, mock_emotion_response):
        """
        Test the emotion aggregation task processing
        """
        # Mock emotional responses for personas
        mock_emotion_response.side_effect = [
            ('joy', 0.8, 'Positive response'),
            ('anger', 0.6, 'Negative response')
        ] * 5

        # Create AggregateEmotion object
        aggregate_emotion_obj = AggregateEmotion.objects.create(
            news_item=self.news_item,
            city=self.city_name,
            summary={'status': 'Processing'},
            demographic_summary={}
        )

        # Run aggregation task
        result = aggregate_emotion_task(
            self.city_name,
            self.news_item.title,
            aggregate_emotion_obj.id
        )

        # Refresh the object from database
        aggregate_emotion_obj.refresh_from_db()

        # Verify results
        self.assertEqual(result, "Aggregation completed successfully")
        self.assertIn('positive_percentage', aggregate_emotion_obj.summary)
        self.assertIn('negative_percentage', aggregate_emotion_obj.summary)
        self.assertTrue(aggregate_emotion_obj.summary['total'] > 0)

    def test_results_summary_view(self):
        """
        Test the results summary view
        """
        # Create an AggregateEmotion object
        aggregate_emotion_obj = AggregateEmotion.objects.create(
            news_item=self.news_item,
            city=self.city_name,
            summary={
                'total': 10,
                'positive': 4,
                'negative': 5,
                'neutral': 1,
                'positive_percentage': 40,
                'negative_percentage': 50,
                'neutral_percentage': 10
            },
            demographic_summary={
                'Age Group': {
                    'young adult': {
                        'total': 5,
                        'positive': 2,
                        'negative': 3,
                        'positive_percentage': 40,
                        'negative_percentage': 60
                    },
                    'middle aged': {
                        'total': 5,
                        'positive': 2,
                        'negative': 2,
                        'neutral': 1,
                        'positive_percentage': 40,
                        'negative_percentage': 40,
                        'neutral_percentage': 20
                    }
                }
            }
        )

        # Set up session data
        session = self.client.session
        session['city_name'] = self.city_name
        session['news_item'] = self.news_item.title
        session.save()

        # Call results summary view using client
        response = self.client.get(reverse('results_summary'))

        # Check response
        self.assertEqual(response.status_code, 200)

        # Check context data
        self.assertIn('summary', response.context)
        self.assertIn('demographic_summary', response.context)
        self.assertIn('city_name', response.context)
        self.assertIn('news_item', response.context)
        self.assertIn('charts', response.context)

    def test_argument_parsing(self):
        """
        Test that command arguments are parsed correctly.
        """
        command = EmotionAggregationCommand()
        parser = command.create_parser('manage.py', 'emotion_aggregation')

        args = parser.parse_args(['--city', 'TestCity', '--interval', '60'])

        self.assertEqual(args.city, 'TestCity')
        self.assertEqual(args.interval, 60)
