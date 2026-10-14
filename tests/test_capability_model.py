from pathlib import Path
import unittest, yaml
ROOT=Path(__file__).parents[1]
CAP=ROOT/'capabilities'
def load(n): return yaml.safe_load((CAP/n).read_text(encoding='utf-8'))
class TestCapabilityModel(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.f=load('facts.yaml'); cls.o=load('operations.yaml'); cls.m=load('metrics.yaml'); cls.r=load('relationships.yaml'); cls.c=load('constraints.yaml')
 def test_yaml_parse_and_counts(self):
  self.assertEqual(len(self.f['facts']),6); self.assertEqual(len(self.o['operations']),7); self.assertEqual(len(self.m['metrics']),21); self.assertEqual(len(self.c['constraints']),9)
 def test_metric_fact_refs(self):
  facts=set(self.f['facts']); self.assertFalse({v['source_fact'] for v in self.m['metrics'].values()}-facts)
 def test_metric_operation_refs(self):
  ops=set(self.o['operations']); bad={(k,x) for k,v in self.m['metrics'].items() for x in v['allowed_operations'] if x not in ops}; self.assertFalse(bad)
 def test_relationship_metric_refs(self):
  metrics=set(self.m['metrics']); refs={x for r in self.r['relationships'] for side in ('left','right') for x in r[side]}; self.assertFalse(refs-metrics)
 def test_migration_direction_and_resolution(self):
  x=self.f['facts']['migration_flow']; self.assertEqual(x['semantics']['direction'],'origin_to_destination'); self.assertEqual(x['dimensions']['destination_geography']['finest'],'county')
 def test_marriage_is_persons_not_pairs(self):
  x=self.f['facts']['marriage_activity']; self.assertEqual(x['semantics']['count_unit'],'persons'); self.assertIn('marriage pair count',self.m['metrics']['marriage_person_count']['claims']['does_not_support'])
 def test_fertility_semantics_verified(self):
  self.assertEqual(self.m['metrics']['total_fertility_rate']['unit'],'births_per_woman')
  self.assertEqual(self.m['metrics']['general_fertility_rate']['unit'],'per_thousand')
  self.assertEqual(self.m['metrics']['age_specific_fertility_rate']['unit'],'per_thousand')
  for n in ('total_fertility_rate','general_fertility_rate','age_specific_fertility_rate'):
   x=self.m['metrics'][n]; self.assertEqual(x['aggregation'],'non_additive'); self.assertTrue(x['display_enabled']); self.assertEqual(x['status'],'normal')
 def test_share_change_unit(self):
  for n in ('age_group_share','child_share','working_age_share','aging_share','marital_status_share','unmarried_share','partnered_share','divorced_stock_share','marriage_person_share','same_sex_marriage_person_share','migration_destination_share'):
   self.assertEqual(self.m['metrics'][n]['change_unit'],'percentage_point')
 def test_no_dangerous_operations(self):
  ops=set(self.o['operations']); self.assertTrue({'sum','average','join','correlate','predict','forecast','generate_sql'}.isdisjoint(ops))
 def test_negative_contracts(self):
  metrics=set(self.m['metrics']); self.assertNotIn('divorce_rate',metrics); self.assertNotIn('marriage_rate',metrics); self.assertNotIn('net_migration',metrics); self.assertNotIn('average_marriage_age',metrics); self.assertNotIn('migration_origin_share',metrics)
 def test_cross_frequency_blocked(self):
  r={x['id']:x for x in self.r['relationships']}; self.assertFalse(r['population_marital']['execution_enabled'])
 def test_fertility_relationships_enabled_with_limits(self):
  for x in self.r['relationships']:
   if 'fertility' in x['id']: self.assertTrue(x['execution_enabled'])
if __name__=='__main__': unittest.main(verbosity=2)
