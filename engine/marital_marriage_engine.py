from .marital_marriage_compiler import MaritalMarriageCompiler
class MaritalMarriageEngine:
 def __init__(self,con,marital_path,marriage_path):
  self.con=con; self.marital_path=str(marital_path); self.marriage_path=str(marriage_path); self.compiler=MaritalMarriageCompiler()
 def execute(self,plan):
  q=self.compiler.compile(plan)
  params=[self.marital_path if x=="{marital_path}" else self.marriage_path if x=="{marriage_path}" else x for x in q["params"]]
  cur=self.con.execute(q["sql"],params); cols=[x[0] for x in cur.description]
  return {"status":"OK","observation":{"metric":plan["metric"],"operation":plan["operation"],"unit":q["unit"],"results":[dict(zip(cols,r)) for r in cur.fetchall()]}}
