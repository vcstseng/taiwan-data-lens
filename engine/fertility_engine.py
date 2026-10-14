from .fertility_compiler import FertilityCompiler
class FertilityEngine:
    def __init__(self,con,fertility_path):
        self.con=con; self.fertility_path=str(fertility_path); self.compiler=FertilityCompiler()
    def execute(self,plan):
        q=self.compiler.compile(plan)
        params=[self.fertility_path if x=="{fertility_path}" else x for x in q["params"]]
        cur=self.con.execute(q["sql"],params); cols=[x[0] for x in cur.description]
        return {"status":"OK","observation":{"metric":plan["metric"],"operation":plan["operation"],"unit":q["unit"],"results":[dict(zip(cols,r)) for r in cur.fetchall()]}}
