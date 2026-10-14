from .migration_compiler import MigrationQueryCompiler

class MigrationEngine:
    def __init__(self, con, migration_path):
        self.con=con
        self.migration_path=str(migration_path)
        self.compiler=MigrationQueryCompiler()

    def execute(self, plan):
        q=self.compiler.compile(plan)
        params=[self.migration_path if x=="{migration_path}" else x for x in q["params"]]
        cur=self.con.execute(q["sql"],params)
        cols=[x[0] for x in cur.description]
        rows=[dict(zip(cols,r)) for r in cur.fetchall()]
        unit="persons" if plan["metric"]=="migration_flow_count" else "percent"
        return {"status":"OK","observation":{"metric":plan["metric"],"operation":plan["operation"],
                                            "unit":unit,"results":rows}}
