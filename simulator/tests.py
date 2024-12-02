"""
This module contains unit tests for the persona generation and impact assessment functionalities
of the simulator application. It ensures the following:
- Proper validation and creation of personas based on demographic data.
- Handling of special cases and error scenarios in persona generation.
- Verification of the impact assessment process, including emotional response creation,
  result viewing, and duplicate prevention.
- Testing of aggregate emotion summaries, including API responses for different processing states.
"""
from unittest.mock import patch
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.messages import get_messages
from simulator.models import AggregateEmotion, EmotionalResponse, NewsItem, Persona

class PersonaGenerationTestCase(TestCase):
    """
    This class validates:
    - Proper persona creation with valid input data.
    - Error handling for invalid demographic percentages.
    - Special cases like zero population input.
    """
    def setUp(self):
        self.client = Client()
        self.url = reverse('persona_generation')

    def test_persona_generation_valid_data(self):
        """Test persona generation with valid demographic data."""
        data = {
            'city_name': 'Test City',
            'population': 100,
            'demographics[age_groups][18-25]': 25,
            'demographics[age_groups][26-40]': 25,
            'demographics[age_groups][41-60]': 25,
            'demographics[age_groups][60+]': 25,
            'demographics[religions][hindu]': 50,
            'demographics[religions][muslim]': 30,
            'demographics[religions][christian]': 10,
            'demographics[religions][others]': 10,
            'demographics[income_groups][low]': 40,
            'demographics[income_groups][medium]': 40,
            'demographics[income_groups][high]': 20,
        }

        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse('impact_assessment'))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('generated successfully' in str(message) for message in messages))

        self.assertEqual(Persona.objects.filter(city='Test City').count(), 100)

    def test_persona_generation_invalid_demographics(self):
        """Test persona generation with invalid demographic percentages."""
        data = {
            'city_name': 'Test City',
            'population': 100,
            'demographics[age_groups][18-25]': 25,
            'demographics[age_groups][26-40]': 25,
            'demographics[age_groups][41-60]': 25,
            'demographics[age_groups][60+]': 30,
            'demographics[religions][hindu]': 50,
            'demographics[religions][muslim]': 30,
            'demographics[religions][christian]': 10,
            'demographics[religions][others]': 10,
            'demographics[income_groups][low]': 40,
            'demographics[income_groups][medium]': 40,
            'demographics[income_groups][high]': 20,
        }

        response = self.client.post(self.url, data)

        self.assertRedirects(response, self.url)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any(
                'Demographic percentages must sum up to 100.' in str(message)
                for message in messages
            )
        )
        self.assertEqual(Persona.objects.filter(city='Test City').count(), 0)

    def test_persona_generation_population_zero(self):
        """Test persona generation with population set to zero."""
        data = {
            'city_name': 'Test City',
            'population': 0,  
            'demographics[age_groups][18-25]': 25,
            'demographics[age_groups][26-40]': 25,
            'demographics[age_groups][41-60]': 25,
            'demographics[age_groups][60+]': 25,
            'demographics[religions][hindu]': 50,
            'demographics[religions][muslim]': 30,
            'demographics[religions][christian]': 10,
            'demographics[religions][others]': 10,
            'demographics[income_groups][low]': 40,
            'demographics[income_groups][medium]': 40,
            'demographics[income_groups][high]': 20,
        }

        response = self.client.post(self.url, data)

        self.assertRedirects(response, reverse('impact_assessment'))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('generated successfully' in str(message) for message in messages))

        self.assertEqual(Persona.objects.filter(city='Test City').count(), 0)


