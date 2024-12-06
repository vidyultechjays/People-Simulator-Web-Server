"""
This module contains unit tests for the persona generation and impact assessment functionalities
of the simulator application. It ensures the following:
- Proper validation and creation of personas based on demographic data.
- Handling of special cases and error scenarios in persona generation.
- Verification of the impact assessment process, including emotional response creation,
  result viewing, and duplicate prevention.
- Testing of aggregate emotion summaries, including API responses for different processing states.
"""
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

class FetchSummaryAPITest(TestCase):
    """
    Unit tests for the FetchSummaryAPI view.

    This test suite ensures the API behaves correctly under various scenarios,
    such as successful summary retrieval, missing parameters, invalid inputs,
    and different data states.
    """
    def setUp(self):
        """
        Set up initial data for tests.
        """
        self.news_item = NewsItem.objects.create(
            title="Test News Item",
            content="This is a test news item."
        )

        self.aggregate_emotion = AggregateEmotion.objects.create(
            city="Test City",
            news_item=self.news_item,
            summary={
                "positive": 5,
                "negative": 3,
                "neutral": 2,
                "total": 10,
                "positive_percentage": 50,
                "negative_percentage": 30,
                "neutral_percentage": 20,
            },
            demographic_summary={
                "age_categories": {
                    "18-25": {"positive": 2, "negative": 1, "neutral": 1, "total": 4},
                    "26-40": {"positive": 3, "negative": 2, "neutral": 1, "total": 6},
                },
                "income_categories": {
                    "low": {"positive": 2, "negative": 1, "neutral": 1, "total": 4},
                    "medium": {"positive": 3, "negative": 2, "neutral": 1, "total": 6},
                },
            },
        )

        self.client = Client()
        self.url = reverse("fetch_summary_api")

    def test_fetch_summary_success(self):
        """
        Test successful fetching of the summary for an existing city and news item.
        """
        response = self.client.get(self.url, {
            "city": "Test City",
            "news_item": "Test News Item"
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertIn("summary", response.json())
        self.assertIn("demographic_summary", response.json())
        self.assertEqual(response.json()["summary"]["positive"], 5)

    def test_fetch_summary_processing(self):
        """
        Test response when the summary is still processing (total count is 0).
        """
        self.aggregate_emotion.summary = {"total": 0}
        self.aggregate_emotion.save()

        response = self.client.get(self.url, {
            "city": "Test City",
            "news_item": "Test News Item"
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "processing")

    def test_fetch_summary_missing_parameters(self):
        """
        Test response when required parameters are missing.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_fetch_summary_invalid_city_or_news_item(self):
        """
        Test response when the city or news item does not exist.
        """
        response = self.client.get(self.url, {
            "city": "Nonexistent City",
            "news_item": "Nonexistent News Item"
        })

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["status"], "error")
        self.assertEqual(response.json()["message"], "Summary not found")

    def test_fetch_summary_no_data(self):
        """
        Test response when there is no demographic data.
        """
        self.aggregate_emotion.demographic_summary = {}
        self.aggregate_emotion.save()

        response = self.client.get(self.url, {
            "city": "Test City",
            "news_item": "Test News Item"
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        self.assertEqual(response.json()["demographic_summary"], {})
