from unittest.mock import patch
from django.test import TestCase
from rest_framework.test import APIClient
from planner.models import Station
class ApiTests(TestCase):
 def setUp(self):self.client=APIClient()
 def test_input_validation(self):
  r=self.client.post('/api/v1/routes/optimize/',{},format='json')
  self.assertEqual(r.status_code,400)
 def test_health(self):
  self.assertEqual(self.client.get('/health/').json(),{'status':'ok'})
 @patch('planner.views.get_route')
 def test_optimized_route(self,route_mock):
  route_mock.return_value=({'distance_miles':700,'duration_minutes':700,'geometry':{'type':'LineString','coordinates':[[-101,35],[-106,35],[-110,35]]}},False)
  Station.objects.create(opis_id='1',name='Demo',city='Gallup',state='NM',price='3.000',latitude=35,longitude=-106)
  response=self.client.post('/api/v1/routes/optimize/',{'start_coordinates':{'lat':35,'lon':-101},'finish_coordinates':{'lat':35,'lon':-110}},format='json')
  self.assertEqual(response.status_code,200,response.data)
  self.assertGreater(len(response.data['fuel_plan']['stops']),0)
  self.assertEqual(response.data['metadata']['routing_cache_hit'],False)
 @patch('planner.views.get_route')
 def test_unreachable(self,route_mock):
  route_mock.return_value=({'distance_miles':1500,'duration_minutes':1000,'geometry':{'type':'LineString','coordinates':[[-101,35],[-110,35]]}},False)
  response=self.client.post('/api/v1/routes/optimize/',{'start_coordinates':{'lat':35,'lon':-101},'finish_coordinates':{'lat':35,'lon':-110}},format='json')
  self.assertEqual(response.status_code,422)