class ImpactAssessmentTests(TestCase):
    """
    This class includes tests for:
    - Retrieving the impact assessment page.
    - Submitting impact assessment data with success and error cases.
    - Ensuring no duplicate emotional responses are created.
    - Displaying results and generated charts.
    """
    def setUp(self):
        self.client = Client()
        self.city_name = "TestCity"
        self.news_content = "This is a test news item."

        self.persona1 = Persona.objects.create(
            name="John Doe",
            age_group="18-25",
            income_level="low",
            religion="Christian",
            city=self.city_name
        )
        self.persona2 = Persona.objects.create(
            name="Jane Doe",
            age_group="26-40",
            income_level="medium",
            religion="Hindu",
            city=self.city_name
        )

    def test_get_impact_assessment_page(self):
        """Test the GET request for the impact assessment page."""
        response = self.client.get(reverse("impact_assessment"), {"city": self.city_name})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "impact_assessment.html")
        self.assertIn("personas", response.context)
        self.assertIn("cities", response.context)
        self.assertEqual(len(response.context["personas"]), 2)

    def test_post_impact_assessment_missing_data(self):
        """Test POST request with missing data."""
        response = self.client.post(reverse("impact_assessment"), {})
        self.assertRedirects(response, reverse("impact_assessment"))
        messages = list(response.wsgi_request._messages)
        self.assertTrue(
            any(
                "Both news content and persona selection are required." in str(m)
                for m in messages
            )
        )

    def test_post_impact_assessment_success(self):
        """Test successful emotional response generation."""
        response = self.client.post(reverse("impact_assessment"), {
            "news_item": self.news_content,
            "persona_ids[]": [self.persona1.id, self.persona2.id]
        })

        # Fetch the news item created during the POST request
        news_item = NewsItem.objects.get(title=self.news_content)
        self.assertIsNotNone(news_item)

        # Check redirection to the correct results page using the actual news_item.id
        self.assertRedirects(response, reverse("results", args=[news_item.id]))

        # Verify emotional responses are created for both personas
        emotional_responses = EmotionalResponse.objects.filter(news_item=news_item)
        self.assertEqual(emotional_responses.count(), 2)

    def test_duplicate_emotional_response(self):
        """Test that duplicate emotional responses are not created."""
        # Create the news item with a specific ID if needed
        news_item = NewsItem.objects.create(
            title=self.news_content,
            content=self.news_content,
            id=1  # Force a specific ID if needed
        )

        # Create an initial emotional response
        EmotionalResponse.objects.create(
            persona=self.persona1,
            news_item=news_item,
            emotion="Happy",
            intensity=5,
            explanation="Test explanation."
        )

        # Perform the POST request with the same news item
        response = self.client.post(reverse("impact_assessment"), {
            "news_item": self.news_content,
            "persona_ids[]": [self.persona1.id, self.persona2.id]
        })

        # Dynamically get the actual news item ID
        actual_news_item = NewsItem.objects.get(title=self.news_content)

        # Use the actual news item ID in the redirect check
        self.assertRedirects(response, reverse("results", args=[actual_news_item.id]))

        # Verify that only two emotional responses are created (no duplicates)
        emotional_responses = EmotionalResponse.objects.filter(news_item=news_item)
        self.assertEqual(emotional_responses.count(), 2)

    def test_results_view(self):
        """Test the results view for displaying emotional responses."""
        news_item = NewsItem.objects.create(title=self.news_content, content=self.news_content)
        EmotionalResponse.objects.create(
            persona=self.persona1,
            news_item=news_item,
            emotion="Happy",
            intensity=5,
            explanation="Feeling uplifted."
        )
        EmotionalResponse.objects.create(
            persona=self.persona2,
            news_item=news_item,
            emotion="Sad",
            intensity=3,
            explanation="Disheartened by the news."
        )

        response = self.client.get(reverse("results", args=[news_item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "results.html")
        self.assertIn("results", response.context)
        self.assertIn("emotion_chart", response.context)
        self.assertIn("emotion_intensity_bar_chart", response.context)

        results = response.context["results"]
        self.assertEqual(results.count(), 2)
        self.assertEqual(results[0].persona.name, "John Doe")
        self.assertEqual(results[1].persona.name, "Jane Doe")


class AggregateEmotionTests(TestCase):
    """
    This class includes tests for:
    - Validating the behavior when parameters are missing.
    - Ensuring that tasks are triggered correctly on valid requests.
    - Verifying the API response when fetching summary information in 
      different states (completed, processing, or error).
    """
    def setUp(self):
        """
        Set up test data and URLs for testing aggregate emotion features.
        """
        self.client = Client()
        self.city_name = "TestCity"
        self.news_item_title = "TestNews"
        self.aggregate_emotion_url = reverse("aggregate_emotion")  # Replace with the correct name
        self.results_summary_url = reverse("results_summary")  # Replace with the correct name
        self.fetch_summary_url = reverse("fetch_summary_api")  # Replace with the correct name

        # Create mock personas
        for i in range(3):
            Persona.objects.create(city=self.city_name, name=f"Persona {i+1}")

    def test_missing_parameters(self):
        """
        Test redirection to impact assessment when required parameters are missing.
        """
        response = self.client.get(self.aggregate_emotion_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("impact_assessment"))

    def test_valid_request_triggers_task(self):
        """
        Test that a valid request triggers the aggregate emotion task and redirects 
        to the results summary page.
        """
        with patch("simulator.tasks.aggregate_emotion_task.delay") as mock_task:
            response = self.client.get(self.aggregate_emotion_url, {
                "city": self.city_name,
                "news_item": self.news_item_title
            })
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.results_summary_url)
            mock_task.assert_called_once_with(self.city_name, self.news_item_title)

    def test_fetch_summary_completed(self):
        """
        Test that the fetch summary API returns the correct data for a completed summary.
        """
        news_item = NewsItem.objects.create(title=self.news_item_title, content="Test content")
        AggregateEmotion.objects.create(
            news_item=news_item,
            city=self.city_name,
            summary={"positive": 50, "negative": 30, "neutral": 20}
        )
        response = self.client.get(self.fetch_summary_url, {
            "city": self.city_name,
            "news_item": self.news_item_title
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["summary"]["positive"], 50)

    def test_fetch_summary_processing(self):
        """
        Test that the fetch summary API returns 'processing' status for an ongoing summary.
        """
        news_item = NewsItem.objects.create(title=self.news_item_title, content="Test content")
        AggregateEmotion.objects.create(
            news_item=news_item,
            city=self.city_name,
            summary="Processing..."
        )
        response = self.client.get(self.fetch_summary_url, {
            "city": self.city_name,
            "news_item": self.news_item_title
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processing")

    def test_fetch_summary_error(self):
        """
        Test that the fetch summary API handles errors gracefully 
        for non-existent city or news item.
        """
        response = self.client.get(self.fetch_summary_url, {
            "city": "NonExistentCity",
            "news_item": "NonExistentNews"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processing")
