from django.db import models
class Station(models.Model):
 opis_id=models.CharField(max_length=50,db_index=True)
 name=models.CharField(max_length=255)
 address=models.CharField(max_length=255,blank=True)
 city=models.CharField(max_length=120,db_index=True)
 state=models.CharField(max_length=2,db_index=True)
 rack_id=models.CharField(max_length=50,blank=True)
 price=models.DecimalField(max_digits=10,decimal_places=5)
 latitude=models.FloatField(null=True,blank=True)
 longitude=models.FloatField(null=True,blank=True)
 precision=models.CharField(max_length=20,default='unknown')
 class Meta:
  indexes=[models.Index(fields=['state','city']),models.Index(fields=['latitude','longitude'])]
  constraints=[models.UniqueConstraint(fields=['opis_id','city','state'],name='unique_opis_city_state')]
 def __str__(self):return f'{self.name} ({self.city}, {self.state})'
