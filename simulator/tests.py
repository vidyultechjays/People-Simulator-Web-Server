"""
Unit tests for the persona generation functionality in the simulator app.
These tests cover valid and invalid persona generation, demographic validation,
and template rendering.
"""
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from faker import Faker

class PersonaGenerationTest(TestCase):
    """
    Test cases for generating personas in the simulator app. 
    This includes tests for valid persona generation, invalid demographic inputs, 
    zero population handling, and GET request rendering.
    """

    def setUp(self):
        """Set up any data that will be used in the tests."""
        self.faker = Faker()
        self.url = reverse('persona_generation')

    @patch('simulator.views.Persona.objects.bulk_create')
    def test_valid_persona_generation(self, mock_bulk_create):
        """Test for valid persona generation when demographics sum to 100."""
        data = {
            'city_name': 'Test City',
            'population': 100,
            'demographics[age_groups][18-25]': 25,
            'demographics[age_groups][26-40]': 25,
            'demographics[age_groups][41-60]': 25,
            'demographics[age_groups][60+]': 25,
            'demographics[religions][hindu]': 25,
            'demographics[religions][muslim]': 25,
            'demographics[religions][christian]': 25,
            'demographics[religions][others]': 25,
            'demographics[income_groups][low]': 33,
            'demographics[income_groups][medium]': 33,
            'demographics[income_groups][high]': 34
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)  # Should be 200 OK
        self.assertIn("Personas for Test City generated successfully.", response.content.decode())
        mock_bulk_create.assert_called()  # Check that Persona.objects.bulk_create was called

    def test_invalid_demographics_sum(self):
        """Test when demographics percentages don't sum to 100."""
        data = {
            'city_name': 'Test City',
            'population': 100,
            'demographics[age_groups][18-25]': 30,
            'demographics[age_groups][26-40]': 30,
            'demographics[age_groups][41-60]': 30,
            'demographics[age_groups][60+]': 20,  # Total does not sum to 100
            'demographics[religions][hindu]': 25,
            'demographics[religions][muslim]': 25,
            'demographics[religions][christian]': 25,
            'demographics[religions][others]': 25,
            'demographics[income_groups][low]': 33,
            'demographics[income_groups][medium]': 33,
            'demographics[income_groups][high]': 34
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 400)  # Should return bad request
        self.assertIn("Demographic percentages must sum up to 100.", response.content.decode())

    @patch('simulator.views.Persona.objects.bulk_create')
    def test_valid_persona_generation_without_population(self, mock_bulk_create):
        """Test for valid persona generation with no population."""
        data = {
            'city_name': 'Test City',
            'population': 0,  # Zero population
            'demographics[age_groups][18-25]': 25,
            'demographics[age_groups][26-40]': 25,
            'demographics[age_groups][41-60]': 25,
            'demographics[age_groups][60+]': 25,
            'demographics[religions][hindu]': 25,
            'demographics[religions][muslim]': 25,
            'demographics[religions][christian]': 25,
            'demographics[religions][others]': 25,
            'demographics[income_groups][low]': 33,
            'demographics[income_groups][medium]': 33,
            'demographics[income_groups][high]': 34
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Personas for Test City generated successfully.", response.content.decode())
        mock_bulk_create.assert_not_called()

    def test_get_request_renders_template(self):
        """Test that GET requests render the persona generation template."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "persona_generation.html")
        self.assertIn("<h1>GENERATE PERSONAS</h1>", response.content.decode())
