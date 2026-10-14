class PopulationQueryCompiler:
    POP_METRICS = {
        "total_population","households","age_group_population","age_group_share",
        "child_share","working_age_share","aging_share","aging_speed"
    }

    def compile(self, plan):
        metric, op = plan["metric"], plan["operation"]
        if metric not in self.POP_METRICS:
            raise ValueError("not a population metric")
        if op not in {"snapshot","rank","trend","change","compare"}:
            raise ValueError("unsupported population operation")

        periods = self._periods(plan)
        scope = plan.get("scope") or {}
        age = self._age_contract(metric, plan)
        value_sql, source = self._value_sql(metric, age, len(periods), scope.get("geography_level"))

        sql = "WITH base AS (\n" + value_sql + "\n)\n"
        params = [source, *periods]

        # Critical invariant: parent geography is part of the semantic universe.
        # It must survive compilation for set-valued operations.
        parent = scope.get("parent_geography")
        parent_clause = ""
        if parent:
            parent_clause = "geography LIKE ?"

        if op in {"snapshot","trend"}:
            geo = scope.get("geography")
            if not geo:
                raise ValueError(f"{op} requires geography")
            sql += "SELECT period, geography, metric_value FROM base WHERE geography = ?"
            params.append(geo)
            sql += " ORDER BY period"

        elif op == "compare":
            geos = scope.get("geographies")
            if not isinstance(geos, list) or len(geos) < 2:
                raise ValueError("compare requires geographies")
            clauses = []
            if parent_clause:
                clauses.append(parent_clause)
                params.append(parent + "%")
            clauses.append("geography IN (" + ",".join("?" for _ in geos) + ")")
            sql += "SELECT period, geography, metric_value FROM base WHERE " + " AND ".join(clauses)
            params.extend(geos)
            sql += " ORDER BY geography"

        elif op == "rank":
            sql += "SELECT period, geography, metric_value FROM base"
            if parent_clause:
                sql += " WHERE " + parent_clause
                params.append(parent + "%")
            sql += " ORDER BY metric_value " + ("DESC" if plan.get("order","descending")=="descending" else "ASC") + ", geography ASC"
            if plan.get("limit") is not None:
                sql += " LIMIT ?"
                params.append(plan["limit"])

        else:  # change
            start, end = plan["start_period"], plan["end_period"]
            sql += """, p AS (
 SELECT geography,
 MAX(CASE WHEN period=? THEN metric_value END) AS start_value,
 MAX(CASE WHEN period=? THEN metric_value END) AS end_value
 FROM base GROUP BY geography
)
SELECT geography,start_value,end_value,end_value-start_value AS change_value
FROM p WHERE start_value IS NOT NULL AND end_value IS NOT NULL"""
            params.extend([start, end])
            clauses = []
            if parent_clause:
                clauses.append(parent_clause)
                params.append(parent + "%")
            geo = scope.get("geography")
            if geo:
                clauses.append("geography=?")
                params.append(geo)
            if clauses:
                sql += " AND " + " AND ".join(clauses)
            sql += " ORDER BY change_value " + ("DESC" if plan.get("order","descending")=="descending" else "ASC") + ", geography ASC"
            if plan.get("limit") is not None:
                sql += " LIMIT ?"
                params.append(plan["limit"])

        return {"sql": sql.strip(), "params": params, "source": source}

    def _periods(self, plan):
        if plan["operation"] in {"snapshot","rank","compare"}:
            return [plan["period"]]
        return [plan["start_period"], plan["end_period"]]

    def _age_contract(self, metric, plan):
        if metric == "child_share": return (0,14)
        if metric == "working_age_share": return (15,64)
        if metric in {"aging_share","aging_speed"}: return (65,None)
        if metric in {"age_group_population","age_group_share"}:
            a=(plan.get("parameters") or {}).get("age_range") or {}
            return (a.get("min"),a.get("max"))
        return None

    def _value_sql(self, metric, age, period_count, geography_level=None):
        marks=",".join("?" for _ in range(period_count))
        geography_expr = self._geography_expr(geography_level)
        if metric in {"total_population","households"}:
            col="population_total" if metric=="total_population" else "households"
            return f"""SELECT period, {geography_expr} AS geography, SUM({col})::DOUBLE AS metric_value
FROM read_parquet(?) WHERE period IN ({marks})
GROUP BY period,geography""", "{population_summary_path}"

        lo,hi=age
        cond=[]
        if lo is not None: cond.append(f"age >= {int(lo)}")
        if hi is not None: cond.append(f"age <= {int(hi)}")
        condition=" AND ".join(cond) if cond else "TRUE"
        if metric=="age_group_population":
            expr=f"SUM(CASE WHEN {condition} THEN population ELSE 0 END)::DOUBLE"
        else:
            expr=f"""100.0*SUM(CASE WHEN {condition} THEN population ELSE 0 END)
 / NULLIF(SUM(population),0)"""
        return f"""SELECT period, {geography_expr} AS geography, {expr} AS metric_value
FROM read_parquet(?) WHERE period IN ({marks})
GROUP BY period,geography""", "{population_age_path}"


    def _geography_expr(self, level):
        # Existing behavior remains the default. Rollups are explicit.
        if not level or level == "district":
            return "site_id"
        if level == "county":
            # site_id is a district/township label prefixed by its county/city,
            # e.g. 臺北市內湖區 / 嘉義縣民雄鄉 / 嘉義市東區.
            return "regexp_extract(site_id, '^(.+?[縣市])', 1)"
        if level == "country":
            return "'臺灣'"
        raise ValueError(f"unsupported population geography_level: {level}")
